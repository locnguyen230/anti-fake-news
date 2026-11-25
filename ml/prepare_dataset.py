"""Prepare the merged DATA v1 export (PR #87) as the ML Train/Validation handoff (#34).

The export at ``data/processed/manifest.json`` is a JSON array (``sample_id``,
``source``, ``label``, ``title``, ``text``, ``pathIMG``, ``type``) without the
``afn-manifest-v1`` fields, and its split had cross-split duplicates. This step:

1. decides ``accepted``/``rejected`` per sample with label-free rules (``RULES``),
2. regroups accepted samples with the AFN-017 rules (exact body/image hash,
   near-duplicate text, title+text event candidates, image pHash), keeping
   every original DATA group together,
3. re-splits with the AFN-018 ``assign_groups`` (seed 42, 70/15/15 by group),
4. writes ``train-validation/`` (Test IDs withheld) for ML and ``qa-only/``
   (Test payload + full split) for QA.

    .venv/bin/python -m ml.prepare_dataset --manifest data/processed/manifest.json \
        --groups data/processed/groups.json --image-root data --out data/private/ml-v2

The output directory must not exist and should stay under ``data/private/``
(gitignored). Images are not copied; paths stay relative to ``--image-root``.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
from collections import Counter
from hashlib import sha256 as hash_bytes
from itertools import combinations
from pathlib import Path, PurePosixPath
from tempfile import TemporaryDirectory
from typing import Any

from PIL import Image

from ml import REPO_ROOT  # noqa: F401  (puts backend/ on sys.path)
from app.config import IMAGE_MAX_BYTES, IMAGE_MAX_PIXELS
from app.preprocessing import PreprocessingError, load_image_rgb, preprocess_text
from ml.common import MANIFEST_SCHEMA_VERSION, sha256_file
from scripts.group_samples import RULES as GROUP_RULES
from scripts.group_samples import UnionFind, normalize, phash, similarities
from scripts.split_data import NAMES, RATIOS, SEED, assign_groups

VERSION = "afn-ml-prepare-v1"
RULES = {
    "max_body_chars": 50_000,       # data-contract.md
    "max_title_chars": 500,         # data-contract.md
    "min_body_words": 50,           # shorter bodies were menus, captions or paywall stubs
    "min_image_side_px": 64,        # smaller images were favicons/placeholders
    "min_ascii_letter_ratio": 0.8,  # input_language: en
}
REASON_ORDER = (
    "missing_body", "missing_image", "image_unreadable", "image_too_small", "body_too_long",
    "title_too_long", "body_too_short", "non_english", "boilerplate_body",
)
RIGHTS = {"status": "unverified", "evidence": "FakeNewsNet recovery merged in PR #87; publisher rights not yet audited"}


def _body_key(text: str) -> str:
    return hash_bytes(normalize(text).encode("utf-8")).hexdigest()


def _image_record(path_text: str | None, image_root: Path) -> tuple[dict[str, str] | None, str | None, Any]:
    """Return (image record, rejection reason, decoded RGB image)."""
    if not path_text:
        return None, "missing_image", None
    relative = PurePosixPath(path_text)
    if relative.is_absolute() or ".." in relative.parts:
        return None, "image_unreadable", None
    path = image_root / relative
    if not path.is_file():
        return None, "missing_image", None
    data = path.read_bytes()
    if len(data) > IMAGE_MAX_BYTES:
        return None, "image_unreadable", None
    try:
        with Image.open(io.BytesIO(data)) as probe:
            media_type = Image.MIME.get(probe.format)
        rgb = load_image_rgb(data, max_pixels=IMAGE_MAX_PIXELS)
    except (OSError, Image.DecompressionBombError, PreprocessingError):
        return None, "image_unreadable", None
    if media_type not in {"image/jpeg", "image/png"}:
        return None, "image_unreadable", None
    record = {"path": relative.as_posix(), "media_type": media_type, "sha256": hash_bytes(data).hexdigest()}
    if min(rgb.size) < RULES["min_image_side_px"]:
        return record, "image_too_small", rgb
    return record, None, rgb


def decide(rows: list[dict[str, Any]], image_root: Path) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Label-free accept/reject decision for every exported row."""
    titles_by_body: dict[str, set[str]] = {}
    for row in rows:
        body = row.get("text") or ""
        if body.strip():
            titles_by_body.setdefault(_body_key(body), set()).add(normalize(row.get("title")))

    decisions, decoded = [], {}
    for row in rows:
        body, title = row.get("text") or "", row.get("title") or ""
        reasons = []
        if not body.strip():
            reasons.append("missing_body")
        image, image_reason, rgb = _image_record(row.get("pathIMG"), image_root)
        if image_reason:
            reasons.append(image_reason)
        if len(body) > RULES["max_body_chars"]:
            reasons.append("body_too_long")
        if len(title) > RULES["max_title_chars"]:
            reasons.append("title_too_long")
        if body.strip():
            if len(body.split()) < RULES["min_body_words"]:
                reasons.append("body_too_short")
            letters = [ch for ch in body if ch.isalpha()]
            if letters and sum(ch.isascii() for ch in letters) / len(letters) < RULES["min_ascii_letter_ratio"]:
                reasons.append("non_english")
            # Same body under different headlines = site footer/boilerplate, not the article.
            if len(titles_by_body[_body_key(body)]) > 1:
                reasons.append("boilerplate_body")
            try:
                preprocess_text(title, body)
            except PreprocessingError:
                reasons.append("missing_body")
        reasons = sorted(set(reasons), key=REASON_ORDER.index)
        sid = row["sample_id"]
        decisions.append({
            "schema_version": MANIFEST_SCHEMA_VERSION, "is_fixture": False, "sample_id": sid,
            "source": row["source"], "label": row["label"],
            "status": "rejected" if reasons else "accepted",
            "exclusion_reason": reasons[0] if reasons else None, "all_reasons": reasons,
            "title": title, "body": body, "group_id": None, "image": image, "rights": RIGHTS,
        })
        if not reasons:
            decoded[sid] = rgb
    return decisions, decoded


def regroup(rows: dict[str, dict[str, Any]], image_hashes: dict[str, int],
            original_groups: dict[str, str]) -> tuple[dict[str, str], list[list[Any]]]:
    """AFN-017 rules minus URL/publisher/event keys, which the export does not carry."""
    ids = sorted(rows)
    components = UnionFind(ids)
    edges: list[list[Any]] = []

    def connect(left: str, right: str, kind: str, value: Any = None) -> None:
        components.union(left, right)
        edges.append([left, right, kind, value])

    seen: dict[tuple[str, str], str] = {}
    for sid in ids:
        keys = [("body_sha256", _body_key(rows[sid]["body"])), ("image_sha256", rows[sid]["image"]["sha256"])]
        if original_groups.get(sid):
            keys.append(("data_group", original_groups[sid]))
        for key in keys:
            if key in seen:
                connect(seen[key], sid, key[0])
            else:
                seen[key] = sid

    titles = similarities([normalize(rows[sid]["title"]) for sid in ids])
    bodies = similarities([normalize(rows[sid]["body"]) for sid in ids])
    for i, j in combinations(range(len(ids)), 2):
        left, right = ids[i], ids[j]
        title, body = float(titles[i, j]), float(bodies[i, j])
        if body >= GROUP_RULES["text_near"]:
            connect(left, right, "text_near", round(body, 6))
        if title >= GROUP_RULES["title_candidate"]:
            weight = GROUP_RULES["title_weight"]
            score = weight * title + (1 - weight) * body
            if score >= GROUP_RULES["title_text"] and body >= GROUP_RULES["text_support"]:
                connect(left, right, "event_candidate", round(score, 6))
        distance = (image_hashes[left] ^ image_hashes[right]).bit_count()
        if distance <= GROUP_RULES["phash_distance"]:
            connect(left, right, "image_near", distance)

    members: dict[str, list[str]] = {}
    for sid in ids:
        members.setdefault(components.root(sid), []).append(sid)
    mapping = {sid: f"group_{index:04d}"
               for index, key in enumerate(sorted(members), start=1) for sid in members[key]}
    return mapping, edges


def _write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8", newline="\n") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")


def _write_split(path: Path, partitions: dict[str, list[str]], mapping: dict[str, str], *, hide_test: bool) -> None:
    with path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh, lineterminator="\n")
        writer.writerow(("sample_id", "split", "group_id"))
        for name in NAMES:
            for sid in partitions[name]:
                writer.writerow(("" if hide_test and name == "test" else sid, name, mapping[sid]))


def prepare(manifest: Path, groups: Path | None, image_root: Path, out: Path) -> dict[str, Any]:
    if out.exists():
        raise FileExistsError(f"{out} exists; choose a new directory")
    image_root = image_root.resolve(strict=True)
    exported = json.loads(manifest.read_text(encoding="utf-8"))
    if not isinstance(exported, list) or not exported:
        raise ValueError("expected a non-empty JSON array of samples")
    ids = [row.get("sample_id") for row in exported]
    if len(set(ids)) != len(ids) or not all(isinstance(sid, str) and sid for sid in ids):
        raise ValueError("sample_id must be unique non-empty strings")
    if any(row.get("label") not in {"fake", "real"} for row in exported):
        raise ValueError("label must be fake or real")
    original_groups = json.loads(groups.read_text(encoding="utf-8")) if groups else {}

    decisions, decoded = decide(exported, image_root)
    accepted = {row["sample_id"]: row for row in decisions if row["status"] == "accepted"}
    if not accepted:
        raise ValueError("no accepted samples")
    mapping, edges = regroup(accepted, {sid: phash(img) for sid, img in decoded.items()}, original_groups)
    partitions = assign_groups(accepted, mapping)
    for row in decisions:
        row["group_id"] = mapping.get(row["sample_id"])

    report: dict[str, Any] = {
        "version": VERSION, "rules": RULES, "group_rules": GROUP_RULES, "seed": SEED,
        "inputs": {"manifest_sha256": sha256_file(manifest),
                   "groups_sha256": sha256_file(groups) if groups else None},
        "exported": len(decisions), "accepted": len(accepted),
        "excluded_by_reason": dict(Counter(r["exclusion_reason"] for r in decisions if r["exclusion_reason"])),
        "group_count": len(set(mapping.values())),
        "group_sizes": dict(sorted(Counter(Counter(mapping.values()).values()).items())),
        "edge_counts": dict(Counter(edge[2] for edge in edges)),
        "splits": {},
    }
    for name, target in zip(NAMES, RATIOS, strict=True):
        members = partitions[name]
        report["splits"][name] = {
            "samples": len(members), "groups": len({mapping[sid] for sid in members}),
            "target_fraction": target, "actual_fraction": round(len(members) / len(accepted), 4),
            "by_source_label": dict(sorted(Counter(
                f'{accepted[sid]["source"]}:{accepted[sid]["label"]}' for sid in members).items())),
        }

    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as temporary:
        stage = Path(temporary) / "release"
        ml_dir, qa_dir = stage / "train-validation", stage / "qa-only"
        ml_dir.mkdir(parents=True)
        qa_dir.mkdir()
        clean = [{k: v for k, v in row.items() if k != "all_reasons"} for row in decisions]
        by_id = {row["sample_id"]: row for row in clean}
        _write_jsonl(ml_dir / "manifest.jsonl",
                     [by_id[sid] for name in ("train", "validation") for sid in partitions[name]])
        _write_split(ml_dir / "split.csv", partitions, mapping, hide_test=True)
        _write_jsonl(qa_dir / "manifest-test.jsonl", [by_id[sid] for sid in partitions["test"]])
        _write_split(qa_dir / "split.csv", partitions, mapping, hide_test=False)
        _write_jsonl(qa_dir / "decisions.jsonl", decisions)
        (qa_dir / "grouping-edges.json").write_text(json.dumps(edges, indent=1) + "\n", encoding="utf-8")
        report["sha256"] = {f.relative_to(stage).as_posix(): sha256_file(f)
                            for f in sorted(stage.rglob("*")) if f.is_file()}
        (stage / "prepare-report.json").write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        stage.rename(out)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--groups", type=Path, help="DATA groups.json; members stay together")
    parser.add_argument("--image-root", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = prepare(args.manifest, args.groups, args.image_root, args.out)
    except (OSError, ValueError) as error:
        parser.exit(1, f"{error}\n")
    print(f"{report['accepted']}/{report['exported']} accepted, {report['group_count']} groups")
    print("excluded:", report["excluded_by_reason"])
    for name, info in report["splits"].items():
        print(f"  {name:<10} {info['samples']:>4} samples  {info['groups']:>4} groups")
    print(f"ML handoff: {args.out / 'train-validation'} (Test IDs withheld)")


if __name__ == "__main__":
    main()
