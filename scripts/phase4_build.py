#!/usr/bin/env python3
"""Build the next reviewed reference-book import package."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from phase1_build import pdf_page_count, sha256
from phase3_build import ordinary_book_rows, title_parts, write_jsonl
from priority_manifest import BATCH_A, BATCH_B, priority_rows, title


BATCHES = {"A": BATCH_A, "B": BATCH_B}
CURRENT_RECORDS = {"A": 103_611, "B": 147_206, "remaining": 165_007}
CORPUS_VERSIONS = {
    "A": "phase4-a-2026-08-12",
    "B": "phase4-b-2026-08-19",
    "remaining": "phase4-cde-prefix-2026-08-20",
}


def batch_paths(root: Path, batch: str) -> list[Path]:
    if batch == "remaining":
        rows = priority_rows(root)
        return [root / row["source_path"] for group in "CDE" for row in rows if row["batch"] == group]
    by_code = {}
    for path in root.glob("*xx-en&chs*/*.pdf"):
        if not path.name.startswith("._"):
            by_code[title(path)[0]] = path
    codes = BATCHES[batch]
    missing = [code for code in codes if code not in by_code]
    if missing:
        raise FileNotFoundError(f"Missing Batch {batch} books: {missing}")
    return [by_code[code] for code in codes]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--batch", choices=(*BATCHES, "remaining"), default="A")
    parser.add_argument("--current-records", type=int)
    parser.add_argument("--ceiling-gib", type=float)
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    args.out = args.out or root / f"output/phase4-batch-{args.batch.lower()}"
    args.out.mkdir(parents=True, exist_ok=True)
    corpus_version = CORPUS_VERSIONS[args.batch]
    current_records = args.current_records if args.current_records is not None else CURRENT_RECORDS[args.batch]
    ceiling_gib = args.ceiling_gib if args.ceiling_gib is not None else (1.8 if args.batch == "remaining" else 1.6)

    documents = []
    chunks = []
    languages = Counter()
    per_document = Counter()
    deferred = []
    first_deferred = None
    paths = batch_paths(root, args.batch)
    for index, path in enumerate(paths):
        source_path = str(path.relative_to(root))
        doc_id, title_zh, title_en = title_parts(source_path)
        document = {
            "id": doc_id,
            "title": title_zh,
            "title_en": title_en,
            "language": "zh-Hans+en",
            "source_type": "bilingual_pdf",
            "source_path": source_path,
            "checksum": sha256(path),
            "page_count": pdf_page_count(path),
            "rights_policy": "private_acceptance_only",
            "corpus_version": corpus_version,
        }
        rows = list(ordinary_book_rows(root, document))
        if not rows:
            raise ValueError(f"No searchable text extracted from {source_path}")
        projected_records = current_records + len(chunks) + len(rows)
        if projected_records * 10_240 / 2**30 >= ceiling_gib:
            deferred = [title_parts(str(item.relative_to(root)))[0] for item in paths[index:]]
            first_deferred = {
                "id": doc_id,
                "chunks": len(rows),
                "projected_total_records": projected_records,
                "projected_gib": round(projected_records * 10_240 / 2**30, 6),
            }
            break
        documents.append(document)
        chunks.extend(rows)
        per_document[doc_id] = len(rows)
        languages.update(row["metadata"]["language"] for row in rows)

    ids = [row["id"] for row in chunks]
    if not documents or len(ids) != len(set(ids)):
        raise ValueError(f"Batch {args.batch} document count or chunk ID uniqueness check failed")
    if set(languages) - {"zh-Hans", "en", "zh-Hans+en"}:
        raise ValueError(f"Unexpected languages: {languages}")

    write_jsonl(args.out / "documents.jsonl", documents)
    write_jsonl(args.out / "chunks.jsonl", chunks)
    projected_records = current_records + len(chunks)
    projected_gib = projected_records * 10_240 / 2**30
    summary = {
        "batch": args.batch,
        "corpus_version": corpus_version,
        "documents": len(documents),
        "chunks": len(chunks),
        "deferred_documents": deferred,
        "first_deferred": first_deferred,
        "languages": dict(languages),
        "document_chunks": dict(per_document),
        "projected_total_records": projected_records,
        "conservative_storage_gib": round(projected_gib, 3),
        "ceiling_gib": ceiling_gib,
        "qa": "PASS",
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
