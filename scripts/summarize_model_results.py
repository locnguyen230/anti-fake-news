"""Summarize a normalized AFN-051 confusion-matrix export for the report."""

import argparse
import json
from pathlib import Path


LABELS = ("fake", "real")
CONFIGURATIONS = ("text-only", "image-only", "multimodal")
SCHEMA = "afn-report-metrics-v1"


def summarize(document: dict) -> dict:
    if document.get("schema") != SCHEMA:
        raise ValueError(f"Expected schema {SCHEMA}")
    evidence_kind = document.get("evidence_kind")
    if evidence_kind not in ("FIXTURE_NOT_RESEARCH", "TEST_FINAL"):
        raise ValueError("Expected a fixture or final Test evidence label")
    if document.get("labels") != list(LABELS):
        raise ValueError("Expected confusion matrix rows and columns in fake, real order")

    matrices = document.get("confusion_matrices")
    if not isinstance(matrices, dict) or set(matrices) != set(CONFIGURATIONS):
        raise ValueError("Expected exactly text-only, image-only and multimodal matrices")

    configurations = {}
    expected_support = None
    for name in CONFIGURATIONS:
        matrix = matrices[name]
        if (not isinstance(matrix, list) or len(matrix) != 2
                or any(not isinstance(row, list) or len(row) != 2 for row in matrix)
                or any(type(count) is not int or count < 0 for row in matrix for count in row)):
            raise ValueError(f"{name}: expected a 2×2 matrix of nonnegative integers")
        support = tuple(sum(row) for row in matrix)
        if not sum(support) or (expected_support is not None and support != expected_support):
            raise ValueError("Expected the same nonempty class support for all configurations")
        expected_support = support

        per_class = {}
        for index, label in enumerate(LABELS):
            correct = matrix[index][index]
            predicted = sum(row[index] for row in matrix)
            per_class[label] = {
                "precision": correct / predicted if predicted else 0.0,
                "recall": correct / support[index] if support[index] else 0.0,
                "f1": 2 * correct / (predicted + support[index]) if predicted + support[index] else 0.0,
                "support": support[index],
            }
        configurations[name] = {
            "accuracy": (matrix[0][0] + matrix[1][1]) / sum(support),
            "macro_f1": sum(metrics["f1"] for metrics in per_class.values()) / len(LABELS),
            "per_class": per_class,
            "rows_true_cols_pred": matrix,
        }

    return {
        "schema": SCHEMA,
        "evidence_kind": evidence_kind,
        "labels": list(LABELS),
        "missing_reference_labels": [label for label, count in zip(LABELS, expected_support) if count == 0],
        "configurations": configurations,
        "delta_macro_f1_mm_minus_text": (
            configurations["multimodal"]["macro_f1"] - configurations["text-only"]["macro_f1"]
        ),
    }


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("metrics", type=Path)
    args = parser.parse_args()
    try:
        document = json.loads(args.metrics.read_text(encoding="utf-8"))
        if not isinstance(document, dict):
            raise ValueError("Expected one JSON object")
        results = summarize(document)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
