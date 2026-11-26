"""Analyze paired AFN-050 predictions without rerunning inference or reading images."""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import json
from pathlib import Path

from ml.common import MANIFEST_SCHEMA_VERSION, sha256_file
from ml.evaluate_test import LABELS, SCHEMA as METRICS_SCHEMA, EvaluationError, check_split_against_freeze
from ml.freeze import ROLES, SCHEMA as FREEZE_SCHEMA, canonical_sha256, read_record


CONFIGS = ("text-only", "multimodal")
OUTCOMES = {
    (True, True): "both_correct",
    (False, False): "both_wrong",
    (True, False): "text_only_correct",
    (False, True): "multimodal_only_correct",
}
TEXT_FLAGS = {"short_body", "boilerplate", "wrong_article", "paywall", "unsupported_language"}
IMAGE_FLAGS = {"low_resolution", "logo_or_placeholder", "irrelevant_image", "unverified_image"}


def index_rows(path):
    rows = {}
    with path.open(encoding="utf-8") as stream:
        for line in stream:
            if not line.strip():
                continue
            row = json.loads(line)
            sample_id = row.get("sample_id") if isinstance(row, dict) else None
            if not isinstance(sample_id, str) or not sample_id.strip() or sample_id in rows:
                raise ValueError("JSONL requires unique, nonempty sample IDs")
            rows[sample_id] = row
    return rows


def require_signed_freeze(record):
    if (record.get("schema") != FREEZE_SCHEMA or record.get("status") != "signed"
            or record.get("evidence_kind") != "VALIDATION_ONLY"
            or record.get("protocol", {}).get("status") != "locked" or record.get("blockers") != []):
        raise ValueError("a signed research freeze with a locked protocol and no blockers is required")
    digest = canonical_sha256(record)
    signed_by = {}
    for role in ROLES:
        signature = record.get("signoffs", {}).get(role)
        if (not signature or signature.get("record_sha256") != digest
                or not isinstance(signature.get("by"), str) or not signature["by"].strip()):
            raise ValueError(f"missing or invalid {role} signoff")
        signed_by[role] = signature["by"].strip()
    if len({name.casefold() for name in signed_by.values()}) != len(ROLES):
        raise ValueError("ML and QA must be distinct signers")
    return {"record_sha256": digest, "status": "signed", "signed_by": signed_by}


def verify_evidence(args):
    record = read_record(args.freeze)
    signature = require_signed_freeze(record)
    metrics = json.loads(args.metrics.read_text(encoding="utf-8"))
    if (metrics.get("schema") != METRICS_SCHEMA or metrics.get("evidence_kind") != "TEST_FINAL"
            or metrics.get("split") != "test" or metrics.get("refit") is not False
            or metrics.get("labels") != LABELS or metrics.get("positive_label") != "fake"
            or metrics.get("freeze") != signature):
        raise ValueError("expected AFN-050 research Test metrics for the signed freeze")

    summary_text = args.summary.read_text(encoding="utf-8")
    if (sha256_file(args.summary) != args.summary_sha256
            or any(record["data"][key] not in summary_text for key in ("manifest_sha256", "split_sha256"))):
        raise ValueError("dataset summary does not match the QA hash and frozen data")

    for name in CONFIGS:
        expected = record["configurations"][name]
        observed = metrics["configurations"][name]
        if expected.get("is_fixture") is not False or any(
            expected[key] != observed[key] for key in ("model_id", "model_version", "threshold", "C")
        ):
            raise ValueError("Test configuration does not match the research freeze")

    inputs = {
        "freeze_sha256": args.freeze,
        "test_manifest_sha256": args.manifest,
        "qa_split_sha256": args.qa_split,
        "locked_split_sha256": args.locked_split,
        "predictions_sha256": args.predictions,
    }
    for name, path in inputs.items():
        if sha256_file(path) != metrics["inputs"].get(name):
            raise ValueError(f"Test evidence checksum mismatch: {name}")
    split = check_split_against_freeze(record, args.locked_split, args.qa_split)
    return metrics, split


def read_quality_flags(path, digest, samples):
    if path is None:
        return {}
    if sha256_file(path) != digest:
        raise ValueError("QA quality flags checksum mismatch")
    flags = index_rows(path)
    if not flags.keys() <= samples:
        raise ValueError("quality flags contain an ID outside Test")
    for row in flags.values():
        for key, allowed in (("text_flags", TEXT_FLAGS), ("image_flags", IMAGE_FLAGS)):
            values = row.get(key)
            if (not isinstance(values, list) or any(not isinstance(value, str) or value not in allowed for value in values)
                    or len(values) != len(set(values))):
                raise ValueError("invalid QA quality flags")
    return flags


def breakdown(counts):
    total = sum(counts.values())
    return {
        "n": total,
        "outcomes": {
            name: {"count": counts[name], "fraction": counts[name] / total if total else None}
            for name in OUTCOMES.values()
        },
    }


def analyze(args):
    metrics, split = verify_evidence(args)
    manifest = index_rows(args.manifest)
    predictions = index_rows(args.predictions)
    if not split or split.keys() != manifest.keys() or split.keys() != predictions.keys():
        raise ValueError("manifest, predictions and QA split must cover exactly the same nonempty Test set")
    quality = read_quality_flags(args.quality_flags, args.quality_sha256, split.keys())

    overall = Counter()
    support = Counter()
    matrices = {name: [[0, 0], [0, 0]] for name in CONFIGS}
    strata = defaultdict(lambda: defaultdict(Counter))
    group_sizes = Counter(split.values())
    for sample_id, group in split.items():
        sample = manifest[sample_id]
        predicted = predictions[sample_id]
        label, source = sample.get("label"), sample.get("source")
        if (sample.get("schema_version") != MANIFEST_SCHEMA_VERSION or sample.get("status") != "accepted"
                or sample.get("is_fixture") is not False or sample.get("group_id") != group
                or label not in LABELS or source not in ("gossipcop", "politifact")
                or predicted.get("source_label") != label or predicted.get("group_id") != group
                or type(predicted.get("text_truncated")) is not bool):
            raise ValueError("invalid Test row or inconsistent label/group metadata")
        support[label] += 1
        correct = []
        for name in CONFIGS:
            result = predicted["predictions"][name]
            config = metrics["configurations"][name]
            score = result.get("fake_score")
            if (type(score) not in (float, int) or not 0 <= score <= 1
                    or result.get("model_version") != config["model_version"]):
                raise ValueError("invalid Test score or model version")
            decision = "fake" if score >= config["threshold"] else "real"
            if result.get("label") != decision:
                raise ValueError("prediction disagrees with the frozen threshold")
            matrices[name][LABELS.index(label)][LABELS.index(decision)] += 1
            correct.append(label == decision)

        outcome = OUTCOMES[tuple(correct)]
        overall[outcome] += 1
        dimensions = {
            "label": label,
            "source": source,
            "source_label": f"{source}:{label}",
            "publisher_metadata": "recorded" if sample.get("publisher") else "unknown",
            "event_metadata": "recorded" if sample.get("event_id") else "unknown",
            "group_size": str(group_sizes[group]),
            "text_truncated": str(predicted["text_truncated"]).lower(),
        }
        for dimension, value in dimensions.items():
            strata[dimension][value][outcome] += 1
        for key in ("text_flags", "image_flags"):
            values = quality[sample_id][key] if sample_id in quality else ["unknown"]
            for value in values or ["none_recorded"]:
                strata[key][value][outcome] += 1

    class_support = {label: support[label] for label in LABELS}
    if (metrics["n_test"] != len(split) or metrics["n_groups"] != len(group_sizes)
            or metrics["class_support"] != class_support):
        raise ValueError("Test total, group count or class support disagrees with metrics")
    for name, matrix in matrices.items():
        evidence = metrics["configurations"][name]["confusion_matrix"]
        if evidence.get("rows_true_cols_pred") != matrix:
            raise ValueError("recomputed confusion matrix disagrees with metrics")

    return {
        "schema": "afn-error-analysis-v1",
        "status": "PENDING_QA_REVIEW",
        "evidence_kind": "TEST_FINAL",
        "n_test": len(split),
        "n_groups": len(group_sizes),
        "class_support": class_support,
        "overall": breakdown(overall),
        "strata": {name: {value: breakdown(count) for value, count in sorted(buckets.items())}
                   for name, buckets in strata.items()},
        "quality_reviewed_count": len(quality),
        "confusion_matrices": matrices,
        "provenance": {
            "record_sha256": metrics["freeze"]["record_sha256"],
            "metrics_sha256": sha256_file(args.metrics),
            "predictions_sha256": metrics["inputs"]["predictions_sha256"],
            "summary_sha256": args.summary_sha256,
            "quality_sha256": args.quality_sha256,
        },
    }


def write_outputs(out_dir, result):
    review = [
        "# AFN-047 · Phân tích bất đồng trên Test",
        "",
        "**Chờ QA duyệt phạm vi công bố và các ô có số mẫu nhỏ.**",
        "",
        "| Kết quả | Số mẫu | Tỷ lệ |",
        "| --- | ---: | ---: |",
    ]
    for name, entry in result["overall"]["outcomes"].items():
        review.append(f"| `{name}` | {entry['count']} | {entry['fraction']:.2%} |")
    review += ["", "Các phân tầng, ma trận và hash bàn giao nằm trong `error-analysis.json`.", ""]
    files = {
        "error-analysis.json": json.dumps(result, ensure_ascii=False, indent=2) + "\n",
        "error-analysis.md": "\n".join(review),
    }
    out_dir.mkdir(parents=True, exist_ok=False)
    created = []
    try:
        for name, contents in files.items():
            path = out_dir / name
            with path.open("x", encoding="utf-8", newline="\n") as stream:
                created.append(path)
                stream.write(contents)
    except OSError:
        for path in created:
            path.unlink()
        out_dir.rmdir()
        raise


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("freeze", "metrics", "predictions", "manifest", "qa-split", "locked-split", "summary", "out-dir"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--summary-sha256", required=True)
    parser.add_argument("--quality-flags", type=Path)
    parser.add_argument("--quality-sha256")
    args = parser.parse_args(argv)
    if (args.quality_flags is None) != (args.quality_sha256 is None):
        parser.error("provide both --quality-flags and --quality-sha256")
    try:
        write_outputs(args.out_dir, analyze(args))
    except (EvaluationError, OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        parser.exit(1, f"AFN-047: {error}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
