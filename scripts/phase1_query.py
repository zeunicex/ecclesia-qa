#!/usr/bin/env python3
"""Minimal evidence lookup against the Phase 1 SQLite corpus."""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


BOOK_ALIASES = {
    "创世记": "Gen", "诗篇": "Ps", "马太福音": "Matt", "马太": "Matt",
    "马可福音": "Mark", "马可": "Mark", "路加福音": "Luke", "路加": "Luke",
    "约翰福音": "John", "约翰": "John", "使徒行传": "Acts", "使徒": "Acts",
    "罗马书": "Rom", "哥林多前书": "1Cor", "哥林多后书": "2Cor",
    "以弗所书": "Eph", "启示录": "Rev",
}


def verse_rows(connection: sqlite3.Connection, reference: str) -> list[dict]:
    match = re.fullmatch(r"([1-3]?[A-Za-z]+)\.(\d+)\.(\d+)(?:-(\d+))?", reference)
    if not match:
        return []
    book, chapter, start, end = match.groups()
    end = end or start
    rows = connection.execute(
        """SELECT book_name,chapter,verse,text,source_id FROM bible_verses
        WHERE book_id=? AND chapter=? AND verse BETWEEN ? AND ? ORDER BY verse""",
        (book, int(chapter), int(start), int(end)),
    ).fetchall()
    return [
        {"citation": row[4], "reference": f"{row[0]} {row[1]}:{row[2]}", "text": row[3]}
        for row in rows
    ]


def direct_reference(question: str) -> str | None:
    for alias, book_id in sorted(BOOK_ALIASES.items(), key=lambda item: len(item[0]), reverse=True):
        match = re.search(rf"{re.escape(alias)}\s*(\d+)\s*[:：]\s*(\d+)(?:\s*[-～—]\s*(\d+))?", question)
        if match:
            chapter, start, end = match.groups()
            return f"{book_id}.{chapter}.{start}" + (f"-{end}" if end else "")
    match = re.search(r"\b([1-3]?[A-Za-z]+)[. ](\d+)[:.](\d+)(?:-(\d+))?\b", question)
    if match:
        book, chapter, start, end = match.groups()
        return f"{book}.{chapter}.{start}" + (f"-{end}" if end else "")
    return None


def lookup(connection: sqlite3.Connection, question: str) -> dict:
    reference = direct_reference(question)
    if reference:
        evidence = verse_rows(connection, reference)
        return {"mode": "direct_scripture", "question": question, "references": [reference], "evidence": evidence}

    topic = connection.execute(
        """SELECT topics.id,topics.references_json,topic_aliases.alias
        FROM topics JOIN topic_aliases ON topics.id=topic_aliases.topic_id
        ORDER BY length(topic_aliases.alias) DESC"""
    ).fetchall()
    for topic_id, references_json, alias in topic:
        if alias.casefold() in question.casefold():
            references = json.loads(references_json)
            evidence = [row for item in references for row in verse_rows(connection, item)]
            book_hits = connection.execute(
                """SELECT source_id,document_id,page_start,page_label,language,substr(text,1,700)
                FROM chunks WHERE source_type='reference_book' AND text LIKE ?
                ORDER BY CASE WHEN language='zh-Hans' THEN 0 ELSE 1 END,page_start LIMIT 5""",
                (f"%{alias}%",),
            ).fetchall()
            sources = [
                {"citation": row[0], "document_id": row[1], "pdf_page": row[2], "printed_page": row[3],
                 "language": row[4], "text": row[5]}
                for row in book_hits
            ]
            return {
                "mode": "reviewed_topic", "topic_id": topic_id, "matched_alias": alias,
                "question": question, "references": references, "evidence": evidence,
                "reference_book_hits": sources,
            }

    literal = re.sub(r"[？?，,。.!！什么哪里何时请问告诉我]", "", question).strip()
    if len(literal) >= 2:
        rows = connection.execute(
            """SELECT source_id,document_id,page_start,page_label,language,substr(text,1,900)
            FROM chunks WHERE text LIKE ? ORDER BY page_start LIMIT 8""",
            (f"%{literal}%",),
        ).fetchall()
    else:
        rows = []
    evidence = [
        {"citation": row[0], "document_id": row[1], "pdf_page": row[2], "printed_page": row[3],
         "language": row[4], "text": row[5]}
        for row in rows
    ]
    return {
        "mode": "literal_search" if evidence else "insufficient_evidence",
        "question": question,
        "answer_policy": "Only answer from the returned evidence; abstain when evidence is empty.",
        "evidence": evidence,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("question")
    parser.add_argument(
        "--db", type=Path,
        default=Path(__file__).resolve().parents[1] / "output" / "phase1" / "ecclesia_phase1.sqlite3",
    )
    args = parser.parse_args()
    connection = sqlite3.connect(f"file:{args.db.resolve()}?mode=ro", uri=True)
    result = lookup(connection, args.question)
    connection.close()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
