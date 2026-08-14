#!/usr/bin/env python3
"""Estimate a deduplicated reference-book corpus without writing chunk text."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

from phase1_build import clean_pdf_page, extract_pdf_pages, make_page_chunks


ROOT_BOOKS = {
    "2020-DST-en&chs-hwmr.pdf",
    "2021-MDC-en&chs-hwmr.pdf",
    "2021-MDC-hwmr-chs.pdf",
    "LetterGraduatingSeniors.pdf",
    "shenjinglundefuyin.pdf",
    "恢复本新约圣经52题.pdf",
    "道路.pdf",
}


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as source:
        for block in iter(lambda: source.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def candidates(root: Path) -> list[Path]:
    numbered = [path for path in root.glob("*xx-en&chs*/*.pdf") if not path.name.startswith("._")]
    return sorted(numbered + [root / name for name in ROOT_BOOKS if (root / name).exists()])


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    existing = set()
    for jsonl in (root / "output/phase1/documents.jsonl", root / "output/phase3/documents.jsonl"):
        for line in jsonl.read_text(encoding="utf-8").splitlines():
            existing.add(json.loads(line)["source_path"])

    unique = {}
    duplicates = []
    for path in candidates(root):
        checksum = digest(path)
        if checksum in unique:
            duplicates.append((str(path.relative_to(root)), unique[checksum]))
        else:
            unique[checksum] = str(path.relative_to(root))

    rows = []
    for index, source_path in enumerate(unique.values(), start=1):
        if source_path in existing:
            continue
        path = root / source_path
        chunks = text_bytes = 0
        for raw in extract_pdf_pages(path):
            for _language, text in make_page_chunks(clean_pdf_page(raw), limit=1400):
                chunks += 1
                text_bytes += len(text.encode())
        rows.append({"source_path": source_path, "chunks": chunks, "text_bytes": text_bytes, "pdf_bytes": path.stat().st_size})
        if index % 25 == 0:
            print(f"scanned={index}/{len(unique)}", flush=True)

    rows.sort(key=lambda row: row["chunks"], reverse=True)
    current_records = 101_354
    additional = sum(row["chunks"] for row in rows)
    total = current_records + additional
    report = {
        "candidate_files": len(candidates(root)),
        "unique_files": len(unique),
        "already_imported_files": len(set(unique.values()) & existing),
        "remaining_files": len(rows),
        "duplicate_files": duplicates,
        "additional_chunks": additional,
        "projected_total_records": total,
        "projected_gib_at_6k_per_record": round(total * 6144 / 2**30, 3),
        "projected_gib_at_8k_per_record": round(total * 8192 / 2**30, 3),
        "projected_gib_at_10k_per_record": round(total * 10240 / 2**30, 3),
        "largest_remaining_books": rows[:30],
    }
    out = root / "output/phase3/full-library-capacity.json"
    out.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
