#!/usr/bin/env python3
"""Extract English Recovery Version footnotes from the supplied EPUB."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
import zipfile
from pathlib import Path
from xml.etree import ElementTree as ET

from parse_rcv_bilingual_chm import BOOKS, sql_value


CORPUS_VERSION = "phase4-c-2026-08-13"
DOCUMENT_ID = "bible-rcv-en-footnotes-epub"
NOTE_ID = re.compile(r"n(\d+)_(\d+)_(\d+)")
SINGLE_CHAPTER_NOTE_ID = re.compile(r"n(\d+)_(\d+)")
SUPERSCRIPTION_NOTE_ID = re.compile(r"n(\d+)_0_st(\d+)")
NOTE_PAGE_START = 1257


def clean_text(value: str) -> str:
    value = unicodedata.normalize("NFKC", value).replace("\u00a0", " ")
    return re.sub(r"\s+", " ", value).strip()


def local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def parse_note_page(source: bytes, expected_chapter: int, single_chapter: bool) -> list[dict]:
    root = ET.fromstring(source)
    rows = []
    for element in root.iter():
        identity = element.attrib.get("id", "")
        match = NOTE_ID.fullmatch(identity)
        superscription = SUPERSCRIPTION_NOTE_ID.fullmatch(identity)
        single = SINGLE_CHAPTER_NOTE_ID.fullmatch(identity) if single_chapter else None
        if match:
            chapter, verse, note_no = map(int, match.groups())
        elif superscription:
            chapter, note_no = map(int, superscription.groups())
            verse = 0
        elif single:
            verse, note_no = map(int, single.groups())
            chapter = 1
        else:
            continue
        if chapter != expected_chapter:
            raise ValueError(f"Expected chapter {expected_chapter}, found note for chapter {chapter}")
        paragraphs = [child for child in element.iter() if local_name(child) == "p"]
        heading = next((clean_text("".join(child.itertext())) for child in paragraphs
                        if child.attrib.get("class") == "note-head"), "")
        bodies = [clean_text("".join(child.itertext())) for child in paragraphs
                  if child.attrib.get("class") == "note"]
        bodies = [body for body in bodies if body]
        if not heading or not bodies:
            raise ValueError(f"Incomplete footnote {chapter}:{verse} note {note_no}")
        rows.append({
            "chapter": chapter,
            "verse": verse,
            "note_no": note_no,
            "heading_text": heading,
            "text": "\n\n".join(bodies),
        })
    return rows


def parse_epub(path: Path) -> list[dict]:
    rows = []
    page = NOTE_PAGE_START
    with zipfile.ZipFile(path) as archive:
        for book_id, _book_zh, book_name, chapters in BOOKS:
            for chapter in range(1, chapters + 1):
                name = f"text/part{page:04d}.html"
                for note in parse_note_page(archive.read(name), chapter, chapters == 1):
                    note.update({
                        "translation": "RCV-EN",
                        "language": "en",
                        "book_id": book_id,
                        "book_name": book_name,
                        "source_id": f"footnote:rcv-en:{book_id}.{chapter}.{note['verse']}.{note['note_no']}",
                    })
                    rows.append(note)
                page += 1
    if page != 2446:
        raise ValueError(f"Unexpected final note page: {page - 1}")
    keys = {(row["book_id"], row["chapter"], row["verse"], row["note_no"]) for row in rows}
    if len(keys) != len(rows):
        raise ValueError("Duplicate English footnote identity")
    return rows


def chunks_for(rows: list[dict]) -> list[dict]:
    chunks = []
    for row in rows:
        reference = f'{row["book_name"]} {row["chapter"]}:{row["verse"]}, footnote {row["note_no"]}'
        text = f'{row["heading_text"]}\n{row["text"]}'
        chunks.append({
            "id": row["source_id"],
            "metadata": {
                "document_id": DOCUMENT_ID,
                "language": "en",
                "source_type": "footnote",
                "corpus_version": CORPUS_VERSION,
                "checksum": hashlib.sha256(text.encode()).hexdigest(),
                "book_id": row["book_id"],
                "chapter": row["chapter"],
                "verse_start": row["verse"],
                "verse_end": row["verse"],
                "note_no": row["note_no"],
                "heading_path": reference,
            },
            "text": text,
        })
    return chunks


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def write_d1_sql(path: Path, document: dict, rows: list[dict], chunks: list[dict]) -> None:
    document_values = [document[key] for key in
                       ("id", "title", "title_en", "language", "source_type", "checksum", "corpus_version", "rights_policy")]
    lines = [
        "INSERT OR REPLACE INTO documents (id,title,title_en,language,source_type,checksum,corpus_version,rights_policy) VALUES ("
        + ",".join(sql_value(value) for value in document_values) + ");",
        "DELETE FROM footnotes WHERE translation='RCV-EN' AND language='en';",
        "DELETE FROM search_chunks WHERE language='en' AND source_type='footnote';",
    ]
    for row in rows:
        values = [row[key] for key in ("book_id", "chapter", "verse", "note_no", "translation", "language",
                                       "book_name", "heading_text", "text", "source_id")]
        lines.append("INSERT OR REPLACE INTO footnotes "
                     "(book_id,chapter,verse,note_no,translation,language,book_name,heading_text,text,source_id) VALUES ("
                     + ",".join(sql_value(value) for value in values) + ");")
    for chunk in chunks:
        metadata = chunk["metadata"]
        values = [chunk["id"], "footnote", "Recovery Version Bible", metadata["heading_path"], None, None, "en", chunk["text"]]
        lines.append("INSERT INTO search_chunks "
                     "(source_id,source_type,title,reference,pdf_page,pdf_page_end,language,text) VALUES ("
                     + ",".join(sql_value(value) for value in values) + ");")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--epub", type=Path, required=True)
    parser.add_argument("--out", type=Path, default=Path("output/rcv-english-footnotes"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    source_checksum = hashlib.sha256(args.epub.read_bytes()).hexdigest()
    rows = parse_epub(args.epub)
    chunks = chunks_for(rows)
    document = {
        "id": DOCUMENT_ID,
        "title": "Recovery Version Bible — English Footnotes",
        "title_en": "Recovery Version Bible — English Footnotes",
        "language": "en",
        "source_type": "bible_epub",
        "source_path": str(args.epub),
        "checksum": source_checksum,
        "corpus_version": CORPUS_VERSION,
        "rights_policy": "private-use",
    }

    assert len(rows) == 14_883
    assert next(row for row in rows if row["source_id"] == "footnote:rcv-en:Gen.1.1.1")["text"].startswith("The Bible, composed of two testaments")
    assert next(row for row in rows if row["source_id"] == "footnote:rcv-en:Eph.4.20.1")["text"]

    write_jsonl(args.out / "documents.jsonl", [document])
    write_jsonl(args.out / "footnotes.jsonl", rows)
    write_jsonl(args.out / "chunks.jsonl", chunks)
    write_d1_sql(args.out / "d1-english-footnotes.sql", document, rows, chunks)
    by_book = {book_id: sum(row["book_id"] == book_id for row in rows) for book_id, *_ in BOOKS}
    summary = {
        "source": str(args.epub),
        "source_sha256": source_checksum,
        "books": len(BOOKS),
        "chapters": sum(book[3] for book in BOOKS),
        "footnotes": len(rows),
        "search_chunks": len(chunks),
        "empty_text": sum(not row["text"] for row in rows),
        "by_book": by_book,
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
