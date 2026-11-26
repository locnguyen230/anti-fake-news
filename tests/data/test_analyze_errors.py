from argparse import Namespace
import json

import pytest

from ml.common import sha256_file
from ml.freeze import canonical_sha256, sign
from scripts.analyze_errors import analyze, main


def write_json(path, value):
    path.write_text(json.dumps(value) + "\n", encoding="utf-8", newline="\n")


def write_rows(path, rows):
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8", newline="\n")


@pytest.fixture
def evidence(tmp_path):
    args = Namespace(**{
        name: tmp_path / f"{name}.txt"
        for name in ("freeze", "metrics", "predictions", "manifest", "qa_split", "locked_split", "summary")
    }, quality_flags=None, quality_sha256=None, out_dir=tmp_path / "out")
    header = "sample_id,split,group_id\ntraining,train,training-group\n"
    groups = ("private-a", "private-a", "private-b", "private-b")
    args.locked_split.write_text(header + "".join(f",test,{group}\n" for group in groups), encoding="utf-8")
    ids = [f"private-sample-{i}" for i in range(len(groups))]
    args.qa_split.write_text(header + "".join(f"{sid},test,{group}\n" for sid, group in zip(ids, groups)), encoding="utf-8")
    configs = {
        name: {"model_id": name, "model_version": name + "-1", "threshold": 0.7, "C": 10.0, "is_fixture": False}
        for name in ("text-only", "multimodal")
    }
    record = {
        "schema": "afn-model-freeze-v1",
        "status": "draft",
        "protocol": {"status": "locked"},
        "evidence_kind": "VALIDATION_ONLY",
        "data": {"manifest_sha256": "a" * 64, "split_sha256": sha256_file(args.locked_split), "test_locked_rows": 4},
        "configurations": configs,
        "blockers": [],
        "signoffs": {"ml": None, "qa": None},
    }
    for role in ("ml", "qa"):
        sign(record, role, f"synthetic-{role}")
    write_json(args.freeze, record)
    args.summary.write_text(" ".join(record["data"][key] for key in ("manifest_sha256", "split_sha256")), encoding="utf-8")
    args.summary_sha256 = sha256_file(args.summary)

    manifest, predictions = [], []
    decisions = [("fake", "fake"), ("real", "real"), ("real", "fake"), ("fake", "real")]
    for index, (sid, group) in enumerate(zip(ids, groups)):
        label = "fake" if index < 2 else "real"
        manifest.append({
            "sample_id": sid, "group_id": group, "is_fixture": False, "source": "politifact",
            "status": "accepted", "schema_version": "afn-manifest-v1", "label": label,
            "publisher": "private-publisher", "event_id": "private-event", "body": "private-article",
        })
        predictions.append({
            "sample_id": sid, "group_id": group, "source_label": label, "text_truncated": index == 1,
            "predictions": {
                name: {"label": decision, "fake_score": 0.7 if decision == "fake" else 0.3,
                       "model_version": configs[name]["model_version"]}
                for name, decision in zip(configs, decisions[index])
            },
        })
    write_rows(args.manifest, manifest)
    write_rows(args.predictions, predictions)
    metrics = {
        "schema": "afn-test-metrics-v1", "evidence_kind": "TEST_FINAL", "refit": False,
        "labels": ["fake", "real"], "positive_label": "fake", "split": "test",
        "freeze": {"record_sha256": canonical_sha256(record), "status": "signed",
                   "signed_by": {"ml": "synthetic-ml", "qa": "synthetic-qa"}},
        "inputs": {
            "freeze_sha256": sha256_file(args.freeze), "test_manifest_sha256": sha256_file(args.manifest),
            "qa_split_sha256": sha256_file(args.qa_split), "locked_split_sha256": sha256_file(args.locked_split),
            "predictions_sha256": sha256_file(args.predictions),
        },
        "n_test": 4, "n_groups": 2, "class_support": {"fake": 2, "real": 2},
        "configurations": {name: {**config, "confusion_matrix": {"rows_true_cols_pred": [[1, 1], [1, 1]]}}
                           for name, config in configs.items()},
    }
    write_json(args.metrics, metrics)
    return args, record, metrics, manifest, predictions


def test_cli_reports_paired_counts_and_no_private_values(evidence):
    args, _, _, manifest, _ = evidence
    args.quality_flags = args.out_dir.parent / "flags.jsonl"
    write_rows(args.quality_flags, [
        {"sample_id": manifest[0]["sample_id"], "text_flags": ["short_body"], "image_flags": []},
    ])
    args.quality_sha256 = sha256_file(args.quality_flags)
    cli = [part for name, value in vars(args).items() for part in ("--" + name.replace("_", "-"), str(value))]
    assert main(cli) == 0
    json_path = args.out_dir / "error-analysis.json"
    result = json.loads(json_path.read_text(encoding="utf-8"))
    assert result["status"] == "PENDING_QA_REVIEW"
    assert result["overall"]["n"] == 4
    assert list(result["overall"]["outcomes"].values()) == [{"count": 1, "fraction": 0.25}] * 4
    assert result["strata"]["text_flags"]["short_body"]["n"] == 1
    assert result["strata"]["text_flags"]["unknown"]["n"] == 3
    assert result["strata"]["image_flags"]["none_recorded"]["n"] == 1
    assert result["strata"]["group_size"]["2"]["n"] == 4
    original = json_path.read_bytes()
    assert b"private-" not in original
    assert "25.00%" in (args.out_dir / "error-analysis.md").read_text(encoding="utf-8")
    with pytest.raises(SystemExit):
        main(cli)
    assert json_path.read_bytes() == original


@pytest.mark.parametrize(("case", "message"), [
    ("draft", "signed research freeze"),
    ("signature", "invalid qa signoff"),
    ("fixture", "research Test metrics"),
    ("summary", "dataset summary"),
    ("digest", "checksum mismatch"),
    ("duplicate", "unique, nonempty"),
    ("coverage", "cover exactly"),
    ("label", "inconsistent label"),
    ("group", "inconsistent label/group"),
    ("threshold", "frozen threshold"),
    ("version", "score or model version"),
    ("matrix", "confusion matrix"),
])
def test_reject_invalid_evidence(evidence, case, message):
    args, record, metrics, manifest, predictions = evidence
    if case in ("draft", "signature"):
        if case == "draft":
            record["status"] = "draft"
        else:
            record["signoffs"]["qa"]["record_sha256"] = "invalid"
        write_json(args.freeze, record)
    elif case == "fixture":
        metrics["evidence_kind"] = "FIXTURE_SMOKE_NOT_RESEARCH"
    elif case == "summary":
        args.summary_sha256 = "0" * 64
    elif case == "digest":
        metrics["inputs"]["predictions_sha256"] = "0" * 64
    elif case in ("duplicate", "coverage"):
        write_rows(args.manifest, manifest + [manifest[0]] if case == "duplicate" else manifest[1:])
        metrics["inputs"]["test_manifest_sha256"] = sha256_file(args.manifest)
    elif case == "matrix":
        metrics["configurations"]["text-only"]["confusion_matrix"]["rows_true_cols_pred"] = [[2, 0], [0, 2]]
    else:
        prediction = predictions[0]
        if case == "label":
            prediction["source_label"] = "real"
        elif case == "group":
            prediction["group_id"] = "other"
        elif case == "threshold":
            prediction["predictions"]["text-only"]["label"] = "real"
        elif case == "version":
            prediction["predictions"]["text-only"]["model_version"] = "other"
        write_rows(args.predictions, predictions)
        metrics["inputs"]["predictions_sha256"] = sha256_file(args.predictions)
    write_json(args.metrics, metrics)
    with pytest.raises(ValueError, match=message):
        analyze(args)
    assert not args.out_dir.exists()


def test_quality_flags_require_valid_hash_and_taxonomy(evidence):
    args, _, _, manifest, _ = evidence
    args.quality_flags = args.out_dir.parent / "flags.jsonl"
    write_rows(args.quality_flags, [
        {"sample_id": manifest[0]["sample_id"], "text_flags": ["unreviewed_flag"], "image_flags": []},
    ])
    with pytest.raises(ValueError, match="checksum mismatch"):
        analyze(args)
    args.quality_sha256 = sha256_file(args.quality_flags)
    with pytest.raises(ValueError, match="invalid QA quality flags"):
        analyze(args)
