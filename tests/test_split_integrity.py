"""AFN-029 guards for audited relationships and the locked ML handoff."""

import json
from collections import Counter

import pytest
from PIL import Image

from ml.common import load_dataset, sha256_file
from ml.train_text import fit_text_vectorizer
from scripts.audit_split import audit_provenance, audit_release
from scripts.group_samples import VERSION as GROUPING_VERSION


def write_json(path, value):
    path.write_text(json.dumps(value), encoding="utf-8")
    return sha256_file(path)


@pytest.fixture
def handoff(tmp_path):
    release, grouping = tmp_path / "release", tmp_path / "grouping"
    qa, ml = release / "qa-only", release / "train-validation"
    images = ml / "images"
    for path in (qa, images, grouping):
        path.mkdir(parents=True)
    partitions = {"train": [("a", "g1"), ("b", "g1"), ("c", "g1")],
                  "validation": [("d", "g2"), ("e", "g3")], "test": [("f", "g4"), ("g", "g5")]}
    mapping = {sid: group for pairs in partitions.values() for sid, group in pairs}
    groups_sha = write_json(grouping / "groups.json", mapping)
    rows, qa_csv, ml_csv = [], ["sample_id,split,group_id\n"], ["sample_id,split,group_id\n"]
    stats = {}
    for (split, pairs), fraction in zip(partitions.items(), (0.7, 0.15, 0.15), strict=True):
        labels = ["fake", "real", "fake"][:len(pairs)]
        stats[split] = {"samples": len(pairs), "target_fraction": fraction, "missing_labels": [],
                        "by_label": dict(Counter(labels))}
        for (sid, group), label in zip(pairs, labels, strict=True):
            qa_csv.append(f"{sid},{split},{group}\n")
            ml_csv.append(f"{sid if split != 'test' else ''},{split},{group}\n")
            if split == "test":
                continue
            image_path = images / f"{sid}.png"
            with Image.new("RGB", (2, 2), (ord(sid), 50, 20)) as image:
                image.save(image_path)
            rows.append({"sample_id": sid, "group_id": group, "schema_version": "afn-manifest-v1",
                         "status": "accepted", "body": "Synthetic article", "label": label, "is_fixture": True,
                         "image": {"path": image_path.name, "sha256": sha256_file(image_path)}})
    (qa / "split.csv").write_text("".join(qa_csv), encoding="utf-8")
    (ml / "split.csv").write_text("".join(ml_csv), encoding="utf-8")
    (ml / "manifest.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    summary = {"dataset_version": "v1", "seed": 42, "manifest_sha256": "0" * 64, "is_fixture": True,
               "groups_sha256": groups_sha, "splits": stats,
               "sha256": {p: sha256_file(release / p) for p in ("qa-only/split.csv", "train-validation/split.csv",
                                                              "train-validation/manifest.jsonl")}}
    evidence = {"version": GROUPING_VERSION, "fixture": True, "pending": 0, "accepted": len(mapping),
                "manifest_sha256": summary["manifest_sha256"], "groups_sha256": groups_sha,
                "group_sizes": dict(Counter(mapping.values())), "missing_event": 5, "missing_publisher": 0,
                "edge_counts": {"publisher": 1, "event": 1}, "event_candidates": [],
                "edges": [["a", "b", "publisher", None], ["b", "c", "event", None]]}
    return release, grouping, summary, evidence


def audit(handoff):
    release, grouping, summary, evidence = handoff
    return audit_release(release, grouping, summary_sha=write_json(release / "qa-only" / "split-summary.json", summary),
                         audit_sha=write_json(grouping / "grouping-audit.json", evidence))


def test_audit_checks_transitive_relationships_without_test_payload(handoff):
    result = audit(handoff)
    assert result["status"] == "PASS" and result["is_fixture"]
    assert result["sample_counts"] == {"train": 3, "validation": 2, "test": 2}
    assert result["relationship_counts"] == {"event": 1, "publisher": 1}
    assert not (handoff[0] / "qa-only" / "manifest.jsonl").exists()


def test_audit_rejects_relationship_across_the_locked_test_split(handoff):
    evidence = handoff[3]
    evidence["edges"].append(["c", "f", "image_hash", None])
    evidence["edge_counts"]["image_hash"] = 1
    with pytest.raises(ValueError, match="crosses a group or split"):
        audit(handoff)


def test_audit_rejects_changed_files_and_reports_unresolved_candidates(handoff):
    release, _, _, evidence = handoff
    evidence["event_candidates"].append(["c", "f", 0.9, 0.3, False])
    assert audit(handoff)["status"] == "BLOCKED"
    (release / "train-validation" / "images" / "a.png").write_bytes(b"changed")
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit(handoff)


def test_tfidf_rejects_validation_rows_in_fit(handoff, ml_config):
    path = handoff[0] / "train-validation"
    data = load_dataset(path / "manifest.jsonl", path / "split.csv")
    with pytest.raises(ValueError, match="Train"):
        fit_text_vectorizer(data.rows("train") + data.rows("validation"), ml_config)


def test_provenance_checks_reviewed_keys_without_test_payload(tmp_path):
    csv_path = tmp_path / "provenance.csv"
    csv_path.write_text("sample_id,publisher,event_id\na,Publisher A,one\nb,publisher a,two\nc,Publisher B,two\n",
                        encoding="utf-8")
    assignments = {"a": ("train", "g1"), "b": ("train", "g1"), "c": ("test", "g2")}

    result = audit_provenance(csv_path, sha256_file(csv_path), assignments)

    assert result["samples_checked"] == 3
    assert result["missing"] == {"publisher": 0, "event_id": 0}
    assert result["cross_group"] == result["cross_split"] == {"publisher": 0, "event_id": 1}


def test_provenance_reports_missing_values_and_checks_digest_and_coverage(tmp_path):
    csv_path = tmp_path / "provenance.csv"
    csv_path.write_text("sample_id,publisher,event_id\na,Publisher A,\n", encoding="utf-8")
    digest = sha256_file(csv_path)
    assignments = {"a": ("train", "g1")}

    assert audit_provenance(csv_path, digest, assignments)["missing"] == {"publisher": 0, "event_id": 1}
    with pytest.raises(ValueError, match="missing split assignments"):
        audit_provenance(csv_path, digest, assignments | {"b": ("test", "g2")})
    csv_path.write_text("sample_id,publisher,event_id\na,Publisher A,one\na,Publisher B,two\n", encoding="utf-8")
    with pytest.raises(ValueError, match="checksum mismatch"):
        audit_provenance(csv_path, digest, assignments)
    with pytest.raises(ValueError, match="duplicate or extra sample"):
        audit_provenance(csv_path, sha256_file(csv_path), assignments)
