"""ml.prepare_dataset on a synthetic export shaped like data/processed/manifest.json."""

import csv
import json
import random

import pytest
from PIL import Image

pytest.importorskip("jsonschema")  # scripts.group_samples/split_data import the DATA validator

from ml.common import load_dataset  # noqa: E402
from ml.prepare_dataset import RULES, decide, prepare  # noqa: E402

VOCAB = [f"w{i}" for i in range(4000)]


def _body(seed, words=80):
    rng = random.Random(seed)
    return " ".join(rng.choice(VOCAB) for _ in range(words)) + "."


def _image(path, seed, side=96):
    rng = random.Random(seed)
    img = Image.new("RGB", (side, side))
    img.putdata([(rng.randrange(256), rng.randrange(256), rng.randrange(256)) for _ in range(side * side)])
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path)
    return path.relative_to(path.parents[1]).as_posix()


def _row(root, sid, label, seed, **overrides):
    row = {"sample_id": sid, "source": "politifact" if seed % 2 else "gossipcop", "label": label,
           "title": f"Headline {sid}", "text": _body(seed), "type": "full", "group_event": None,
           "pathIMG": _image(root / "images" / f"{sid}.png", seed)}
    row.update(overrides)
    return row


@pytest.fixture
def export(tmp_path):
    root = tmp_path / "data"
    rows = [_row(root, f"s{i:02d}", "fake" if i % 2 else "real", i) for i in range(30)]
    # Same image as s00 -> must share a group and a split.
    dup_img = _row(root, "dup-img", "fake", 100)
    dup_img["pathIMG"] = rows[0]["pathIMG"]
    # Same body as s01, same headline -> real duplicate article, grouped not rejected.
    dup_body = _row(root, "dup-body", "real", 101, text=rows[1]["text"], title=rows[1]["title"])
    bad = [
        _row(root, "no-img", "fake", 200, pathIMG=None, type="noimg"),
        _row(root, "no-text", "real", 201, text=None, type="notext"),
        _row(root, "short", "fake", 202, text="Menu Home News Sports"),
        _row(root, "long", "real", 203, text="word " * 12_000),
        _row(root, "russian", "fake", 204, text=" ".join(["Брэд Питт биография"] * 30)),
        _row(root, "footer-a", "real", 205, text="Copyright footer " * 30, title="Story A"),
        _row(root, "footer-b", "fake", 206, text="Copyright footer " * 30, title="Story B"),
    ]
    tiny = _row(root, "tiny", "real", 207)
    tiny["pathIMG"] = _image(root / "images" / "tiny.png", 207, side=32)
    all_rows = rows + [dup_img, dup_body, tiny] + bad
    manifest = root / "processed" / "manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_text(json.dumps(all_rows), encoding="utf-8")
    return manifest, root


def test_rejections_are_label_free_and_reasoned(export):
    manifest, root = export
    rows = json.loads(manifest.read_text())
    decisions, _ = decide(rows, root)
    reasons = {d["sample_id"]: d["exclusion_reason"] for d in decisions}
    assert reasons["no-img"] == "missing_image"
    assert reasons["no-text"] == "missing_body"
    assert reasons["short"] == "body_too_short"
    assert reasons["long"] == "body_too_long"
    assert reasons["russian"] == "non_english"
    assert reasons["footer-a"] == reasons["footer-b"] == "boilerplate_body"
    assert reasons["tiny"] == "image_too_small"
    assert reasons["dup-body"] is None and reasons["dup-img"] is None

    flipped = [dict(r, label="real" if r["label"] == "fake" else "fake") for r in rows]
    flipped_decisions, _ = decide(flipped, root)
    assert [d["status"] for d in flipped_decisions] == [d["status"] for d in decisions]
    assert RULES["max_body_chars"] == 50_000


def test_prepare_groups_duplicates_hides_test_and_loads(export, tmp_path):
    manifest, root = export
    out = tmp_path / "private" / "ml-v2"
    report = prepare(manifest, None, root, out)
    assert report["accepted"] == 32 and report["exported"] == 40

    with (out / "qa-only" / "split.csv").open() as fh:
        full = {r["sample_id"]: r for r in csv.DictReader(fh)}
    assert full["dup-img"]["group_id"] == full["s00"]["group_id"]
    assert full["dup-img"]["split"] == full["s00"]["split"]
    assert full["dup-body"]["group_id"] == full["s01"]["group_id"]

    with (out / "train-validation" / "split.csv").open() as fh:
        ml_rows = list(csv.DictReader(fh))
    test_rows = [r for r in ml_rows if r["split"] == "test"]
    assert test_rows and all(r["sample_id"] == "" for r in test_rows)
    ml_ids = {json.loads(line)["sample_id"] for line in (out / "train-validation" / "manifest.jsonl").open()}
    assert ml_ids.isdisjoint({sid for sid, r in full.items() if r["split"] == "test"})

    dataset = load_dataset(out / "train-validation" / "manifest.jsonl", out / "train-validation" / "split.csv",
                           image_root=root)
    assert dataset.locked_counts["test"] == len(test_rows)
    assert len(dataset.rows("train")) + len(dataset.rows("validation")) == len(ml_ids)
    assert not dataset.is_fixture

    with pytest.raises(FileExistsError):
        prepare(manifest, None, root, out)


def test_original_data_groups_stay_together(export, tmp_path):
    manifest, root = export
    groups = tmp_path / "groups.json"
    groups.write_text(json.dumps({"s05": "group_0001", "s06": "group_0001"}))
    out = tmp_path / "out"
    prepare(manifest, groups, root, out)
    with (out / "qa-only" / "split.csv").open() as fh:
        full = {r["sample_id"]: r for r in csv.DictReader(fh)}
    assert full["s05"]["group_id"] == full["s06"]["group_id"]
