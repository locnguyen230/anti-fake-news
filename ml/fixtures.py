"""Synthetic, self-contained Train/Validation/Test fixture for ML smoke tests.

Writes an ``afn-manifest-v1`` JSONL (``is_fixture: true``), a ``sample_id,split``
CSV and generated PNG images. Contains no research data; any score obtained on
it is a pipeline smoke check only.

    .venv/bin/python -m ml.fixtures --out cache/ml-fixture
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
from pathlib import Path

import numpy as np

# Two overlapping vocabularies make the task learnable but not trivial.
_FAKE_WORDS = ["shocking", "secret", "miracle", "exposed", "hoax", "viral", "banned", "cure"]
_REAL_WORDS = ["senate", "report", "official", "budget", "court", "study", "agency", "vote"]
_SHARED = ["the", "news", "people", "said", "today", "state", "new", "claims", "video", "week"]

FIXTURE_SPLIT_COUNTS = {"train": 14, "validation": 4, "test": 3}  # per label


def _text(rng: np.random.Generator, label: str, n_words: int) -> str:
    own = _FAKE_WORDS if label == "fake" else _REAL_WORDS
    other = _REAL_WORDS if label == "fake" else _FAKE_WORDS
    pool = own * 3 + _SHARED * 2 + other  # mostly own words, some confusion
    return " ".join(rng.choice(pool, size=n_words)).capitalize() + "."


def _png(rng: np.random.Generator, label: str) -> bytes:
    from PIL import Image

    base = np.array([200, 60, 60] if label == "fake" else [60, 90, 200], dtype=np.int16)
    noise = rng.integers(-50, 50, size=(48, 64, 3))
    arr = np.clip(base + noise, 0, 255).astype(np.uint8)
    buf = io.BytesIO()
    Image.fromarray(arr).save(buf, format="PNG")
    return buf.getvalue()


def write_synthetic_dataset(out_dir: Path | str, *, seed: int = 42,
                            counts: dict[str, int] | None = None) -> dict[str, Path]:
    out = Path(out_dir)
    (out / "images").mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(seed)
    counts = counts or FIXTURE_SPLIT_COUNTS
    rows, assignment = [], []
    for label in ("fake", "real"):
        idx = 0
        for split, n in counts.items():
            for _ in range(n):
                source_id = f"fx-{label}-{idx:03d}"
                sid = f"politifact:{label}:{source_id}"
                image_bytes = _png(rng, label)
                rel = f"images/{source_id}.png"
                (out / rel).write_bytes(image_bytes)
                rows.append({
                    "schema_version": "afn-manifest-v1",
                    "is_fixture": True,
                    "sample_id": sid,
                    "source_id": source_id,
                    "source": "politifact",
                    "label": label,
                    "status": "accepted",
                    "publisher": "example.test",
                    "source_url": f"https://example.test/{source_id}",
                    "title": _text(rng, label, 5),
                    "body": _text(rng, label, int(rng.integers(20, 60))),
                    "retrieved_at": "2026-11-23T00:00:00Z",
                    "event_id": None,
                    "group_id": f"fx-group-{label}-{idx:03d}",
                    "exclusion_reason": None,
                    "rights": {"status": "redistributable", "evidence": "Synthetic ML fixture"},
                    "image": {"path": rel, "media_type": "image/png",
                              "sha256": hashlib.sha256(image_bytes).hexdigest()},
                })
                assignment.append((sid, split))
                idx += 1
    manifest = out / "manifest.jsonl"
    with manifest.open("w", encoding="utf-8") as fh:
        for row in rows:
            fh.write(json.dumps(row, ensure_ascii=False) + "\n")
    split_path = out / "split.csv"
    with split_path.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["sample_id", "split"])
        writer.writerows(sorted(assignment))
    return {"manifest": manifest, "split": split_path, "image_root": out}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--seed", type=int, default=42)
    args = parser.parse_args(argv)
    paths = write_synthetic_dataset(args.out, seed=args.seed)
    print(json.dumps({k: str(v) for k, v in paths.items()}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
