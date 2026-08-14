#!/usr/bin/env python3
"""Build the Phase 1 structured Bible and representative-book corpus.

Uses only Python's standard library plus Poppler's pdfinfo/pdftotext commands.
The output is a portable SQLite database and embedding-ready JSONL files.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
import zipfile
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable
from xml.etree import ElementTree as ET


CORPUS_VERSION = "phase1-2026-08-11"
TRANSLATION = "RCV-ZH-CN"
XML_NS = "{http://www.w3.org/1999/xhtml}"

BOOKS = [
    ("Gen", "创世记"), ("Exod", "出埃及记"), ("Lev", "利未记"),
    ("Num", "民数记"), ("Deut", "申命记"), ("Josh", "约书亚记"),
    ("Judg", "士师记"), ("Ruth", "路得记"), ("1Sam", "撒母耳记上"),
    ("2Sam", "撒母耳记下"), ("1Kgs", "列王纪上"), ("2Kgs", "列王纪下"),
    ("1Chr", "历代志上"), ("2Chr", "历代志下"), ("Ezra", "以斯拉记"),
    ("Neh", "尼希米记"), ("Esth", "以斯帖记"), ("Job", "约伯记"),
    ("Ps", "诗篇"), ("Prov", "箴言"), ("Eccl", "传道书"),
    ("Song", "雅歌"), ("Isa", "以赛亚书"), ("Jer", "耶利米书"),
    ("Lam", "耶利米哀歌"), ("Ezek", "以西结书"), ("Dan", "但以理书"),
    ("Hos", "何西阿书"), ("Joel", "约珥书"), ("Amos", "阿摩司书"),
    ("Obad", "俄巴底亚书"), ("Jonah", "约拿书"), ("Mic", "弥迦书"),
    ("Nah", "那鸿书"), ("Hab", "哈巴谷书"), ("Zeph", "西番雅书"),
    ("Hag", "哈该书"), ("Zech", "撒迦利亚书"), ("Mal", "玛拉基书"),
    ("Matt", "马太福音"), ("Mark", "马可福音"), ("Luke", "路加福音"),
    ("John", "约翰福音"), ("Acts", "使徒行传"), ("Rom", "罗马书"),
    ("1Cor", "哥林多前书"), ("2Cor", "哥林多后书"), ("Gal", "加拉太书"),
    ("Eph", "以弗所书"), ("Phil", "腓立比书"), ("Col", "歌罗西书"),
    ("1Thess", "帖撒罗尼迦前书"), ("2Thess", "帖撒罗尼迦后书"),
    ("1Tim", "提摩太前书"), ("2Tim", "提摩太后书"), ("Titus", "提多书"),
    ("Phlm", "腓利门书"), ("Heb", "希伯来书"), ("Jas", "雅各书"),
    ("1Pet", "彼得前书"), ("2Pet", "彼得后书"), ("1John", "约翰一书"),
    ("2John", "约翰二书"), ("3John", "约翰三书"), ("Jude", "犹大书"),
    ("Rev", "启示录"),
]
BOOK_NAMES = dict(BOOKS)

PDF_SOURCES = [
    {
        "id": "book-2046-triune-god-father-son-spirit",
        "path": "20xx-en&chs3/(2046)关于父子灵三而一的神-Concerning the Triune God－the Father, the Son, and the Spirit (chs).pdf",
        "title": "关于父子灵三而一的神",
        "title_en": "Concerning the Triune God—The Father, the Son, and the Spirit",
    },
    {
        "id": "book-2066-revelation-triune-god",
        "path": "20xx-en&chs4/(2066)依照圣经纯正话语的三一神启示-The Revelation of the Triune God according to the Pure Words of the Bible (chs).pdf",
        "title": "依照圣经纯正话语的三一神启示",
        "title_en": "The Revelation of the Triune God according to the Pure Words of the Bible",
    },
    {
        "id": "book-2157-truth-lessons",
        "path": "21xx-en&chs2/(2157)真理课程-Truth Lessons (chs).pdf",
        "title": "真理课程",
        "title_en": "Truth Lessons",
    },
    {
        "id": "book-2161-gods-new-testament-economy",
        "path": "21xx-en&chs2/(2161)神新约的经纶-God's New Testament Economy (chs).pdf",
        "title": "神新约的经纶",
        "title_en": "God's New Testament Economy",
    },
    {
        "id": "book-2187-living-divine-trinity",
        "path": "21xx-en&chs4/(2187)在神圣三一里并同神圣三一活着-Living In and With the Divine Trinity (chs).pdf",
        "title": "在神圣三一里并同神圣三一活着",
        "title_en": "Living In and With the Divine Trinity",
    },
    {
        "id": "book-2214-prayers-brother-nee",
        "path": "22xx-en&chs1/(2214)倪柝声弟兄的祷告-The Prayers of Brother Nee (chs).pdf",
        "title": "倪柝声弟兄的祷告",
        "title_en": "The Prayers of Brother Nee",
    },
    {
        "id": "book-2314-church-body-christ",
        "path": "23xx-en&chs1/(2314)召会是基督的身体-The Church as the Body of Christ (chs).pdf",
        "title": "召会是基督的身体",
        "title_en": "The Church as the Body of Christ",
    },
    {
        "id": "book-2341-practical-way-mingling",
        "path": "23xx-en&chs2/(2341)活在神人调和中实际的路-The Practical Way to Live in the Mingling of God with Man (chs).pdf",
        "title": "活在神人调和中实际的路",
        "title_en": "The Practical Way to Live in the Mingling of God with Man",
    },
    {
        "id": "book-2387-divine-trinity-holy-word",
        "path": "23xx-en&chs4/(2387)圣言中所启示的神圣三一-The Divine Trinity as Revealed in the Holy Word (chs).pdf",
        "title": "圣言中所启示的神圣三一",
        "title_en": "The Divine Trinity as Revealed in the Holy Word",
    },
]

TOPICS = [
    {
        "id": "calling-disciples",
        "aliases": {
            "zh-Hans": ["主耶稣呼召门徒", "耶稣呼召门徒", "呼召门徒"],
            "zh-Hant": ["主耶穌呼召門徒", "耶穌呼召門徒", "呼召門徒"],
            "en": ["Jesus calls the disciples", "calling of the disciples"],
        },
        "references": ["Matt.4.18-22", "Mark.1.16-20", "Luke.5.1-11", "John.1.35-51"],
    },
    {
        "id": "great-commission",
        "aliases": {
            "zh-Hans": ["大使命", "使万民作主的门徒"],
            "zh-Hant": ["大使命", "使萬民作主的門徒"],
            "en": ["Great Commission", "disciple all the nations"],
        },
        "references": ["Matt.28.18-20", "Mark.16.15-16", "Luke.24.46-49", "Acts.1.8"],
    },
    {
        "id": "divine-trinity",
        "aliases": {
            "zh-Hans": ["神圣三一", "三一神", "父子灵"],
            "zh-Hant": ["神聖三一", "三一神", "父子靈"],
            "en": ["Divine Trinity", "Triune God", "Father Son Spirit"],
        },
        "references": ["Matt.3.16-17", "Matt.28.19", "John.14.16-17", "2Cor.13.14"],
    },
]


@dataclass(frozen=True)
class Verse:
    book_id: str
    chapter: int
    verse: int
    text: str


@dataclass(frozen=True)
class Footnote:
    book_id: str
    chapter: int
    verse: int
    note_no: int
    heading_text: str
    text: str


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def normalized(text: str) -> str:
    text = text.replace("\u00a0", " ").replace("\u3000", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def tag_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def parse_verse_paragraph(p: ET.Element) -> list[tuple[int, str]]:
    """Split a verse paragraph on direct-child numeric superscripts.

    Footnote superscripts live inside the footnote anchor/list, so direct children
    are the reliable verse boundaries even when the paragraph id is duplicated.
    """
    found: list[tuple[int, str]] = []
    number: int | None = None
    pieces: list[str] = []

    def flush() -> None:
        nonlocal pieces
        if number is not None:
            value = normalized("".join(pieces))
            if value:
                found.append((number, value))
        pieces = []

    if p.text:
        pieces.append(p.text)
    for child in p:
        name = tag_name(child)
        marker = normalized("".join(child.itertext()))
        if name == "sup" and marker.isdigit():
            flush()
            number = int(marker)
        elif not (name == "a" and child.attrib.get("class") == "duokan-footnote"):
            pieces.append("".join(child.itertext()))
        if child.tail:
            pieces.append(child.tail)
    flush()
    return found


def footnote_body(p: ET.Element) -> tuple[str, str]:
    heading = ""
    pieces: list[str] = []
    for child in p:
        name = tag_name(child)
        if name == "b":
            heading = normalized("".join(child.itertext()))
        elif name == "br":
            pieces.append("\n")
        else:
            pieces.append("".join(child.itertext()))
        if child.tail:
            pieces.append(child.tail)
    return heading, normalized("".join(pieces))


def parse_bible(epub: Path) -> tuple[list[Verse], list[Footnote]]:
    verses: list[Verse] = []
    notes: list[Footnote] = []
    with zipfile.ZipFile(epub) as archive:
        for index, (book_id, _book_name) in enumerate(BOOKS, start=1):
            member = f"OEBPS/Text/{index:02d}.xhtml"
            root = ET.fromstring(archive.read(member))
            body = root.find(f"{XML_NS}body")
            if body is None:
                raise ValueError(f"Missing body in {member}")
            chapter = 1
            for child in body:
                child_id = child.attrib.get("id", "")
                chapter_match = re.fullmatch(rf"C(\d+){re.escape(book_id)}", child_id)
                if chapter_match:
                    chapter = int(chapter_match.group(1))
                if tag_name(child) == "p" and child_id.startswith("V"):
                    for verse_no, text in parse_verse_paragraph(child):
                        verses.append(Verse(book_id, chapter, verse_no, text))

            note_pattern = re.compile(rf"N(\d+){re.escape(book_id)}(\d+)$")
            for item in root.iter(f"{XML_NS}li"):
                if item.attrib.get("class") != "duokan-footnote-item":
                    continue
                match = note_pattern.fullmatch(item.attrib.get("id", ""))
                if not match:
                    raise ValueError(f"Unparseable footnote id {item.attrib.get('id')} in {member}")
                verse_no, chapter_no = map(int, match.groups())
                p = item.find(f"{XML_NS}p")
                if p is None:
                    continue
                heading, body_text = footnote_body(p)
                markers = list(re.finditer(r"(?m)^\s*(\d+)\.\s*", body_text))
                for marker_index, marker in enumerate(markers):
                    end = markers[marker_index + 1].start() if marker_index + 1 < len(markers) else len(body_text)
                    note_text = normalized(body_text[marker.end():end])
                    notes.append(Footnote(book_id, chapter_no, verse_no, int(marker.group(1)), heading, note_text))
    return verses, notes


def pdf_page_count(path: Path) -> int:
    completed = subprocess.run(
        ["pdfinfo", str(path)], check=True, capture_output=True, text=True, encoding="utf-8", errors="replace"
    )
    match = re.search(r"^Pages:\s+(\d+)$", completed.stdout, re.MULTILINE)
    if not match:
        raise ValueError(f"Could not read page count for {path}")
    return int(match.group(1))


def extract_pdf_pages(path: Path) -> list[str]:
    completed = subprocess.run(
        ["pdftotext", "-enc", "UTF-8", str(path), "-"], check=True, capture_output=True
    )
    return completed.stdout.decode("utf-8", errors="replace").split("\f")[:-1]


def page_label(text: str) -> str | None:
    matches = re.findall(r"(?:第\s*(\d+)\s*页|Page\s+(\d+))", text, flags=re.IGNORECASE)
    if not matches:
        return None
    chinese, english = matches[-1]
    return chinese or english


def clean_pdf_page(text: str) -> str:
    kept: list[str] = []
    for line in text.replace("\r", "").splitlines():
        stripped = line.strip()
        if re.search(r"\s-\s第\s*\d+\s*页\s*$", stripped):
            continue
        if re.search(r"\s-\sPage\s+\d+\s*$", stripped, flags=re.IGNORECASE):
            continue
        kept.append(stripped)
    return normalized("\n".join(kept))


def paragraph_language(text: str) -> str:
    han = len(re.findall(r"[\u3400-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    if han >= 4 and han >= latin * 0.12:
        return "zh-Hans"
    if latin >= 4:
        return "en"
    return "unknown"


def page_paragraphs(text: str) -> list[tuple[str, str]]:
    paragraphs = [normalized(item) for item in re.split(r"\n\s*\n", text) if normalized(item)]
    tagged: list[tuple[str, str]] = []
    pending: list[str] = []
    for paragraph in paragraphs:
        language = paragraph_language(paragraph)
        if language == "unknown":
            pending.append(paragraph)
            continue
        if pending:
            paragraph = normalized("\n".join(pending + [paragraph]))
            pending = []
        tagged.append((language, paragraph))
    if pending and tagged:
        language, paragraph = tagged[-1]
        tagged[-1] = (language, normalized(paragraph + "\n" + "\n".join(pending)))
    elif pending:
        tagged.append(("zh-Hans+en", normalized("\n".join(pending))))
    return tagged


def split_long_text(text: str, limit: int = 1800, overlap: int = 120) -> Iterable[str]:
    if len(text) <= limit:
        yield text
        return
    start = 0
    while start < len(text):
        end = min(start + limit, len(text))
        if end < len(text):
            candidates = [text.rfind(mark, start + limit // 2, end) for mark in ("。", "！", "？", ". ", "; ", "\n")]
            boundary = max(candidates)
            if boundary > start:
                end = boundary + 1
        yield normalized(text[start:end])
        if end == len(text):
            break
        start = max(end - overlap, start + 1)


def make_page_chunks(text: str, limit: int = 1800) -> list[tuple[str, str]]:
    by_language: dict[str, list[str]] = {"zh-Hans": [], "en": [], "zh-Hans+en": []}
    for language, paragraph in page_paragraphs(text):
        by_language.setdefault(language, []).append(paragraph)

    chunks: list[tuple[str, str]] = []
    for language in ("zh-Hans", "en", "zh-Hans+en"):
        current: list[str] = []
        length = 0
        for paragraph in by_language.get(language, []):
            if len(paragraph) > limit:
                if current:
                    chunks.append((language, normalized("\n\n".join(current))))
                    current, length = [], 0
                chunks.extend((language, piece) for piece in split_long_text(paragraph, limit))
            elif current and length + len(paragraph) + 2 > limit:
                chunks.append((language, normalized("\n\n".join(current))))
                current, length = [paragraph], len(paragraph)
            else:
                current.append(paragraph)
                length += len(paragraph) + (2 if length else 0)
        if current:
            chunks.append((language, normalized("\n\n".join(current))))
    return [(language, text) for language, text in chunks if text]


def jsonl_write(path: Path, rows: Iterable[dict]) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def schema(connection: sqlite3.Connection) -> None:
    connection.executescript(
        """
        PRAGMA journal_mode=DELETE;
        PRAGMA foreign_keys=ON;
        CREATE TABLE documents (
            id TEXT PRIMARY KEY, title TEXT NOT NULL, title_en TEXT,
            language TEXT NOT NULL, source_type TEXT NOT NULL,
            source_path TEXT NOT NULL, checksum TEXT NOT NULL,
            page_count INTEGER, rights_policy TEXT NOT NULL,
            corpus_version TEXT NOT NULL
        );
        CREATE TABLE bible_verses (
            translation TEXT NOT NULL, language TEXT NOT NULL,
            book_id TEXT NOT NULL, book_name TEXT NOT NULL,
            chapter INTEGER NOT NULL, verse INTEGER NOT NULL,
            text TEXT NOT NULL, source_id TEXT UNIQUE NOT NULL,
            document_id TEXT NOT NULL REFERENCES documents(id),
            PRIMARY KEY (translation, book_id, chapter, verse)
        );
        CREATE TABLE footnotes (
            translation TEXT NOT NULL, language TEXT NOT NULL,
            book_id TEXT NOT NULL, book_name TEXT NOT NULL,
            chapter INTEGER NOT NULL, verse INTEGER NOT NULL,
            note_no INTEGER NOT NULL, heading_text TEXT NOT NULL,
            text TEXT NOT NULL, source_id TEXT UNIQUE NOT NULL,
            document_id TEXT NOT NULL REFERENCES documents(id),
            PRIMARY KEY (translation, book_id, chapter, verse, note_no)
        );
        CREATE TABLE chunks (
            source_id TEXT PRIMARY KEY, document_id TEXT NOT NULL REFERENCES documents(id),
            language TEXT NOT NULL, source_type TEXT NOT NULL,
            page_start INTEGER, page_end INTEGER, page_label TEXT,
            book_id TEXT, chapter INTEGER, verse_start INTEGER, verse_end INTEGER,
            note_no INTEGER, heading_path TEXT, text TEXT NOT NULL,
            checksum TEXT NOT NULL, corpus_version TEXT NOT NULL
        );
        CREATE TABLE topics (
            id TEXT PRIMARY KEY, references_json TEXT NOT NULL
        );
        CREATE TABLE topic_aliases (
            topic_id TEXT NOT NULL REFERENCES topics(id), language TEXT NOT NULL,
            alias TEXT NOT NULL, PRIMARY KEY (topic_id, language, alias)
        );
        CREATE INDEX chunks_document_page ON chunks(document_id, page_start);
        CREATE INDEX chunks_scripture ON chunks(book_id, chapter, verse_start, verse_end);
        CREATE INDEX footnotes_scripture ON footnotes(book_id, chapter, verse);
        CREATE VIRTUAL TABLE chunks_fts USING fts5(source_id UNINDEXED, text, tokenize='unicode61');
        """
    )


def add_document(connection: sqlite3.Connection, row: dict) -> None:
    connection.execute(
        """INSERT INTO documents
        (id,title,title_en,language,source_type,source_path,checksum,page_count,rights_policy,corpus_version)
        VALUES (:id,:title,:title_en,:language,:source_type,:source_path,:checksum,:page_count,:rights_policy,:corpus_version)""",
        row,
    )


def add_chunk(connection: sqlite3.Connection, row: dict) -> None:
    columns = [
        "source_id", "document_id", "language", "source_type", "page_start", "page_end",
        "page_label", "book_id", "chapter", "verse_start", "verse_end", "note_no",
        "heading_path", "text", "checksum", "corpus_version",
    ]
    connection.execute(
        f"INSERT INTO chunks ({','.join(columns)}) VALUES ({','.join('?' for _ in columns)})",
        [row.get(column) for column in columns],
    )
    connection.execute("INSERT INTO chunks_fts(source_id,text) VALUES (?,?)", (row["source_id"], row["text"]))


def scripture_chunks(verses: list[Verse], size: int = 5) -> Iterable[dict]:
    grouped: dict[tuple[str, int], list[Verse]] = {}
    for verse in verses:
        grouped.setdefault((verse.book_id, verse.chapter), []).append(verse)
    for (book_id, chapter), chapter_verses in grouped.items():
        for offset in range(0, len(chapter_verses), size):
            group = chapter_verses[offset:offset + size]
            first, last = group[0], group[-1]
            source_id = f"bible:{TRANSLATION.lower()}:{book_id}.{chapter}.{first.verse}-{last.verse}"
            text = "\n".join(f"{item.verse} {item.text}" for item in group)
            yield {
                "source_id": source_id,
                "document_id": "bible-rcv-zh-cn",
                "language": "zh-Hans",
                "source_type": "bible",
                "page_start": None, "page_end": None, "page_label": None,
                "book_id": book_id, "chapter": chapter,
                "verse_start": first.verse, "verse_end": last.verse,
                "note_no": None,
                "heading_path": f"{BOOK_NAMES[book_id]} > 第{chapter}章",
                "text": text,
                "checksum": hashlib.sha256(text.encode()).hexdigest(),
                "corpus_version": CORPUS_VERSION,
            }


def build(root: Path, out: Path) -> dict:
    epub = root / "恢复本圣经带注解.epub"
    missing = [str(root / item["path"]) for item in PDF_SOURCES if not (root / item["path"]).is_file()]
    if not epub.is_file() or missing:
        raise FileNotFoundError("Missing Phase 1 sources: " + ", ".join(([str(epub)] if not epub.is_file() else []) + missing))
    for command in ("pdfinfo", "pdftotext"):
        if subprocess.run(["which", command], capture_output=True).returncode:
            raise RuntimeError(f"Required command not found: {command}")

    out.mkdir(parents=True, exist_ok=True)
    database = out / "ecclesia_phase1.sqlite3"
    for database_file in (database, Path(str(database) + "-wal"), Path(str(database) + "-shm")):
        if database_file.exists():
            database_file.unlink()
    connection = sqlite3.connect(database)
    schema(connection)

    documents: list[dict] = []
    all_chunks: list[dict] = []

    bible_doc = {
        "id": "bible-rcv-zh-cn", "title": "恢复本圣经（带注解）", "title_en": "Recovery Version Bible with Footnotes",
        "language": "zh-Hans", "source_type": "bible_epub", "source_path": epub.relative_to(root).as_posix(),
        "checksum": sha256(epub), "page_count": None, "rights_policy": "unreviewed", "corpus_version": CORPUS_VERSION,
    }
    add_document(connection, bible_doc)
    documents.append(bible_doc)

    verses, notes = parse_bible(epub)
    for verse in verses:
        connection.execute(
            "INSERT INTO bible_verses VALUES (?,?,?,?,?,?,?,?,?)",
            (TRANSLATION, "zh-Hans", verse.book_id, BOOK_NAMES[verse.book_id], verse.chapter, verse.verse,
             verse.text, f"verse:{TRANSLATION.lower()}:{verse.book_id}.{verse.chapter}.{verse.verse}", bible_doc["id"]),
        )
    for note in notes:
        connection.execute(
            "INSERT INTO footnotes VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (TRANSLATION, "zh-Hans", note.book_id, BOOK_NAMES[note.book_id], note.chapter, note.verse,
             note.note_no, note.heading_text, note.text,
             f"footnote:{TRANSLATION.lower()}:{note.book_id}.{note.chapter}.{note.verse}.{note.note_no}", bible_doc["id"]),
        )

    for chunk in scripture_chunks(verses):
        add_chunk(connection, chunk)
        all_chunks.append(chunk)
    for note in notes:
        text = f"经文：{note.heading_text}\n注{note.note_no}：{note.text}"
        chunk = {
            "source_id": f"footnote:{TRANSLATION.lower()}:{note.book_id}.{note.chapter}.{note.verse}.{note.note_no}",
            "document_id": bible_doc["id"], "language": "zh-Hans", "source_type": "footnote",
            "page_start": None, "page_end": None, "page_label": None,
            "book_id": note.book_id, "chapter": note.chapter, "verse_start": note.verse, "verse_end": note.verse,
            "note_no": note.note_no, "heading_path": f"{BOOK_NAMES[note.book_id]} > {note.chapter}:{note.verse} > 注{note.note_no}",
            "text": text, "checksum": hashlib.sha256(text.encode()).hexdigest(), "corpus_version": CORPUS_VERSION,
        }
        add_chunk(connection, chunk)
        all_chunks.append(chunk)

    pdf_stats: list[dict] = []
    for source in PDF_SOURCES:
        path = root / source["path"]
        count = pdf_page_count(path)
        pages = extract_pdf_pages(path)
        if len(pages) != count:
            raise ValueError(f"Page count mismatch for {path}: pdfinfo={count}, text={len(pages)}")
        document = {
            **source, "language": "zh-Hans+en", "source_type": "bilingual_pdf",
            "source_path": source["path"], "checksum": sha256(path), "page_count": count,
            "rights_policy": "unreviewed", "corpus_version": CORPUS_VERSION,
        }
        document.pop("path")
        add_document(connection, document)
        documents.append(document)
        language_counts: Counter[str] = Counter()
        chunk_count = 0
        empty_pages = 0
        for pdf_page, raw_page in enumerate(pages, start=1):
            label = page_label(raw_page)
            clean = clean_pdf_page(raw_page)
            page_chunks = make_page_chunks(clean)
            if not page_chunks:
                empty_pages += 1
            sequence_by_language: Counter[str] = Counter()
            for language, text in page_chunks:
                sequence_by_language[language] += 1
                language_counts[language] += 1
                chunk_count += 1
                lang_code = {"zh-Hans": "zh", "en": "en", "zh-Hans+en": "multi"}.get(language, "x")
                source_id = f"doc:{document['id']}:pdf-{pdf_page:04d}:{lang_code}-{sequence_by_language[language]:03d}"
                chunk = {
                    "source_id": source_id, "document_id": document["id"], "language": language,
                    "source_type": "reference_book", "page_start": pdf_page, "page_end": pdf_page,
                    "page_label": label, "book_id": None, "chapter": None, "verse_start": None,
                    "verse_end": None, "note_no": None,
                    "heading_path": document["title"] if language != "en" else document["title_en"],
                    "text": text, "checksum": hashlib.sha256(text.encode()).hexdigest(),
                    "corpus_version": CORPUS_VERSION,
                }
                add_chunk(connection, chunk)
                all_chunks.append(chunk)
        pdf_stats.append({
            "document_id": document["id"], "pages": count, "chunks": chunk_count,
            "empty_text_pages": empty_pages, "chunk_languages": dict(language_counts),
        })

    for topic in TOPICS:
        connection.execute("INSERT INTO topics VALUES (?,?)", (topic["id"], json.dumps(topic["references"])))
        for language, aliases in topic["aliases"].items():
            for alias in aliases:
                connection.execute("INSERT INTO topic_aliases VALUES (?,?,?)", (topic["id"], language, alias))

    connection.commit()
    qa = run_qa(connection, root, documents, all_chunks, verses, notes)
    connection.close()

    jsonl_write(out / "documents.jsonl", documents)
    jsonl_write(out / "bible_verses.jsonl", (
        {
            "source_id": f"verse:{TRANSLATION.lower()}:{v.book_id}.{v.chapter}.{v.verse}",
            "translation": TRANSLATION, "language": "zh-Hans", "book_id": v.book_id,
            "book_name": BOOK_NAMES[v.book_id], "chapter": v.chapter, "verse": v.verse, "text": v.text,
        } for v in verses
    ))
    jsonl_write(out / "footnotes.jsonl", (
        {
            "source_id": f"footnote:{TRANSLATION.lower()}:{n.book_id}.{n.chapter}.{n.verse}.{n.note_no}",
            "translation": TRANSLATION, "language": "zh-Hans", "book_id": n.book_id,
            "book_name": BOOK_NAMES[n.book_id], "chapter": n.chapter, "verse": n.verse,
            "note_no": n.note_no, "heading_text": n.heading_text, "text": n.text,
        } for n in notes
    ))
    jsonl_write(out / "chunks.jsonl", (
        {"id": chunk["source_id"], "text": chunk["text"], "metadata": {key: value for key, value in chunk.items() if key not in {"source_id", "text"}}}
        for chunk in all_chunks
    ))
    jsonl_write(out / "topics.jsonl", TOPICS)

    summary = {
        "corpus_version": CORPUS_VERSION, "documents": len(documents), "bible_books": len(BOOKS),
        "bible_verses_including_superscriptions": len(verses),
        "canonical_bible_verses": sum(v.verse > 0 for v in verses),
        "psalm_superscriptions": sum(v.book_id == "Ps" and v.verse == 0 for v in verses),
        "footnotes": len(notes), "chunks": len(all_chunks), "pdfs": pdf_stats, "qa": qa,
    }
    (out / "phase1-summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    write_report(out / "PHASE1_REPORT.md", summary)
    return summary


def run_qa(
    connection: sqlite3.Connection, root: Path, documents: list[dict], chunks: list[dict],
    verses: list[Verse], notes: list[Footnote],
) -> dict:
    checks: dict[str, dict] = {}

    def check(name: str, passed: bool, detail: str) -> None:
        checks[name] = {"passed": bool(passed), "detail": detail}

    canonical = sum(verse.verse > 0 for verse in verses)
    superscriptions = sum(verse.book_id == "Ps" and verse.verse == 0 for verse in verses)
    check("canonical_verse_count", canonical == 31102, f"expected=31102 actual={canonical}")
    check("psalm_superscription_count", superscriptions == 116, f"expected=116 actual={superscriptions}")
    check("footnote_count", len(notes) == 15793, f"expected=15793 actual={len(notes)}")
    check("unique_chunk_ids", len(chunks) == len({c["source_id"] for c in chunks}), f"chunks={len(chunks)}")
    check("all_source_files_exist", all((root / d["source_path"]).is_file() for d in documents), f"documents={len(documents)}")
    page_ranges_ok = all(
        c["page_start"] is None or 1 <= c["page_start"] <= next(d["page_count"] for d in documents if d["id"] == c["document_id"])
        for c in chunks
    )
    check("pdf_page_ranges", page_ranges_ok, "all PDF citations fall within pdfinfo page count")

    matt_2819 = connection.execute(
        "SELECT text FROM bible_verses WHERE book_id='Matt' AND chapter=28 AND verse=19"
    ).fetchone()
    check("matt_28_19", bool(matt_2819 and "父、子、圣灵" in matt_2819[0]), matt_2819[0][:120] if matt_2819 else "missing")
    matt_notes = connection.execute(
        "SELECT COUNT(*) FROM footnotes WHERE book_id='Matt' AND chapter=28 AND verse=19"
    ).fetchone()[0]
    check("matt_28_19_footnotes", matt_notes == 6, f"expected=6 actual={matt_notes}")
    john_11 = connection.execute(
        "SELECT text FROM bible_verses WHERE book_id='John' AND chapter=1 AND verse=1"
    ).fetchone()
    check("john_1_1", bool(john_11 and "太初有话" in john_11[0]), john_11[0] if john_11 else "missing")
    calling = connection.execute(
        "SELECT references_json FROM topics JOIN topic_aliases ON topics.id=topic_aliases.topic_id WHERE alias='主耶稣呼召门徒'"
    ).fetchone()
    check("calling_disciples_topic", bool(calling and "Matt.4.18-22" in calling[0]), calling[0] if calling else "missing")
    triune_hits = connection.execute(
        "SELECT COUNT(DISTINCT document_id) FROM chunks WHERE source_type='reference_book' AND (text LIKE '%三一神%' OR text LIKE '%Triune God%')"
    ).fetchone()[0]
    check("triune_retrieval_coverage", triune_hits >= 5, f"representative_books_with_hits={triune_hits}")
    return {"passed": all(item["passed"] for item in checks.values()), "checks": checks}


def write_report(path: Path, summary: dict) -> None:
    pdf_rows = "\n".join(
        f"| `{item['document_id']}` | {item['pages']} | {item['chunks']} | {item['empty_text_pages']} | "
        f"{item['chunk_languages'].get('zh-Hans', 0)} / {item['chunk_languages'].get('en', 0)} / {item['chunk_languages'].get('zh-Hans+en', 0)} |"
        for item in summary["pdfs"]
    )
    qa_rows = "\n".join(
        f"| {'PASS' if item['passed'] else 'FAIL'} | `{name}` | {item['detail'].replace('|', '/')} |"
        for name, item in summary["qa"]["checks"].items()
    )
    report = f"""# Phase 1 structured corpus report

Corpus version: `{summary['corpus_version']}`

## Result

- Sources imported: **{summary['documents']}** (1 annotated Bible EPUB + 9 bilingual representative PDFs)
- Bible: **{summary['bible_books']} books**, **{summary['canonical_bible_verses']:,} canonical verses** plus **{summary['psalm_superscriptions']} Psalm superscriptions**
- Footnotes: **{summary['footnotes']:,} individually addressable notes**
- Retrieval chunks: **{summary['chunks']:,}**
- QA: **{'PASS' if summary['qa']['passed'] else 'FAIL'}**

## Citation contract

- Bible verse: `verse:rcv-zh-cn:Matt.28.19`
- Bible footnote: `footnote:rcv-zh-cn:Matt.28.19.5`
- Reference book: `doc:<document-id>:pdf-<PDF page>:<language>-<sequence>`
- `page_start` is the physical PDF page used by viewers. `page_label` preserves a detected printed page when available.
- Every chunk carries `document_id`, language, source type, checksum, and corpus version.

The PDF sources are bilingual side-by-side pages. Poppler's plain text order was visually verified to emit the Chinese column and then the English column. Chunks are separated by detected language without crossing a physical PDF page.

## PDF import

| Document | PDF pages | Chunks | Empty-text pages | zh / en / mixed chunks |
|---|---:|---:|---:|---:|
{pdf_rows}

## QA

| Status | Check | Detail |
|---|---|---|
{qa_rows}

## Artifacts

- `ecclesia_phase1.sqlite3`: complete local structured corpus and FTS index
- `documents.jsonl`: document/source registry
- `bible_verses.jsonl`: one row per verse or superscription
- `footnotes.jsonl`: one row per numbered footnote
- `chunks.jsonl`: embedding/vector-database import contract
- `topics.jsonl`: reviewed multilingual aliases and exact Scripture reference sets
- `phase1-summary.json`: machine-readable counts and QA evidence

Run a local evidence lookup with:

```bash
python3 scripts/phase1_query.py "主耶稣呼召门徒是在圣经的哪里？"
python3 scripts/phase1_query.py "什么是神圣三一？"
python3 scripts/phase1_query.py "马太福音28:19"
```

## Current boundary

All source rights remain `unreviewed`. These artifacts are suitable for local/private retrieval testing, but public deployment should remain gated until each source's redistribution policy is approved. Actual Cloudflare/Pinecone upload is intentionally not performed without project credentials and a rights decision.

The imported Brother Nee source is a prayer collection, not a verified biography. A question such as “倪柝声弟兄什么时候离开上海？” correctly returns `insufficient_evidence`; a dedicated chronology/biography source is still required for historical claims.
"""
    path.write_text(report, encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--out", type=Path)
    args = parser.parse_args()
    root = args.root.resolve()
    out = (args.out or root / "output" / "phase1").resolve()
    try:
        summary = build(root, out)
    except Exception as exc:
        print(f"phase1 build failed: {exc}", file=sys.stderr)
        return 1
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["qa"]["passed"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
