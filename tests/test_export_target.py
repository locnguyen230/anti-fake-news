"""AFN-035 export into backend/artifacts/: in-place replace, guards and #34 selection check."""

import json

import pytest

import ml.export_artifacts as export_mod
from app.model_bundle import BUNDLE_DIRS, load_bundle
from ml.common import load_dataset
from ml.export_artifacts import DEFAULT_OUT, MANAGED_ENTRIES, export_all


@pytest.fixture
def dataset(ml_fixture):
    return load_dataset(ml_fixture["manifest"], ml_fixture["split"], ml_fixture["image_root"])


@pytest.fixture
def inputs(dataset):
    return {"manifest_sha256": dataset.manifest_sha256, "split_sha256": dataset.split_sha256,
            "experiment_config_sha256": "0" * 64}


@pytest.fixture
def artifacts(tmp_path):
    """Mimic backend/artifacts: a tracked schema file that must survive every export."""
    out = tmp_path / "backend" / "artifacts"
    out.mkdir(parents=True)
    (out / "metadata.schema.json").write_text('{"tracked": true}\n')
    return out


def _versions(out):
    return {name: load_bundle(out / d).model_version for name, d in BUNDLE_DIRS.items()}


def test_default_target_matches_issue_outputs():
    assert DEFAULT_OUT.parts[-2:] == ("backend", "artifacts")
    assert set(MANAGED_ENTRIES) == {"text_only", "image_only", "multimodal", "label_map.json",
                                    "export-report.json"}


def test_exports_next_to_tracked_files(dataset, ml_config, fake_encoder, inputs, artifacts):
    export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs)
    assert {p.name for p in artifacts.iterdir()} == {*MANAGED_ENTRIES, "metadata.schema.json"}
    assert (artifacts / "metadata.schema.json").read_text() == '{"tracked": true}\n'
    assert list(artifacts.parent.glob(".afn-export-*")) == []


def test_replace_requires_flag_and_keeps_other_files(dataset, ml_config, fake_encoder, inputs, artifacts):
    export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs)
    before = (artifacts / "text_only" / "metadata.json").read_bytes()
    with pytest.raises(FileExistsError, match="--replace"):
        export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs)
    assert (artifacts / "text_only" / "metadata.json").read_bytes() == before

    export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs, replace=True)
    assert (artifacts / "metadata.schema.json").exists()
    assert set(_versions(artifacts)) == set(BUNDLE_DIRS)


def test_fixture_never_replaces_research_bundles(dataset, ml_config, fake_encoder, inputs, artifacts):
    export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs)
    report = artifacts / "export-report.json"
    data = json.loads(report.read_text())
    data["is_fixture"] = False  # pretend the installed bundles are research candidates
    report.write_text(json.dumps(data))
    with pytest.raises(FileExistsError, match="research bundles"):
        export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs, replace=True)
    assert json.loads(report.read_text())["is_fixture"] is False


def test_failed_install_rolls_back(dataset, ml_config, fake_encoder, inputs, artifacts, monkeypatch):
    export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs)
    before = _versions(artifacts)
    report_before = (artifacts / "export-report.json").read_bytes()
    real_rename = type(artifacts).rename

    def flaky_rename(self, target):
        if self.name == "multimodal" and ".afn-export-" in str(self) and "bundles" in str(self):
            raise OSError("simulated failure while installing")
        return real_rename(self, target)

    monkeypatch.setattr(type(artifacts), "rename", flaky_rename)
    with pytest.raises(OSError, match="simulated"):
        export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs, replace=True)
    monkeypatch.undo()
    assert (artifacts / "export-report.json").read_bytes() == report_before
    assert _versions(artifacts) == before


def test_expected_selection_must_match(dataset, ml_config, fake_encoder, inputs, artifacts, tmp_path):
    first = export_all(dataset, ml_config, fake_encoder, tmp_path / "probe", inputs=inputs)
    selected = {"run_id": "r1", "inputs": inputs, "configurations": {
        name: {"C": b["C"], "threshold": b["threshold"]} for name, b in first["bundles"].items()}}
    report = export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs,
                        expected_selection=selected)
    assert report["selected_models_run_id"] == "r1"

    wrong = json.loads(json.dumps(selected))
    wrong["configurations"]["multimodal"]["threshold"] = 0.123
    with pytest.raises(RuntimeError, match="#34 chose"):
        export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs, replace=True,
                   expected_selection=wrong)
    stale = dict(selected, inputs=dict(inputs, split_sha256="f" * 64))
    with pytest.raises(RuntimeError, match="different manifest/split/config"):
        export_all(dataset, ml_config, fake_encoder, artifacts, inputs=inputs, replace=True,
                   expected_selection=stale)
    assert json.loads((artifacts / "export-report.json").read_text())["selected_models_run_id"] == "r1"


def test_cli_refuses_existing_bundles_without_replace(artifacts, ml_fixture, monkeypatch, capsys):
    (artifacts / "text_only").mkdir()
    with pytest.raises(SystemExit):
        export_mod.main(["--manifest", str(ml_fixture["manifest"]), "--split", str(ml_fixture["split"]),
                         "--out", str(artifacts)])
    assert "--replace" in capsys.readouterr().err
