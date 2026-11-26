"""Reconcile ml-v2 QA IDs with pinned FakeNewsNet source metadata."""

import argparse
import csv
import json
import re
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.parse import urlsplit

import ml  # Makes the shared Backend package importable from the repository root.
from ml.common import read_split_file, sha256_file
from scripts.group_samples import RULES, article_key, normalize, similarities


SOURCE_REVISION = "654361e1c8d5baa751baf1dac5032df621652280"
SOURCE_HASHES = {
    "gossipcop_fake.csv": "c6932bffadb1230bc61c66bb2ca298f4ef28ce849d268313ad2eed41d18d4c99",
    "gossipcop_real.csv": "d721e9a8b7e660da05c089691743c33fecb25367074e936b5fab3d85cdcbe79f",
    "politifact_fake.csv": "abe7fe7aad801b1e2ab5fc963cbd0881d9670190262ae3df85e91c3380bd004c",
    "politifact_real.csv": "2500f86a7addca0f59fe8cf089c0f802d3eca6980f53538992b3b0e9687dbae0",
}


def source_article(url: str) -> str:
    """Return the source URL, unwrapping a Wayback URL when it embeds a target."""
    url = url.strip()
    if not url:
        return ""
    url = url if "://" in url else "https://" + url
    try:
        parsed = urlsplit(url)
        if parsed.hostname == "web.archive.org":
            match = re.fullmatch(r"/web/\d+[a-z_]*?/(https?://.+)", parsed.path, re.IGNORECASE)
            if not match:
                return ""
            url = match[1] + ("?" + parsed.query if parsed.query else "")
            parsed = urlsplit(url)
        if parsed.scheme in {"http", "https"} and parsed.hostname and not parsed.username:
            return url
    except ValueError:
        pass
    return ""


def write_csv(path: Path, columns, rows) -> None:
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\n")
        writer.writerow(columns)
        writer.writerows(rows)


def build(source_dir: Path, qa_split: Path, out: Path) -> dict:
    if out.exists():
        raise FileExistsError("choose a new private output directory")
    assignments, _ = read_split_file(qa_split, include_test=True)
    ids = sorted(assignments)
    matched = {}
    # Some upstream tweet-ID cells exceed the CSV parser's default limit.
    csv.field_size_limit(16 * 1024 * 1024)
    for name, checksum in SOURCE_HASHES.items():
        path = source_dir / name
        if sha256_file(path) != checksum:
            raise ValueError(f"unexpected FakeNewsNet checksum for {name}")
        with path.open(encoding="utf-8-sig", newline="") as stream:
            for row in csv.DictReader(stream):
                sid = row["id"].strip()
                if sid not in assignments:
                    continue
                if sid in matched:
                    raise ValueError("ambiguous upstream sample ID; resolve before filling metadata")
                matched[sid] = name, row["news_url"].strip(), normalize(row["title"])

    rows, evidence, titles, url_keys = [], [], [], {}
    by_host = defaultdict(set)
    for sid in ids:
        name, original, title = matched.get(sid, ("", "", ""))
        url = source_article(original)
        host = (urlsplit(url).hostname or "").removeprefix("www.") if url else ""
        if host:
            key = article_key(url)
            url_keys[sid] = key
            by_host[host].add(assignments[sid])
        rows.append((sid, host, ""))
        evidence.append((sid, name, original, host))
        titles.append(title)
    scores = similarities(titles)
    candidates = []
    for i, j in combinations(range(len(ids)), 2):
        left, right = ids[i], ids[j]
        same_url = left in url_keys and url_keys[left] == url_keys.get(right)
        score = float(scores[i, j])
        if same_url or score >= RULES["title_candidate"]:
            candidates.append((left, right, "same_article_url" if same_url else "source_title_similarity",
                               round(score, 6), assignments[left][0] != assignments[right][0]))

    report = {
        "status": "DRAFT_REQUIRES_DATA_REVIEW",
        "source_revision": SOURCE_REVISION,
        "source_sha256": SOURCE_HASHES,
        "qa_split_sha256": sha256_file(qa_split),
        "samples": len(ids),
        "source_ids_matched": len(matched),
        "publisher_hosts_filled": sum(bool(host) for _, host, _ in rows),
        "event_ids_from_source": 0,
        "publisher_keys_crossing_groups": sum(len(groups) > 1 for groups in by_host.values()),
        "publisher_keys_crossing_splits": sum(len({split for split, _ in groups}) > 1 for groups in by_host.values()),
        "event_candidate_pairs": dict(Counter(row[2] for row in candidates)),
        "cross_split_candidate_pairs": dict(Counter(row[2] for row in candidates if row[-1])),
    }
    out.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(dir=out.parent) as temp:
        stage = Path(temp) / "provenance"
        stage.mkdir()
        write_csv(stage / "provenance-draft.csv", ("sample_id", "publisher", "event_id"), rows)
        write_csv(stage / "source-evidence.csv", ("sample_id", "source_csv", "source_url", "publisher_host"), evidence)
        write_csv(stage / "event-candidates.csv", ("left_id", "right_id", "reason", "title_similarity", "cross_split"),
                  candidates)
        report["output_sha256"] = {path.name: sha256_file(path) for path in sorted(stage.iterdir())}
        (stage / "summary.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8", newline="\n")
        stage.rename(out)
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", type=Path, required=True)
    parser.add_argument("--qa-split", type=Path, required=True)
    parser.add_argument("--out", type=Path, required=True)
    args = parser.parse_args()
    try:
        report = build(args.source_dir, args.qa_split, args.out)
    except (OSError, ValueError, KeyError, csv.Error) as error:
        parser.exit(1, f"{error}\n")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
