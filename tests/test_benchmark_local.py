"""AFN-052/053 benchmark guards and portable package regression."""

import importlib.util
import json
from pathlib import Path
import subprocess
import sys
from zipfile import ZipFile

import pytest

ROOT = Path(__file__).resolve().parents[1]


def module(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / "scripts" / f"{name}.py")
    loaded = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(loaded)
    return loaded


bench = module("benchmark_local")


def test_summary_uses_actual_values_and_nearest_rank_p95():
    values = [10000.0] + list(range(1, 20))
    assert bench.statistics_ms(values) == {"n": 20, "min": 1, "median": 10.5,
                                           "p95_nearest_rank": 19, "max": 10000}


@pytest.mark.parametrize("values", [[], [float("nan")], [float("inf")], [-1]])
def test_bad_measurements_cannot_be_reported_as_success(values):
    with pytest.raises(ValueError):
        bench.statistics_ms(values)


@pytest.mark.parametrize("arguments", [["--repeat", "19"], ["--threads", "0"], ["--timeout", "nan"]])
def test_cli_requires_meaningful_measurement(arguments):
    with pytest.raises(SystemExit) as error:
        bench.main(["--bundle", "absent", *arguments])
    assert error.value.code == 2


def test_candidate_is_explicit_and_never_promoted_to_frozen_evidence(tmp_path):
    meta = {"is_fixture": False, "configuration": "multimodal", "status": "candidate",
            "model_id": "candidate", "model_version": "version"}
    path = tmp_path / "metadata.json"
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        bench.preflight(tmp_path, False, tmp_path / "freeze.json")
    identity = bench.preflight(tmp_path, True, tmp_path / "absent-freeze.json")
    assert identity["freeze_verified"] is False
    assert len(identity["metadata_sha256"]) == 64
    meta["is_fixture"] = True
    path.write_text(json.dumps(meta))
    with pytest.raises(ValueError):
        bench.preflight(tmp_path, True, tmp_path / "freeze.json")


def test_frozen_metadata_alone_is_not_a_signed_freeze(tmp_path):
    meta = {"is_fixture": False, "configuration": "multimodal", "status": "frozen",
            "model_id": "candidate", "model_version": "version"}
    (tmp_path / "metadata.json").write_text(json.dumps(meta))
    with pytest.raises(FileNotFoundError):
        bench.preflight(tmp_path, False, tmp_path / "missing-freeze.json")


def test_backend_package_contains_lifecycle_and_cors_and_imports_in_isolation(tmp_path):
    package = module("package_backend")
    archive_path = tmp_path / "backend.zip"
    package.build_backend(archive_path)
    with ZipFile(archive_path) as archive:
        assert "backend/app/lifespan.py" in archive.namelist()
        assert "backend/app/cors.py" in archive.namelist()
        assert all(not n.startswith("data/") and n != ".env" for n in archive.namelist())
        archive.extractall(tmp_path / "unpacked")
    result = subprocess.run([sys.executable, "-c", "from app.main import app; print(app.version)"],
                            cwd=tmp_path / "unpacked/backend", capture_output=True, text=True, timeout=30)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "0.2.0"
