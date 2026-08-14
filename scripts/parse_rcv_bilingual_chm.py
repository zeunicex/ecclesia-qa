#!/usr/bin/env python3
"""Extract the bilingual Recovery Version CHM into verse-level JSONL."""

from __future__ import annotations

import argparse
import hashlib
import html
import json
import re
import subprocess
import tempfile
from pathlib import Path


BOOKS = [
    ("Gen", "创世记", "Genesis", 50), ("Exod", "出埃及记", "Exodus", 40),
    ("Lev", "利未记", "Leviticus", 27), ("Num", "民数记", "Numbers", 36),
    ("Deut", "申命记", "Deuteronomy", 34), ("Josh", "约书亚记", "Joshua", 24),
    ("Judg", "士师记", "Judges", 21), ("Ruth", "路得记", "Ruth", 4),
    ("1Sam", "撒母耳记上", "1 Samuel", 31), ("2Sam", "撒母耳记下", "2 Samuel", 24),
    ("1Kgs", "列王纪上", "1 Kings", 22), ("2Kgs", "列王纪下", "2 Kings", 25),
    ("1Chr", "历代志上", "1 Chronicles", 29), ("2Chr", "历代志下", "2 Chronicles", 36),
    ("Ezra", "以斯拉记", "Ezra", 10), ("Neh", "尼希米记", "Nehemiah", 13),
    ("Esth", "以斯帖记", "Esther", 10), ("Job", "约伯记", "Job", 42),
    ("Ps", "诗篇", "Psalms", 150), ("Prov", "箴言", "Proverbs", 31),
    ("Eccl", "传道书", "Ecclesiastes", 12), ("Song", "雅歌", "Song of Songs", 8),
    ("Isa", "以赛亚书", "Isaiah", 66), ("Jer", "耶利米书", "Jeremiah", 52),
    ("Lam", "耶利米哀歌", "Lamentations", 5), ("Ezek", "以西结书", "Ezekiel", 48),
    ("Dan", "但以理书", "Daniel", 12), ("Hos", "何西阿书", "Hosea", 14),
    ("Joel", "约珥书", "Joel", 3), ("Amos", "阿摩司书", "Amos", 9),
    ("Obad", "俄巴底亚书", "Obadiah", 1), ("Jonah", "约拿书", "Jonah", 4),
    ("Mic", "弥迦书", "Micah", 7), ("Nah", "那鸿书", "Nahum", 3),
    ("Hab", "哈巴谷书", "Habakkuk", 3), ("Zeph", "西番雅书", "Zephaniah", 3),
    ("Hag", "哈该书", "Haggai", 2), ("Zech", "撒迦利亚书", "Zechariah", 14),
    ("Mal", "玛拉基书", "Malachi", 4), ("Matt", "马太福音", "Matthew", 28),
    ("Mark", "马可福音", "Mark", 16), ("Luke", "路加福音", "Luke", 24),
    ("John", "约翰福音", "John", 21), ("Acts", "使徒行传", "Acts", 28),
    ("Rom", "罗马书", "Romans", 16), ("1Cor", "哥林多前书", "1 Corinthians", 16),
    ("2Cor", "哥林多后书", "2 Corinthians", 13), ("Gal", "加拉太书", "Galatians", 6),
    ("Eph", "以弗所书", "Ephesians", 6), ("Phil", "腓立比书", "Philippians", 4),
    ("Col", "歌罗西书", "Colossians", 4), ("1Thess", "帖撒罗尼迦前书", "1 Thessalonians", 5),
    ("2Thess", "帖撒罗尼迦后书", "2 Thessalonians", 3), ("1Tim", "提摩太前书", "1 Timothy", 6),
    ("2Tim", "提摩太后书", "2 Timothy", 4), ("Titus", "提多书", "Titus", 3),
    ("Phlm", "腓利门书", "Philemon", 1), ("Heb", "希伯来书", "Hebrews", 13),
    ("Jas", "雅各书", "James", 5), ("1Pet", "彼得前书", "1 Peter", 5),
    ("2Pet", "彼得后书", "2 Peter", 3), ("1John", "约翰一书", "1 John", 5),
    ("2John", "约翰二书", "2 John", 1), ("3John", "约翰三书", "3 John", 1),
    ("Jude", "犹大书", "Jude", 1), ("Rev", "启示录", "Revelation", 22),
]
CORPUS_VERSION = "phase4-b-2026-08-12"
ROW = re.compile(
    r'<a name=(\d+)>(\d+):(\d+)</a></td><td class=td>(.*?)</td></tr>',
    re.IGNORECASE | re.DOTALL,
)


def clean(fragment: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", fragment))).strip()


def chinese_fallback(path: Path) -> dict[tuple[str, int, int], str]:
    rows = {}
    if not path.exists():
        return rows
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        if row["verse"] > 0:
            rows[(row["book_id"], row["chapter"], row["verse"])] = row["text"]
    return rows


def parse_pages(root: Path, fallback: dict[tuple[str, int, int], str]) -> tuple[list[dict], list[dict], int]:
    bilingual = []
    english = []
    fallback_used = 0
    seen = set()
    page = 1
    for book_id, book_zh, book_en, chapters in BOOKS:
        book_chapters = set()
        for _ in range(chapters):
            source = (root / f"{page}.htm").read_text(encoding="gb18030")
            found = ROW.findall(source)
            if not found:
                raise ValueError(f"No verses found in page {page}")
            for anchor, found_chapter, verse, body in found:
                chapter = int(found_chapter)
                key = (book_id, chapter, int(verse))
                # One source-page anchor is duplicated at Rev. 12:18; chapter:verse is authoritative.
                if key in seen:
                    raise ValueError(f"Bad verse identity on page {page}: {found_chapter}:{verse}")
                seen.add(key)
                book_chapters.add(chapter)
                parts = re.split(r"<br\s*/?>", body, maxsplit=1, flags=re.IGNORECASE)
                if len(parts) != 2:
                    raise ValueError(f"Missing bilingual separator on page {page}: {chapter}:{verse}")
                zh_text = clean(parts[0])
                if not zh_text:
                    zh_text = fallback.get(key, "")
                    fallback_used += 1
                en_text = clean(parts[1])
                if not zh_text or not en_text:
                    raise ValueError(f"Empty verse text: {book_id}.{chapter}.{verse}")
                bilingual.append({
                    "book_id": book_id, "book_name": book_zh, "book_name_en": book_en,
                    "chapter": chapter, "verse": int(verse), "zh_text": zh_text, "en_text": en_text,
                })
                english.append({
                    "translation": "RCV-EN", "language": "en", "book_id": book_id,
                    "book_name": book_en, "chapter": chapter, "verse": int(verse), "text": en_text,
                    "source_id": f"verse:rcv-en:{book_id}.{chapter}.{verse}",
                })
            page += 1
        if book_chapters != set(range(1, chapters + 1)):
            raise ValueError(f"Incomplete chapter set for {book_id}: {sorted(book_chapters)}")
    if page != 1190 or len(english) != 31_102:
        raise ValueError(f"Unexpected corpus shape: pages={page - 1} verses={len(english)}")
    return bilingual, english, fallback_used


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.write_text("".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows), encoding="utf-8")


def scripture_chunks(verses: list[dict], size: int = 5) -> list[dict]:
    chunks = []
    grouped = {}
    for verse in verses:
        grouped.setdefault((verse["book_id"], verse["book_name"], verse["chapter"]), []).append(verse)
    for (book_id, book_name, chapter), rows in grouped.items():
        for offset in range(0, len(rows), size):
            group = rows[offset:offset + size]
            text = "\n".join(f'{row["verse"]} {row["text"]}' for row in group)
            first, last = group[0]["verse"], group[-1]["verse"]
            chunks.append({
                "id": f"bible:rcv-en:{book_id}.{chapter}.{first}-{last}",
                "metadata": {
                    "document_id": "bible-rcv-en-chm", "language": "en", "source_type": "bible",
                    "corpus_version": CORPUS_VERSION, "checksum": hashlib.sha256(text.encode()).hexdigest(),
                    "book_id": book_id, "chapter": chapter, "verse_start": first, "verse_end": last,
                    "heading_path": f"{book_name} > Chapter {chapter}",
                },
                "text": text,
            })
    return chunks


def sql_value(value: object) -> str:
    if value is None:
        return "NULL"
    if isinstance(value, (int, float)):
        return str(value)
    return "'" + str(value).replace("'", "''") + "'"


def write_d1_sql(path: Path, verses: list[dict], chunks: list[dict], source_checksum: str) -> None:
    lines = [(
        "INSERT OR REPLACE INTO documents (id,title,title_en,language,source_type,checksum,corpus_version,rights_policy) VALUES "
        f"('bible-rcv-en-chm','Recovery Version Bible','Recovery Version Bible','en','bible_chm','{source_checksum}',"
        f"'{CORPUS_VERSION}','unreviewed');"
    )]
    for row in verses:
        values = [row[key] for key in ("book_id", "chapter", "verse", "translation", "language", "book_name", "text", "source_id")]
        lines.append("INSERT OR REPLACE INTO bible_verses "
                     "(book_id,chapter,verse,translation,language,book_name,text,source_id) VALUES ("
                     + ",".join(sql_value(value) for value in values) + ");")
    lines.append("DELETE FROM search_chunks WHERE source_id LIKE 'bible:rcv-en:%';")
    for chunk in chunks:
        metadata = chunk["metadata"]
        values = [chunk["id"], "bible", "Recovery Version Bible", metadata["heading_path"], None, None, "en", chunk["text"]]
        lines.append("INSERT INTO search_chunks "
                     "(source_id,source_type,title,reference,pdf_page,pdf_page_end,language,text) VALUES ("
                     + ",".join(sql_value(value) for value in values) + ");")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--chm", type=Path, default=Path("恢复本中英对照.chm"))
    parser.add_argument("--chinese", type=Path, default=Path("output/phase1/bible_verses.jsonl"))
    parser.add_argument("--out", type=Path, default=Path("output/rcv-bilingual"))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="ecclesia-rcv-") as temporary:
        subprocess.run(["extract_chmLib", str(args.chm), temporary], check=True, stdout=subprocess.DEVNULL)
        fallback = chinese_fallback(args.chinese)
        bilingual, english, fallback_used = parse_pages(Path(temporary), fallback)
    assert english[0]["text"] == "In the beginning God created the heavens and the earth."
    assert next(row for row in english if row["source_id"] == "verse:rcv-en:Matt.28.19")["text"].startswith("Go therefore")
    assert english[-1]["text"] == "The grace of the Lord Jesus be with all the saints. Amen."
    order = {book[0]: index for index, book in enumerate(BOOKS)}
    bilingual.sort(key=lambda row: (order[row["book_id"]], row["chapter"], row["verse"]))
    english.sort(key=lambda row: (order[row["book_id"]], row["chapter"], row["verse"]))
    chunks = scripture_chunks(english)
    source_checksum = hashlib.sha256(args.chm.read_bytes()).hexdigest()
    write_jsonl(args.out / "bible_verses_bilingual.jsonl", bilingual)
    write_jsonl(args.out / "bible_verses_en.jsonl", english)
    write_jsonl(args.out / "chunks.jsonl", chunks)
    document = {
        "id": "bible-rcv-en-chm", "title": "Recovery Version Bible", "title_en": "Recovery Version Bible",
        "language": "en", "source_type": "bible_chm", "source_path": str(args.chm),
        "checksum": source_checksum, "corpus_version": CORPUS_VERSION, "rights_policy": "unreviewed",
    }
    write_jsonl(args.out / "documents.jsonl", [document])
    write_d1_sql(args.out / "d1-english-bible.sql", english, chunks, source_checksum)
    english_keys = {(row["book_id"], row["chapter"], row["verse"]) for row in english}
    existing_only = sorted(fallback.keys() - english_keys)
    source_only = sorted(english_keys - fallback.keys())
    summary = {
        "source": str(args.chm),
        "source_sha256": source_checksum,
        "books": len(BOOKS), "chapters": sum(book[3] for book in BOOKS),
        "verses": len(english), "pinecone_chunks": len(chunks), "english_empty": 0,
        "chinese_filled_from_existing_rcv": fallback_used,
        "footnotes": 0,
        "existing_chinese_keys_equal": not existing_only and not source_only,
        "existing_chinese_only": [f"{book}.{chapter}.{verse}" for book, chapter, verse in existing_only],
        "bilingual_source_only": [f"{book}.{chapter}.{verse}" for book, chapter, verse in source_only],
    }
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
