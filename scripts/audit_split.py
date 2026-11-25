"""Audit an AFN-018 release or the ml-v2 candidate without opening Test articles or images."""

import argparse
import csv
import json
from collections import Counter
from itertools import product
from pathlib import Path
from re import fullmatch

import ml  # Makes the shared Backend package importable from the repository root.
from ml.common import load_dataset, load_experiment_config, order_digest, read_split_file, sha256_file
from scripts.group_samples import VERSION as GROUPING_VERSION, normalize


def verified_file(path: Path, expected: str) -> Path:
    if not fullmatch(r"[0-9a-f]{64}", expected) or sha256_file(path) != expected:
        raise ValueError(f"checksum mismatch for {path.name}")
    return path


def audit_release(release: Path, grouping: Path, *, summary_sha: str, audit_sha: str) -> dict:
    summary_path = verified_file(release / "qa-only" / "split-summary.json", summary_sha)
    summary = json.loads(summary_path.read_bytes())
    evidence_path = verified_file(grouping / "grouping-audit.json", audit_sha)
    evidence = json.loads(evidence_path.read_bytes())
    if (not fullmatch(r"v[1-9][0-9]*", summary["dataset_version"]) or summary["seed"] != 42
            or evidence["version"] != GROUPING_VERSION or evidence["pending"] != 0
            or summary["manifest_sha256"] != evidence["manifest_sha256"]
            or summary["groups_sha256"] != evidence["groups_sha256"]
            or summary["is_fixture"] is not evidence["fixture"]):
        raise ValueError("inconsistent split or grouping provenance")

    mapping_path = verified_file(grouping / "groups.json", summary["groups_sha256"])
    mapping = json.loads(mapping_path.read_bytes())
    hashes = summary["sha256"]
    qa_csv = verified_file(release / "qa-only" / "split.csv", hashes["qa-only/split.csv"])
    ml_csv = verified_file(release / "train-validation" / "split.csv", hashes["train-validation/split.csv"])
    manifest = verified_file(release / "train-validation" / "manifest.jsonl",
                             hashes["train-validation/manifest.jsonl"])
    assignments, _ = read_split_file(qa_csv, include_test=True)
    ml_assignments, locked_count = read_split_file(ml_csv, include_test=False)
    if ({sid: group for sid, (_, group) in assignments.items()} != mapping
            or dict(Counter(mapping.values())) != evidence["group_sizes"]
            or len(assignments) != evidence["accepted"]):
        raise ValueError("split membership differs from the approved group mapping")
    dataset_counts = Counter(split for split, _ in assignments.values())
    for split, fraction in zip(("train", "validation", "test"), (0.7, 0.15, 0.15), strict=True):
        entry = summary["splits"][split]
        if not dataset_counts[split] or entry["samples"] != dataset_counts[split] or entry["target_fraction"] != fraction:
            raise ValueError("split totals or allocation targets differ from the QA summary")
    visible = {sid: row for sid, row in assignments.items() if row[0] != "test"}
    with ml_csv.open(encoding="utf-8", newline="") as stream:
        ml_test_groups = Counter(row["group_id"].strip() for row in csv.DictReader(stream) if row["split"].strip() == "test")
    qa_test_groups = Counter(group for split, group in assignments.values() if split == "test")
    if visible != ml_assignments or locked_count != dataset_counts["test"] or ml_test_groups != qa_test_groups:
        raise ValueError("ML handoff does not match the locked QA split")

    edges = evidence["edges"]
    if Counter(edge[2] for edge in edges) != evidence["edge_counts"]:
        raise ValueError("grouping relationships differ from the audit totals")
    for left, right, _, _ in edges:
        if left not in assignments or right not in assignments or assignments[left] != assignments[right]:
            raise ValueError("a duplicate, publisher or event relationship crosses a group or split")
    review_candidates = sum(assignments[left][0] != assignments[right][0]
                            for left, right, _, _, _ in evidence["event_candidates"])

    data = load_dataset(manifest, ml_csv, ml_csv.parent / "images")
    if data.is_fixture is not summary["is_fixture"]:
        raise ValueError("fixture marker differs from the QA summary")
    split_by_image = {}
    image_root = (ml_csv.parent / "images").resolve()
    for split in ("train", "validation"):
        rows = data.rows(split)
        counts = Counter(row.label for row in rows)
        if counts != summary["splits"][split]["by_label"]:
            raise ValueError("label counts differ from the QA summary")
        for row in rows:
            if row.image_path is None or row.image_sha256 is None:
                raise ValueError("image metadata is missing")
            path = row.image_path.resolve()
            if not path.is_relative_to(image_root):
                raise ValueError("image path leaves the Train/Validation handoff")
            verified_file(path, row.image_sha256)
            if split_by_image.setdefault(row.image_sha256, split) != split:
                raise ValueError("image checksum is missing or crosses Train and Validation")
    missing_labels = {name: split["missing_labels"] for name, split in summary["splits"].items()}
    status = "BLOCKED" if review_candidates or any(missing_labels.values()) else "PASS"
    return {"status": status, "dataset_version": summary["dataset_version"], "is_fixture": data.is_fixture,
            "manifest_sha256": data.manifest_sha256, "split_sha256": data.split_sha256,
            "sample_counts": dict(dataset_counts), "relationship_counts": evidence["edge_counts"],
            "missing_labels": missing_labels, "missing_event": evidence["missing_event"],
            "missing_publisher": evidence["missing_publisher"], "cross_split_event_candidates": review_candidates}


def audit_validation_run(data, selected: dict, search: dict, config_path: Path) -> None:
    """Check the saved selection from its scores and inputs, without fitting a model."""
    if (selected["run_id"] != search["run_id"]
            or selected["inputs"] != search["inputs"]
            or selected["test_split"] != search["test_split"]
            or selected["test_split"] != {"loaded": False, "locked_rows": data.locked_counts["test"]}
            or selected["evidence_kind"] != "VALIDATION_ONLY"
            or search["evidence_kind"] != selected["evidence_kind"]
            or selected["selection_split"] != "validation"):
        raise ValueError("inconsistent Validation run provenance")
    inputs = selected["inputs"]
    if (inputs["manifest_sha256"] != data.manifest_sha256 or inputs["split_sha256"] != data.split_sha256):
        raise ValueError("candidate dataset differs from the ML Validation run")
    verified_file(config_path, inputs["experiment_config_sha256"])

    config = load_experiment_config(config_path)
    selection = config["selection"]
    if (search["experiment_config"] != config or config["fit_split"] != "train"
            or config["refit_on_train_and_validation"]
            or selection["split"] != "validation"
            or selection["tie_break_order"] != ["closest_threshold_to_0_5", "lower_c", "lower_threshold"]
            or selected["metric"] != selection["metric"]
            or set(selected["configurations"]) != set(config["configurations"])
            or set(search["results"]) != set(config["configurations"])):
        raise ValueError("saved runner configuration differs from the recorded protocol")
    pairs = set(product(selection["c_candidates"], selection["threshold_candidates"]))
    for name, chosen in selected["configurations"].items():
        result = search["results"][name]
        grid = result["grid"]
        if len(grid) != len(pairs) or {(row["C"], row["threshold"]) for row in grid} != pairs:
            raise ValueError(f"incomplete Validation grid for {name}")
        decimals = selection["metric_decimal_places"]
        best = min(grid, key=lambda row: (
            -round(row["macro_f1"], decimals), round(abs(row["threshold"] - 0.5), decimals),
            row["C"], row["threshold"],
        ))
        for record in (chosen, result["selected"]):
            if (record["C"], record["threshold"], record["validation_macro_f1"]) != (
                best["C"], best["threshold"], best["macro_f1"]
            ):
                raise ValueError(f"Validation selection differs for {name}")
        for split in ("train", "validation"):
            rows = data.rows(split)
            digest = order_digest([row.sample_id for row in rows])
            if any(record[f"{split}_order_sha256"] != digest or record[f"n_{split}"] != len(rows)
                   for record in (chosen, result)):
                raise ValueError(f"ordered {split} membership differs for {name}")


def audit_ml_v2(release: Path, image_root: Path, selected_path: Path, search_path: Path,
                config_path: Path) -> dict:
    """Cross-check the pinned candidate and grouped QA metadata without loading Test payload."""
    report = json.loads((release / "prepare-report.json").read_bytes())
    if report["version"] != "afn-ml-prepare-v1" or report["seed"] != 42:
        raise ValueError("unexpected candidate dataset version or seed")
    hashes = report["sha256"]
    qa_csv = verified_file(release / "qa-only/split.csv", hashes["qa-only/split.csv"])
    ml_csv = verified_file(release / "train-validation/split.csv", hashes["train-validation/split.csv"])
    manifest = verified_file(release / "train-validation/manifest.jsonl", hashes["train-validation/manifest.jsonl"])
    edges_path = verified_file(release / "qa-only/grouping-edges.json", hashes["qa-only/grouping-edges.json"])
    qa, _ = read_split_file(qa_csv, include_test=True)
    ml, locked = read_split_file(ml_csv, include_test=False)
    with ml_csv.open(encoding="utf-8", newline="") as stream:
        locked_groups = Counter(row["group_id"] for row in csv.DictReader(stream) if row["split"] == "test")
    if (ml != {sid: row for sid, row in qa.items() if row[0] != "test"}
            or locked_groups != Counter(gid for split, gid in qa.values() if split == "test")
            or locked != sum(locked_groups.values())):
        raise ValueError("QA and redacted ML split assignments differ")
    edges = json.loads(edges_path.read_bytes())
    if (Counter(kind for _, _, kind, _ in edges) != report["edge_counts"]
            or any(left not in qa or right not in qa or qa[left] != qa[right] for left, right, _, _ in edges)):
        raise ValueError("grouping evidence crosses a split or group, or differs from reported edge counts")

    data = load_dataset(manifest, ml_csv, image_root)
    if data.is_fixture:
        raise ValueError("expected research candidate data")
    seen = {}
    for split in ("train", "validation"):
        for row in data.rows(split):
            if row.image_path is None or row.image_sha256 is None:
                raise ValueError("image metadata missing from Train/Validation")
            path = row.image_path.resolve()
            if not path.is_relative_to(image_root.resolve()):
                raise ValueError("image path leaves the configured image root")
            verified_file(path, row.image_sha256)
            for key in (("image", row.image_sha256), ("body", normalize(row.body)),
                        ("title", normalize(row.title or ""))):
                if key[1] and seen.setdefault(key, split) != split:
                    raise ValueError("exact image, body or title repeats across Train and Validation")
    counts = Counter(split for split, _ in qa.values())
    groups = {split: {gid for name, gid in qa.values() if name == split} for split in counts}
    visible_breakdown = {"train": Counter(), "validation": Counter()}
    with manifest.open(encoding="utf-8") as stream:
        for line in stream:
            row = json.loads(line)
            split, _ = ml[row["sample_id"]]
            visible_breakdown[split][f'{row["source"]}:{row["label"]}'] += 1
    missing_labels = {}
    for split in ("train", "validation", "test"):
        summary = report["splits"][split]
        breakdown = Counter()
        for source_label, count in summary["by_source_label"].items():
            breakdown[source_label.rsplit(":", 1)[1]] += count
        if (counts[split] != summary["samples"] or len(groups[split]) != summary["groups"]
                or sum(breakdown.values()) != counts[split] or not counts[split]):
            raise ValueError("candidate sample, group or label counts differ")
        if split in visible_breakdown and visible_breakdown[split] != summary["by_source_label"]:
            raise ValueError("candidate source and label counts differ from Train/Validation manifest")
        missing_labels[split] = sorted({"fake", "real"} - {label for label, count in breakdown.items() if count})
    audit_validation_run(data, json.loads(selected_path.read_bytes()), json.loads(search_path.read_bytes()), config_path)
    # The ml-v2 export omits publisher/event identity by design. The edge ledger
    # cannot rule out relationships that require either of those identifiers.
    return {"status": "BLOCKED", "checked": "candidate split and recorded Validation run",
            "dataset_version": "ml-v2", "prepare_version": report["version"],
            "manifest_sha256": data.manifest_sha256,
            "split_sha256": data.split_sha256, "sample_counts": dict(counts),
            "group_counts": {split: len(ids) for split, ids in groups.items()},
            "relationship_counts": report["edge_counts"], "missing_labels": missing_labels,
            "blockers": ["publisher/event provenance unavailable in ml-v2; DATA review required"]}

def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release", type=Path, required=True)
    parser.add_argument("--grouping", type=Path)
    parser.add_argument("--summary-sha256", help="AFN-018 summary hash from the QA handoff")
    parser.add_argument("--audit-sha256", help="AFN-017 grouping audit hash from the QA handoff")
    parser.add_argument("--ml-v2", action="store_true", help="Audit the reconstructed AFN-034 candidate")
    parser.add_argument("--image-root", type=Path, help="Root of the original DATA images for ml-v2")
    parser.add_argument("--selected-models", type=Path, default=Path("configs/selected-models.json"))
    parser.add_argument("--validation-search", type=Path, default=Path("reports/validation-search.json"))
    parser.add_argument("--experiment-config", type=Path, default=Path("configs/experiment.yaml"))
    args = parser.parse_args()
    if args.ml_v2 and not args.image_root:
        parser.error("--ml-v2 requires --image-root")
    if not args.ml_v2 and not all((args.grouping, args.summary_sha256, args.audit_sha256)):
        parser.error("AFN-018 audit requires --grouping, --summary-sha256 and --audit-sha256")
    try:
        if args.ml_v2:
            result = audit_ml_v2(args.release, args.image_root, args.selected_models,
                                 args.validation_search, args.experiment_config)
        else:
            result = audit_release(args.release, args.grouping, summary_sha=args.summary_sha256,
                                   audit_sha=args.audit_sha256)
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        print(json.dumps({"status": "BLOCKED", "reason": "missing or inconsistent handoff evidence"}))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return int(result["status"] != "PASS")


if __name__ == "__main__":
    raise SystemExit(main())
