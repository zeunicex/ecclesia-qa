#!/usr/bin/env python3
"""Build the reviewed Batch A reference-book import package."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

from phase1_build import pdf_page_count, sha256
from phase3_build import ordinary_book_rows, title_parts, write_jsonl
from priority_manifest import BATCH_A, title


CORPUS_VERSION = "phase4-a-2026-08-12"
CURRENT_RECORDS_AFTER_FOOTNOTES = 103_611


def batch_a_paths(root: Path) -> list[Path]:
    by_code = {}
    for path in root.glob("*xx-en&chs*/*.pdf"):
        if not path.name.startswith("._"):
            by_code[title(path)[0]] = path
    missing = [code for code in BATCH_A if code not in by_code]
    if missing:
        raise FileNotFoundError(f"Missing Batch A books: {missing}")
    return [by_code[code] for code in BATCH_A]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=root / "output/phase4-batch-a")
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    documents = []
    chunks = []
    languages = Counter()
    per_document = Counter()
    for path in batch_a_paths(root):
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
            "corpus_version": CORPUS_VERSION,
        }
        rows = list(ordinary_book_rows(root, document))
        if not rows:
            raise ValueError(f"No searchable text extracted from {source_path}")
        documents.append(document)
        chunks.extend(rows)
        per_document[doc_id] = len(rows)
        languages.update(row["metadata"]["language"] for row in rows)

    ids = [row["id"] for row in chunks]
    if len(documents) != 50 or len(ids) != len(set(ids)):
        raise ValueError("Batch A document count or chunk ID uniqueness check failed")
    if set(languages) - {"zh-Hans", "en", "zh-Hans+en"}:
        raise ValueError(f"Unexpected languages: {languages}")

    write_jsonl(args.out / "documents.jsonl", documents)
    write_jsonl(args.out / "chunks.jsonl", chunks)
    projected_records = CURRENT_RECORDS_AFTER_FOOTNOTES + len(chunks)
    projected_gib = projected_records * 10_240 / 2**30
    if projected_gib >= 1.6:
        raise ValueError(f"Batch A exceeds the 1.6 GiB safety ceiling: {projected_gib:.3f} GiB")
    summary = {
        "corpus_version": CORPUS_VERSION,
        "documents": len(documents),
        "chunks": len(chunks),
        "languages": dict(languages),
        "document_chunks": dict(per_document),
        "projected_total_records": projected_records,
        "conservative_storage_gib": round(projected_gib, 3),
        "qa": "PASS",
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
