#!/usr/bin/env python3
"""Build a reproducible Phase 0 corpus manifest and inspect the Bible EPUB."""

import argparse
import csv
import hashlib
import json
import mimetypes
import os
import re
import subprocess
import zipfile
from collections import Counter, defaultdict
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree as ET


EXCLUDED_DIRS = {".git", ".agents", ".codex", "reports", "scripts"}
EXCLUDED_FILES = {"ARCHITECTURE.md"}
TEXT_EXTENSIONS = {".txt", ".md", ".html", ".htm", ".xhtml", ".xml"}
ARCHIVE_EXTENSIONS = {".zip", ".rar", ".7z"}
REFERENCE_EXTENSIONS = {".pdf", ".epub", ".chm", ".pdb", ".doc", ".docx"}
SIMPLIFIED_MARKERS = set("这为个们来时会里后发国东见说门体圣经书话灵万与从并过还将实应亲间无开")
TRADITIONAL_MARKERS = set("這為個們來時會裡後發國東見說門體聖經書話靈萬與從並過還將實應親間無開")


class TextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.parts = []

    def handle_data(self, data):
        self.parts.append(data)


def sha256_file(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def sample_epub(path, limit=30000):
    parts = []
    with zipfile.ZipFile(path) as archive:
        for name in archive.namelist():
            if not name.lower().endswith((".xhtml", ".html", ".htm")):
                continue
            parser = TextExtractor()
            parser.feed(archive.read(name).decode("utf-8", errors="ignore"))
            parts.append(" ".join(parser.parts))
            if sum(map(len, parts)) >= limit:
                break
    return " ".join(parts)[:limit]


def sample_pdf(path, limit=30000):
    try:
        result = subprocess.run(
            ["pdftotext", "-f", "1", "-l", "3", str(path), "-"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            timeout=20,
            check=False,
        )
        return result.stdout.decode("utf-8", errors="ignore")[:limit]
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return ""


def sample_text(path, limit=30000):
    try:
        return path.read_text(encoding="utf-8", errors="ignore")[:limit]
    except OSError:
        return ""


def language_guess(name, sample=""):
    lowered = Path(name).name.lower()
    full_name = name.lower()
    explicit_bilingual = bool(
        re.search(r"en\s*[&+_-]\s*(?:ch|chs|zh)|(?:ch|chs|zh)\s*[&+_-]\s*en", full_name)
    )
    explicit_en = bool(re.search(r"(^|[^a-z])(en|eng|english)([^a-z]|$)", lowered))
    explicit_hans = bool(re.search(r"(^|[^a-z])(ch|chs|zh-cn|hans)([^a-z]|$)", lowered)) or "简体" in name
    explicit_hant = bool(re.search(r"(^|[^a-z])(cht|zh-tw|hant)([^a-z]|$)", lowered)) or "繁體" in name or "繁体" in name

    cjk = sum("\u3400" <= char <= "\u9fff" for char in sample)
    latin = sum(char.isascii() and char.isalpha() for char in sample)
    simplified = sum(char in SIMPLIFIED_MARKERS for char in sample)
    traditional = sum(char in TRADITIONAL_MARKERS for char in sample)

    if cjk >= 40:
        chinese = "zh-Hant" if traditional > simplified * 1.2 else "zh-Hans"
        if explicit_hant or explicit_hans:
            return chinese, "high", "content_sample+filename"
        if latin >= cjk * 0.35:
            return chinese + "+en", "medium", "content_sample"
        return chinese, "medium", "content_sample"
    if latin >= 80:
        return "en", "medium", "content_sample"
    if explicit_hant:
        return ("zh-Hant+en" if explicit_en else "zh-Hant"), "high", "filename"
    if explicit_hans:
        return ("zh-Hans+en" if explicit_en else "zh-Hans"), "high", "filename"
    if explicit_en:
        return "en", "low", "filename"
    if explicit_bilingual:
        return "zh-Hans+en", "medium", "filename"
    if re.search(r"[\u3400-\u9fff]", name):
        return "zh-Hans", "low", "filename"
    return "unknown", "low", "none"


def corpus_role(path):
    extension = path.suffix.lower()
    name = path.name.lower()
    if extension in ARCHIVE_EXTENSIONS:
        return "archive"
    if extension == ".mp3":
        return "audio"
    if extension in {".png", ".jpg", ".jpeg", ".gif", ".webp"}:
        return "image"
    if extension == ".epub" and ("圣经" in path.name or "bible" in name):
        return "bible"
    if extension in REFERENCE_EXTENSIONS:
        return "reference_document"
    return "unknown"


def iter_corpus_files(root):
    for directory, dirnames, filenames in os.walk(root):
        dirnames[:] = sorted(name for name in dirnames if name not in EXCLUDED_DIRS)
        base = Path(directory)
        for filename in sorted(filenames):
            if filename == ".DS_Store" or filename.startswith("._"):
                continue
            path = base / filename
            if path == root / filename and filename in EXCLUDED_FILES:
                continue
            if path.is_file():
                yield path


def inspect_epub(path):
    namespace = {"x": "http://www.w3.org/1999/xhtml"}
    books = []
    duplicate_ids = []
    linked_notes = []
    note_items = set()
    chapter_count = verse_block_count = verse_count = superscription_count = individual_note_count = 0

    with zipfile.ZipFile(path) as archive:
        xhtml_names = sorted(name for name in archive.namelist() if re.search(r"/Text/\d+\.xhtml$", name))
        for name in xhtml_names:
            root = ET.fromstring(archive.read(name))
            file_ids = set()
            title_node = root.find(".//x:title", namespace)
            title = "" if title_node is None else "".join(title_node.itertext()).strip()
            chapter_ids = []
            verse_blocks = []
            book_note_items = []
            book_linked_notes = []

            for element in root.iter():
                element_id = element.attrib.get("id")
                if element_id:
                    if element_id in file_ids:
                        duplicate_ids.append(f"{name}#{element_id}")
                    file_ids.add(element_id)
                if re.fullmatch(r"C\d+.+", element_id or ""):
                    chapter_ids.append(element_id)
                if re.fullmatch(r"V\d+.+\d+", element_id or ""):
                    verse_blocks.append(element)
                classes = set(element.attrib.get("class", "").split())
                if "duokan-footnote-item" in classes and element_id:
                    book_note_items.append(element_id)
                    individual_note_count += len(element.findall(".//x:sup", namespace))
                if "duokan-footnote" in classes:
                    href = element.attrib.get("href", "")
                    if href.startswith("#"):
                        book_linked_notes.append(href[1:])

            direct_verse_values = [
                int((child.text or "").strip())
                for paragraph in verse_blocks
                for child in list(paragraph)
                if child.tag.endswith("sup") and (child.text or "").strip().isdigit()
            ]
            direct_verse_numbers = sum(value > 0 for value in direct_verse_values)
            superscriptions = sum(value == 0 for value in direct_verse_values)
            if chapter_ids:
                first_heading = next(
                    (element for element in root.iter() if element.attrib.get("id") == chapter_ids[0]), None
                )
                heading_text = "" if first_heading is None else "".join(first_heading.itertext())
                chapter_match = re.search(r"第\s*(\d+)\s*章", heading_text)
                chapter_number = chapter_match.group(1) if chapter_match else "1"
                book_code = chapter_ids[0][len("C" + chapter_number) :]
            elif verse_blocks:
                first_id = verse_blocks[0].attrib["id"]
                first_verse = next(
                    (
                        (child.text or "").strip()
                        for child in list(verse_blocks[0])
                        if child.tag.endswith("sup") and (child.text or "").strip().isdigit()
                    ),
                    "1",
                )
                book_code = re.sub(r"1$", "", first_id[len("V" + first_verse) :])
            else:
                book_code = None
            chapters = len(chapter_ids) or (1 if verse_blocks else 0)
            books.append(
                {
                    "file": name,
                    "title": title,
                    "book_code": book_code,
                    "chapters": chapters,
                    "verse_blocks": len(verse_blocks),
                    "verses": direct_verse_numbers,
                    "superscriptions": superscriptions,
                    "footnote_links": len(book_linked_notes),
                    "footnote_items": len(book_note_items),
                }
            )
            chapter_count += chapters
            verse_block_count += len(verse_blocks)
            verse_count += direct_verse_numbers
            superscription_count += superscriptions
            linked_notes.extend(book_linked_notes)
            note_items.update(book_note_items)

        metadata = {}
        opf = ET.fromstring(archive.read("OEBPS/content.opf"))
        for key in ("title", "language", "date", "identifier"):
            node = opf.find(".//{http://purl.org/dc/elements/1.1/}" + key)
            metadata[key] = "" if node is None else (node.text or "").strip()

    broken_links = sorted(set(linked_notes) - note_items)
    unlinked_items = sorted(note_items - set(linked_notes))
    return {
        "path": path.name,
        "metadata": metadata,
        "books": books,
        "counts": {
            "book_files": len(books),
            "chapters": chapter_count,
            "verse_blocks": verse_block_count,
            "verses": verse_count,
            "psalm_superscriptions": superscription_count,
            "footnote_links": len(linked_notes),
            "footnote_items": len(note_items),
            "duplicate_footnote_links": len(linked_notes) - len(set(linked_notes)),
            "individual_footnote_markers": individual_note_count,
            "broken_footnote_links": len(broken_links),
            "unlinked_footnote_items": len(unlinked_items),
            "duplicate_ids": len(duplicate_ids),
            "duplicate_ids_by_prefix": dict(sorted(Counter(value.rsplit("#", 1)[-1][:1] for value in duplicate_ids).items())),
        },
        "broken_footnote_link_ids": broken_links[:100],
        "unlinked_footnote_item_ids": unlinked_items[:100],
        "duplicate_ids": duplicate_ids[:100],
        "anchor_patterns": {
            "chapter": "C{chapter}{book_code}",
            "verse_block": "V{first_verse}{book_code}{chapter}",
            "footnote_link_and_item": "N{verse}{book_code}{chapter}",
        },
    }


def write_json(path, value):
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def write_epub_markdown(path, report):
    counts = report["counts"]
    lines = [
        "# Recovery Version EPUB structure audit",
        "",
        f"- File: `{report['path']}`",
        f"- Title: {report['metadata']['title']}",
        f"- Language: `{report['metadata']['language']}`",
        f"- Book files: {counts['book_files']}",
        f"- Chapters: {counts['chapters']}",
        f"- Verses detected: {counts['verses']}",
        f"- Psalm superscriptions (`verse 0`, excluded from verse count): {counts['psalm_superscriptions']}",
        f"- Footnote links/items: {counts['footnote_links']} / {counts['footnote_items']}",
        f"- Repeated links to the same footnote item: {counts['duplicate_footnote_links']}",
        f"- Individual footnote markers: {counts['individual_footnote_markers']}",
        f"- Broken footnote links: {counts['broken_footnote_links']}",
        f"- Unlinked footnote items: {counts['unlinked_footnote_items']}",
        f"- Duplicate IDs: {counts['duplicate_ids']}",
        f"- Duplicate IDs by prefix: `{json.dumps(counts['duplicate_ids_by_prefix'], ensure_ascii=False)}`",
        "",
        "## Anchor model",
        "",
        "- Chapter: `C{chapter}{book_code}`",
        "- Verse paragraph: `V{first_verse}{book_code}{chapter}`; direct `<sup>` children mark each verse.",
        "- Footnote link/item: `N{verse}{book_code}{chapter}`.",
        "- One footnote item contains all numbered notes for that verse; its descendant `<sup>` markers identify individual note numbers.",
        "- Raw XHTML verse-paragraph IDs are not unique in every book. The production parser must derive each verse key from the direct `<sup>` value instead of trusting paragraph IDs as primary keys.",
        "",
        "## Books",
        "",
        "| # | Title | Code | Chapters | Verses | Footnote items |",
        "|---:|---|---|---:|---:|---:|",
    ]
    for number, book in enumerate(report["books"], 1):
        lines.append(
            f"| {number} | {book['title']} | `{book['book_code']}` | {book['chapters']} | {book['verses']} | {book['footnote_items']} |"
        )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def audit(root, output):
    output.mkdir(parents=True, exist_ok=True)
    records = []
    hashes = defaultdict(list)
    for path in iter_corpus_files(root):
        relative = path.relative_to(root).as_posix()
        extension = path.suffix.lower() or "[none]"
        sample = ""
        if extension == ".pdf":
            sample = sample_pdf(path)
        elif extension == ".epub":
            sample = sample_epub(path)
        elif extension in TEXT_EXTENSIONS:
            sample = sample_text(path)
        language, confidence, basis = language_guess(relative, sample)
        checksum = sha256_file(path)
        hashes[checksum].append(relative)
        records.append(
            {
                "path": relative,
                "filename": path.name,
                "extension": extension,
                "bytes": path.stat().st_size,
                "sha256": checksum,
                "mime_type": mimetypes.guess_type(path.name)[0] or "application/octet-stream",
                "corpus_role": corpus_role(path),
                "language_guess": language,
                "language_confidence": confidence,
                "language_basis": basis,
                "sample_characters": len(sample),
                "rights_policy": "unreviewed",
                "ingestion_status": "blocked_empty" if path.stat().st_size == 0 else "candidate",
            }
        )

    duplicate_groups = [
        {"sha256": digest, "bytes": next(record["bytes"] for record in records if record["sha256"] == digest), "paths": paths}
        for digest, paths in hashes.items()
        if len(paths) > 1
    ]
    duplicate_bytes = sum(group["bytes"] * (len(group["paths"]) - 1) for group in duplicate_groups)
    first_path_by_hash = {digest: paths[0] for digest, paths in hashes.items()}
    for record in records:
        first_path = first_path_by_hash[record["sha256"]]
        record["duplicate_of"] = None if record["path"] == first_path else first_path
    summary = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "root": str(root),
        "excluded_directories": sorted(EXCLUDED_DIRS),
        "file_count": len(records),
        "total_bytes": sum(record["bytes"] for record in records),
        "extensions": dict(sorted(Counter(record["extension"] for record in records).items())),
        "roles": dict(sorted(Counter(record["corpus_role"] for record in records).items())),
        "languages": dict(sorted(Counter(record["language_guess"] for record in records).items())),
        "duplicate_groups": len(duplicate_groups),
        "duplicate_files_beyond_first": sum(len(group["paths"]) - 1 for group in duplicate_groups),
        "duplicate_bytes_beyond_first": duplicate_bytes,
        "zero_byte_files": sum(record["bytes"] == 0 for record in records),
        "pdfs_without_text_sample": sum(
            record["extension"] == ".pdf" and record["sample_characters"] == 0 and record["bytes"] > 0
            for record in records
        ),
        "unreviewed_rights_files": len(records),
    }

    with (output / "corpus-manifest.jsonl").open("w", encoding="utf-8") as handle:
        for record in records:
            handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
    with (output / "corpus-manifest.csv").open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(records[0]))
        writer.writeheader()
        writer.writerows(records)
    with (output / "rights-review.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["path", "sha256", "corpus_role", "language_guess", "rights_policy", "notes"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            writer.writerow({key: record.get(key, "") for key in fields})
    with (output / "ingestion-blockers.csv").open("w", encoding="utf-8", newline="") as handle:
        fields = ["path", "issue", "recommended_action"]
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        for record in records:
            issues = []
            if record["bytes"] == 0:
                issues.append(("zero_byte_file", "restore or exclude"))
            elif record["extension"] == ".pdf" and record["sample_characters"] == 0:
                issues.append(("pdf_without_text_sample", "inspect; OCR if scanned, otherwise repair or exclude"))
            if record["extension"] == "[none]":
                issues.append(("unknown_extension", "identify file type manually"))
            if record["language_guess"] == "unknown":
                issues.append(("unknown_language", "review language manually"))
            for issue, action in issues:
                writer.writerow({"path": record["path"], "issue": issue, "recommended_action": action})
    write_json(output / "duplicate-groups.json", duplicate_groups)
    write_json(output / "audit-summary.json", summary)

    epub_files = [root / record["path"] for record in records if record["corpus_role"] == "bible"]
    if epub_files:
        epub_report = inspect_epub(epub_files[0])
        write_json(output / "bible-epub-structure.json", epub_report)
        write_epub_markdown(output / "bible-epub-structure.md", epub_report)
        summary["bible_epub"] = epub_report["counts"]
        write_json(output / "audit-summary.json", summary)
    return summary


def self_test():
    assert language_guess("books-en&chs.zip")[0] == "zh-Hans+en"
    assert language_guess("book (chs).pdf")[0] == "zh-Hans"
    assert language_guess("book (chs).pdf", ("中文内容" * 30) + ("English title " * 20))[0] == "zh-Hans"
    assert language_guess("conference-ch-mp3.zip")[0] == "zh-Hans"
    assert language_guess("book-en.pdf", "This is a sufficiently long English sample " * 5)[0] == "en"
    assert language_guess("unknown.pdf", "这是一个简体中文文本，说明这个文件里面有足够多的中文内容。" * 4)[0] == "zh-Hans"
    assert corpus_role(Path("恢复本圣经带注解.epub")) == "bible"
    print("self-test: ok")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--root", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, default=Path("reports/phase0"))
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        self_test()
        return
    summary = audit(args.root.resolve(), args.output.resolve())
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
