"""Generate AFN-032 aggregate statistics without modifying data or splits."""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
from collections import Counter
from pathlib import Path

VERSION = "afn-profile-v1"
NAMES = ("train", "validation", "test")
RATIOS = (0.70, 0.15, 0.15)
SOURCES = ("gossipcop", "politifact")
LABELS = ("fake", "real")
TYPES = ("full", "noimg", "notext")
STATES = ("accepted", "rejected", "pending")


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate JSON key")
        result[key] = value
    return result


def decode(raw):
    return json.loads(raw, object_pairs_hook=unique_object)


def read_inputs(manifest, groups, split_dir=None, split_csv=None, *, mode):
    paths = {"manifest": manifest, "groups": groups}
    if (split_dir is None) == (split_csv is None):
        raise ValueError("choose exactly one split input")
    if split_dir is not None:
        paths.update({name: split_dir / f"{name}.json" for name in NAMES})
    else:
        paths["split"] = split_csv
    raw = {key: path.read_bytes() for key, path in paths.items()}
    hashes = {key: hashlib.sha256(value).hexdigest() for key, value in raw.items()}
    if mode == "legacy":
        rows = decode(raw["manifest"])
    else:
        rows = [decode(line) for line in raw["manifest"].splitlines() if line.strip()]
    mapping = decode(raw["groups"])
    if split_dir is not None:
        partitions = {name: decode(raw[name]) for name in NAMES}
    else:
        reader = csv.DictReader(io.StringIO(raw["split"].decode("utf-8"), newline=""))
        if reader.fieldnames != ["sample_id", "split", "group_id"]:
            raise ValueError("expected sample_id,split,group_id CSV")
        partitions = {name: [] for name in NAMES}
        for row in reader:
            if None in row or row.get("split") not in NAMES or not row.get("sample_id"):
                raise ValueError("invalid split or redacted Test; QA full metadata required")
            partitions[row["split"]].append({"sample_id": row["sample_id"], "group_id": row["group_id"]})
    return rows, mapping, partitions, hashes


def nonempty(value):
    return isinstance(value, str) and bool(value.strip())


def metadata(rows, mode):
    """Project only needed fields; never inspect body/title/image bytes or predictions."""
    if not isinstance(rows, list) or not rows:
        raise ValueError("expected nonempty manifest")
    result = {}
    fixtures = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError("manifest row must be an object")
        sid = row.get("sample_id")
        if not nonempty(sid) or sid in result:
            raise ValueError("missing or duplicate sample_id")
        source, label = row.get("source"), row.get("label")
        if source not in SOURCES or label not in LABELS:
            raise ValueError("unknown source or label")
        if mode == "legacy":
            kind = row.get("type")
            if kind not in TYPES:
                raise ValueError("unknown legacy type")
            status = "unreviewed"
            reason = {"full": None, "noimg": "missing_image", "notext": "missing_body"}[kind]
        else:
            if row.get("schema_version") != "afn-manifest-v1" or type(row.get("is_fixture")) is not bool:
                raise ValueError("expected afn-manifest-v1 decision metadata")
            fixtures.add(row["is_fixture"])
            status = row.get("status")
            if status not in STATES:
                raise ValueError("invalid decision status")
            reason = row.get("exclusion_reason")
            if status == "rejected" and (not nonempty(reason) or not re.fullmatch(r"[a-z][a-z0-9_]{0,63}", reason)):
                raise ValueError("rejected row needs a reason code")
            if status == "accepted" and reason is not None:
                raise ValueError("accepted row has exclusion_reason")
            kind = None
        publisher = row.get("publisher")
        event = row.get("event_id") if mode == "decisions" else row.get("group_event")
        result[sid] = {"source": source, "label": label, "type": kind,
                       "status": status, "reason": reason,
                       "publisher": publisher.strip().casefold() if nonempty(publisher) else None,
                       "event_present": nonempty(event), "url_present": nonempty(row.get("source_url")),
                       "group_id": row.get("group_id") if mode == "decisions" else None}
    if len(fixtures) > 1:
        raise ValueError("mixed fixture and research decisions")
    return result, next(iter(fixtures), None)


def summarize(ids, rows, mapping, mode):
    selected = [rows[sid] for sid in ids]
    group_sizes = Counter(mapping[sid] for sid in ids if sid in mapping)
    publishers = Counter(r["publisher"] for r in selected if r["publisher"] is not None)
    counts = Counter(r["label"] for r in selected)
    combo = Counter((r["source"], r["label"]) for r in selected)
    status = Counter(r["status"] for r in selected)
    availability = Counter(r["type"] for r in selected) if mode == "legacy" else None
    reasons = Counter(r["reason"] for r in selected if r["reason"] and
                      (mode == "legacy" or r["status"] == "rejected"))
    return {"n": len(ids), "labels": {k: counts[k] for k in LABELS},
            "sources": {s: sum(combo[s, l] for l in LABELS) for s in SOURCES},
            "source_labels": {f"{s}:{l}": combo[s, l] for s in SOURCES for l in LABELS},
            "missing_labels": [l for l in LABELS if not counts[l]],
            "missing_source_labels": [f"{s}:{l}" for s in SOURCES for l in LABELS if not combo[s, l]],
            "status": {k: status[k] for k in (("unreviewed",) if mode == "legacy" else STATES)},
            "quality_by_source_label": {f"{source}:{label}": {key: sum(1 for r in selected if r["source"] == source and r["label"] == label and r["type" if mode == "legacy" else "status"] == key) for key in (TYPES if mode == "legacy" else STATES)} for source in SOURCES for label in LABELS},
            "availability": {k: availability[k] for k in TYPES} if availability is not None else None,
            "reasons": dict(sorted(reasons.items())), "groups": len(group_sizes),
            "group_hist": dict(sorted(Counter(group_sizes.values()).items())),
            "max_group": max(group_sizes.values(), default=0),
            "publisher_missing": len(selected) - sum(publishers.values()),
            "publisher_distinct": len(publishers), "publisher_max": max(publishers.values(), default=0),
            "event_missing": sum(not r["event_present"] for r in selected),
            "url_missing": sum(not r["url_present"] for r in selected)}


def profile(rows, mapping, partitions, *, mode):
    if mode not in ("legacy", "decisions"):
        raise ValueError("invalid mode")
    records, fixture = metadata(rows, mode)
    eligible = {sid for sid, row in records.items() if mode == "legacy" or row["status"] == "accepted"}
    if not isinstance(mapping, dict) or set(mapping) != eligible or not all(nonempty(gid) for gid in mapping.values()):
        raise ValueError("groups must cover exactly assigned IDs")
    if set(partitions) != set(NAMES):
        raise ValueError("expected exactly three splits")
    seen, group_split, results = set(), {}, {}
    for name in NAMES:
        if not isinstance(partitions[name], list):
            raise ValueError("split must be a list")
        ids = []
        for entry in partitions[name]:
            if not isinstance(entry, dict):
                raise ValueError("split entry must be an object")
            sid, gid = entry.get("sample_id"), entry.get("group_id")
            if not nonempty(sid) or sid not in eligible or sid in seen:
                raise ValueError("duplicate, unknown or non-accepted split ID")
            if gid != mapping[sid] or (records[sid]["group_id"] is not None and records[sid]["group_id"] != gid):
                raise ValueError("group mapping mismatch")
            if group_split.setdefault(gid, name) != name:
                raise ValueError("group crosses splits")
            seen.add(sid)
            ids.append(sid)
        results[name] = summarize(ids, records, mapping, mode)
    if seen != eligible:
        raise ValueError("split coverage mismatch")
    results["all"] = summarize(list(records), records, mapping, mode)
    results["unsplit"] = summarize(sorted(set(records) - seen), records, mapping, mode)
    # Unassigned rejected/pending rows never acquire invented split membership.
    return {"mode": mode, "fixture": fixture, "assigned": len(seen), "sets": results}


def pct(n, total):
    return f"{100 * n / total:.2f}%" if total else "—"


def cell(n, total):
    return f"{n} ({pct(n, total)})"


def render(stats, hashes, *, version, revision):
    sets = stats["sets"]
    overall = sets["all"]
    names = ("all", *NAMES, "unsplit")
    legacy = stats["mode"] == "legacy"
    lines = ["# AFN-032 · Thống kê phân bố và phân tích theo nguồn", "",
             f"- Phiên bản công cụ: `{VERSION}`; dataset: `{version}`; commit nguồn: `{revision}`.",
             f"- Chế độ: `{stats['mode']}`; fixture: `{stats['fixture']}`.",
             "- Trạng thái: **EXPLORATORY — chưa nghiệm thu dataset cuối**." if legacy else
             "- Trạng thái: thống kê quyết định đã cung cấp; không thay thế QA sign-off.",
             "- Chỉ thống kê metadata; không đọc ảnh, đánh giá dự đoán hoặc dùng nội dung Test để tuning.",
             "- Test chỉ hiển thị số liệu tổng hợp. Với gói riêng, QA quyết định phạm vi chia sẻ.", "",
             "## 1. Định danh và checksum SHA-256", "",
             "| Đầu vào | SHA-256 |", "| --- | --- |"]
    lines += [f"| `{k}` | `{v}` |" for k, v in hashes.items()]
    lines += ["", "Hash tính trên byte file đầu vào, không phải JSON đã serialize lại. Khi hash thay đổi, sinh lại báo cáo; không tái dùng thống kê cũ.",
              "", "## 2. Inventory và tình trạng mẫu", "",
              "| Phạm vi | Số mẫu | " + ("Đủ hai đầu vào (khai báo) | Thiếu ảnh | Thiếu text | Chưa xác nhận accepted/rejected |" if legacy else "Accepted | Rejected | Pending |"),
              "| --- | ---: |" + (" ---: | ---: | ---: | ---: |" if legacy else " ---: | ---: | ---: |")]
    for name in names:
        s = sets[name]; n = s["n"]
        values = [s["availability"][k] for k in TYPES] + [s["status"]["unreviewed"]] if legacy else [s["status"][k] for k in STATES]
        lines.append(f"| {name} | {n} | " + " | ".join(cell(v,n) for v in values) + " |")
    lines += ["", ("Legacy `type=full/noimg/notext` là khai báo mức đầy đủ, không phải quyết định accepted/rejected theo schema. Mẫu thiếu phương thức không đủ đầu vào Multimodal; chưa loại khỏi split bằng công cụ này." if legacy else "Accepted/rejected/pending là quyết định từ manifest; rejected/pending không có split. Công cụ không tự thay đổi quyết định."),
              "", "### Lý do thiếu/loại theo phạm vi", "", "| Phạm vi | Lý do | Số mẫu / tỷ lệ trên phạm vi |", "| --- | --- | ---: |"]
    for name in names:
        s = sets[name]
        if not s["reasons"]:
            lines.append(f"| {name} | Không có lý do ghi nhận | {cell(0,s['n'])} |")
        for reason, n in s["reasons"].items():
            lines.append(f"| {name} | `{reason}` | {cell(n,s['n'])} |")
    lines += ["", "## 3. Nguồn và nhãn", "", "Source là phân tập FakeNewsNet (`gossipcop`/`politifact`); publisher là nhà xuất bản bài gốc đã đối soát, không đồng nghĩa với source. Nhãn là nhãn nguồn, không phải kết luận độc lập của dự án.", "",
              "| Phạm vi | GossipCop | PolitiFact | Fake | Real |", "| --- | ---: | ---: | ---: | ---: |"]
    for name in names:
        s=sets[name]; n=s["n"]
        lines.append(f"| {name} | " + " | ".join(cell(v,n) for v in [*s["sources"].values(),*s["labels"].values()]) + " |")
    lines += ["", "| Phạm vi | GossipCop fake | GossipCop real | PolitiFact fake | PolitiFact real |", "| --- | ---: | ---: | ---: | ---: |"]
    for name in names:
        s=sets[name]; lines.append(f"| {name} | " + " | ".join(cell(v,s["n"]) for v in s["source_labels"].values()) + " |")
    lines += ["", "### Tình trạng mẫu theo nguồn × nhãn", "", "Tỷ lệ tính trên số mẫu của từng tổ hợp nguồn × nhãn trong từng phạm vi; không dùng mẫu số toàn tập.", "",
              "| Phạm vi | Nguồn × nhãn | Tổng | " + ("Đủ hai đầu vào | Thiếu ảnh | Thiếu text |" if legacy else "Accepted | Rejected | Pending |"),
              "| --- | --- | ---: | ---: | ---: | ---: |"]
    for name in ("all", *NAMES, "unsplit"):
        for category, values in sets[name]["quality_by_source_label"].items():
            n = sum(values.values())
            lines.append(f"| {name} | {category} | {n} | " + " | ".join(cell(v,n) for v in values.values()) + " |")
    lines += ["", "### Biểu đồ phân bố nguồn (mỗi khối xấp xỉ 5% của phạm vi)", "", "```text"]
    for name in ("all", *NAMES):
        s=sets[name]
        for source,n in s["sources"].items():
            bars="█"*round(20*n/s["n"]) if s["n"] else ""
            lines.append(f"{name:10} {source:10} {bars:20} {cell(n,s['n'])}")
    lines += ["```", "", "## 4. Split, group và lớp thiếu", "", "Tỷ lệ split dùng mẫu số là tổng mẫu được phân tập; tỷ lệ nguồn/nhãn dùng mẫu số từng hàng. Độ lệch tính theo điểm phần trăm.", "",
              "| Split | Số mẫu | Tỷ lệ thực | Mục tiêu | Độ lệch (pp) | Group | Lớp thiếu | Nguồn × nhãn thiếu |", "| --- | ---: | ---: | ---: | ---: | ---: | --- | --- |"]
    for name,target in zip(NAMES,RATIOS):
        s=sets[name]; n=s["n"]; total=stats["assigned"]
        deviation=f"{100*(n/total-target):+.2f}" if total else "—"
        lines.append(f"| {name} | {n} | {pct(n,total)} | {target*100:.0f}% | {deviation} | {s['groups']} | {', '.join(s['missing_labels']) or 'Không'} | {', '.join(s['missing_source_labels']) or 'Không'} |")
    lines += ["", "| Phạm vi | Số group | Nhóm lớn nhất (mẫu) | Histogram kích thước: số group | Nguồn chi phối |", "| --- | ---: | ---: | --- | --- |"]
    for name in ("all",*NAMES):
        s=sets[name]; max_source=max(s["sources"].values()); dominant=", ".join(k for k,v in s["sources"].items() if v==max_source) if s["n"] else "—"
        hist=", ".join(f"{size}: {count}" for size,count in s["group_hist"].items()) or "—"
        lines.append(f"| {name} | {s['groups']} | {s['max_group']} | {hist} | {dominant} ({cell(max_source,s['n'])}) |")
    lines += ["", f"Đối soát: {overall['n']} = {stats['assigned']} đã chia + {sets['unsplit']['n']} chưa chia. Không trùng ID, không thiếu ID được yêu cầu chia, không giao group đã khai báo giữa split; đây không phải chứng nhận chống leakage theo nội dung.",
              "", "## 5. Metadata nguồn và giới hạn", "", "| Phạm vi | Thiếu publisher | Publisher phân biệt (khai báo) | Publisher lớn nhất (mẫu) | Thiếu event | Thiếu URL |", "| --- | ---: | ---: | ---: | ---: | ---: |"]
    for name in names:
        s=sets[name]; n=s["n"]
        lines.append(f"| {name} | {cell(s['publisher_missing'],n)} | {s['publisher_distinct']} | {s['publisher_max']} | {cell(s['event_missing'],n)} | {cell(s['url_missing'],n)} |")
    lines += ["", "Publisher chỉ chuẩn hóa khoảng trắng và chữ hoa/thường để đếm metadata hiện có; không suy đoán từ source. Không công bố ID, URL, tên publisher riêng lẻ hoặc nội dung bài/ảnh. Không đánh giá chất lượng model từ phân bố này.",
              "", "## 6. Bàn giao và tái lập", "", "- DATA: `locnguyen230`; QA: `dangnguyen0512`. AFN-018 vẫn chờ nghiệm thu batch thật; AFN-031/029 cần xử lý chất lượng và leakage. Không dùng profile để quyết định tuning hoặc thay split.",
              "- Bản `ml-v2` là ứng viên khác sau lọc/gom nhóm/chia lại; số liệu tham chiếu ở [AFN-034](ml-train-validation.md). Không suy diễn thống kê của ứng viên từ split gốc. Gói quyết định đầy đủ do QA quản lý; chạy chế độ `decisions` khi được bàn giao.",
              "- Khi DATA/QA cập nhật manifest, nhóm hoặc split: tạo version mới, chạy lại công cụ với hash đã bàn giao; soát số đếm, ghi nhận invalidation cho ML/QA trước sử dụng.",
              "", "Chạy từ thư mục gốc repo (Python 3.10+, standard library):", "", "```sh"]
    if legacy:
        command = f"python -m scripts.profile_dataset --mode legacy --manifest data/processed/manifest.json --groups data/processed/groups.json --split-dir data/split --version {version} --revision {revision} --out reports/data-profile.md"
    else:
        command = f"python -m scripts.profile_dataset --mode decisions --qa-private --manifest /private/decisions.jsonl --groups /private/groups.json --split-csv /private/split.csv --version {version} --revision {revision} --out /private/data-profile.md"
    lines += [command, command + " --check", "```", "", "`--check` đối chiếu toàn bộ báo cáo sinh lại (bao gồm checksum); trả mã khác 0 khi dữ liệu hoặc báo cáo không còn khớp. `--expect-sha256 KEY=HASH` có thể lặp để ghim hash bàn giao độc lập. Trên Windows, kiểm tra CRLF do Git checkout; không chuẩn hóa byte trước khi tính hash. Dùng bản file nguyên byte đã bàn giao. Kiểm thử mục tiêu: `python -m pytest -q tests/data/test_profile_dataset.py`.", ""]
    return "\n".join(lines)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--mode", choices=("legacy","decisions"), required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--groups", type=Path, required=True)
    split=parser.add_mutually_exclusive_group(required=True)
    split.add_argument("--split-dir", type=Path)
    split.add_argument("--split-csv", type=Path)
    parser.add_argument("--qa-private", action="store_true", help="QA-only full decision/split metadata")
    parser.add_argument("--version", required=True)
    parser.add_argument("--revision", required=True)
    parser.add_argument("--out", type=Path, required=True)
    parser.add_argument("--expect-sha256", action="append", default=[])
    parser.add_argument("--check", action="store_true")
    args=parser.parse_args()
    try:
        if args.mode == "decisions" and not args.qa_private:
            raise ValueError("decision mode requires --qa-private and full QA metadata")
        if not all(re.fullmatch(r"[A-Za-z0-9_.-]+", value) for value in (args.version,args.revision)):
            raise ValueError("invalid version/revision")
        inputs=[args.manifest,args.groups] + ([args.split_csv] if args.split_csv else [args.split_dir/f"{n}.json" for n in NAMES])
        if args.out.resolve() in {p.resolve() for p in inputs}:
            raise ValueError("output would overwrite input")
        rows,mapping,partitions,hashes=read_inputs(args.manifest,args.groups,args.split_dir,args.split_csv,mode=args.mode)
        for spec in args.expect_sha256:
            key,sep,digest=spec.partition("=")
            if not sep or not re.fullmatch(r"[a-fA-F0-9]{64}",digest) or hashes.get(key)!=digest.lower():
                raise ValueError("input SHA-256 mismatch or invalid key")
        stats=profile(rows,mapping,partitions,mode=args.mode)
        report=render(stats,hashes,version=args.version,revision=args.revision).encode("utf-8")
        if args.check:
            if args.out.read_bytes()!=report:
                raise ValueError("stale report: regenerate from matching inputs")
        else:
            args.out.parent.mkdir(parents=True,exist_ok=True)
            args.out.write_bytes(report)
        print(f"AFN-032: {stats['sets']['all']['n']} rows, {stats['assigned']} assigned; {'verified' if args.check else 'report generated'}")
    except (OSError, ValueError, UnicodeError) as error:
        parser.exit(1,f"{error}\n")


if __name__ == "__main__":
    main()
