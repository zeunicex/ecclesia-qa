#!/usr/bin/env python3
"""Build a downgrade-safe Life-study and core-books import package."""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
from collections import Counter
from pathlib import Path

from phase1_build import (
    clean_pdf_page,
    extract_pdf_pages,
    make_page_chunks,
    normalized,
    paragraph_language,
    pdf_page_count,
    sha256,
    split_long_text,
)


CORPUS_VERSION = "phase4d-2026-08-13"
LIFE_STUDY = {
    "id": "book-life-study-bible",
    "path": "新旧约生命读经.pdf",
    "title": "新旧约生命读经",
    "title_en": "Life-study of the Bible",
}

# High-value books not already present in Phase 1. The order is the priority.
CORE_BOOK_PATHS = [
    "20xx-en&chs1/(2019)正常的基督徒生活-The Normal Christian Life (chs).pdf",
    "20xx-en&chs1/(2022-1)属灵人(上)-The Spiritual Man (1) (chs).pdf",
    "20xx-en&chs1/(2022-2)属灵人(中)-The Spiritual Man (2) (chs).pdf",
    "20xx-en&chs1/(2022-3)属灵人(下)-The Spiritual Man (3) (chs).pdf",
    "20xx-en&chs2/(2023)生命的认识-The Knowledge of Life (chs).pdf",
    "20xx-en&chs2/(2024)生命的经历-The Experience of Life (chs).pdf",
    "20xx-en&chs2/(2026-1)初信造就(上)-Messages for Building Up New Believers (1) (chs).pdf",
    "20xx-en&chs2/(2026-2)初信造就(中)-Messages for Building Up New Believers (2) (chs).pdf",
    "20xx-en&chs2/(2026-3)初信造就(下)-Messages for Building Up New Believers (3) (chs).pdf",
    "20xx-en&chs2/(2028)人的破碎与灵的出来-The Breaking of the Outer Man and the Release of the Spirit (chs).pdf",
    "20xx-en&chs3/(2043)基督是一切属灵的事物-Christ is All Spiritual Matters and Things (chs).pdf",
    "21xx-en&chs2/(2162)生命课程(卷一二三四)-Life Lessons (Vol. 1-2-3-4) (chs).pdf",
    "21xx-en&chs3/(2172)圣经中的基本启示-The Basic Revelation in the Holy Scriptures (chs).pdf",
    "21xx-en&chs4/(2197)神圣启示的中心路线—神的经纶与神的分赐-The Central Line of the Divine Revelation—The Divine Economy and the Divine Dispensing (chs).pdf",
    "22xx-en&chs1/(2213)国度(上下)-The Kingdom (chs).pdf",
    "22xx-en&chs1/(2219)生命信息(上下)-Life Messages (chs).pdf",
    "22xx-en&chs2/(2251)生命树-The Tree of Life (chs).pdf",
    "22xx-en&chs3/(2258)坐行站-Sit, Walk, Stand (chs).pdf",
    "22xx-en&chs3/(2262)约翰的修补职事-The Mending Ministry of John (chs).pdf",
    "22xx-en&chs4/(2298)一个新人-The One New Man (chs).pdf",
]

FOOTER_RE = re.compile(
    r"Life-Study of (?P<book>.+?)"
    r"(?:\s*-\s*Message\s*(?P<message>\d+)|\s*-\s*(?P<appendix>Appendix))?\s*-\s*"
    r"Page\s*(?P<message_page>\d+)\s*-\s*(?P<book_zh>.+?)生命[读讀][经經]\s*"
    r"(?P<section_zh>.*?)第\s*(?P<message_page_zh>[〇零一二三四五六七八九十百\d]+)\s*[页頁]",
    re.IGNORECASE,
)


def title_parts(path: str) -> tuple[str, str, str]:
    stem = Path(path).stem
    code = re.match(r"\(([^)]+)\)", stem)
    without_code = re.sub(r"^\([^)]+\)", "", stem)
    without_suffix = re.sub(r"\s*\(chs\)$", "", without_code, flags=re.IGNORECASE)
    chinese, _, english = without_suffix.partition("-")
    doc_id = "book-" + (code.group(1).lower() if code else hashlib.sha256(path.encode()).hexdigest()[:12])
    return doc_id, chinese.strip(), english.strip()


def record(document: dict, page: int, sequence: int, language: str, text: str, heading: str, page_label=None) -> dict:
    code = {"zh-Hans": "zh", "zh-Hant": "zht", "en": "en"}.get(language, "multi")
    source_id = f"doc:{document['id']}:pdf-{page:05d}:{code}-{sequence:03d}"
    return {
        "id": source_id,
        "text": text,
        "metadata": {
            "document_id": document["id"],
            "language": language,
            "source_type": "reference_book",
            "page_start": page,
            "page_end": page,
            "page_label": str(page_label) if page_label is not None else None,
            "book_id": None,
            "chapter": None,
            "verse_start": None,
            "verse_end": None,
            "note_no": None,
            "heading_path": heading,
            "checksum": hashlib.sha256(text.encode()).hexdigest(),
            "corpus_version": document["corpus_version"],
        },
    }


def extract_life_study_pages(path: Path) -> list[str]:
    """Read each PDF column as a block instead of interleaving its visual rows."""
    completed = subprocess.run(
        ["pdftotext", "-raw", "-enc", "UTF-8", str(path), "-"],
        check=True,
        capture_output=True,
    )
    return completed.stdout.decode("utf-8", errors="replace").split("\f")[:-1]


def language_blocks(text: str) -> list[tuple[str, str]]:
    """Join consecutive same-language lines emitted by pdftotext -raw."""
    result: list[tuple[str, str]] = []
    current_language = ""
    current_lines: list[str] = []
    pending: list[str] = []

    def flush() -> None:
        nonlocal current_language, current_lines, pending
        if current_language and current_lines:
            result.append((current_language, normalized("\n".join(current_lines + pending))))
        current_language, current_lines, pending = "", [], []

    for raw_line in text.replace("\r", "").splitlines():
        line = normalized(raw_line)
        if not line:
            continue
        language = paragraph_language(line)
        if language == "unknown":
            han = len(re.findall(r"[\u3400-\u9fff]", line))
            latin = len(re.findall(r"[A-Za-z]", line))
            if han and han >= latin:
                language = "zh-Hant"
            elif latin:
                language = "en"
        if language == "unknown":
            if current_language:
                pending.append(line)
            continue
        language = "zh-Hant" if language.startswith("zh") else language
        if language != current_language:
            flush()
            current_language = language
        if pending:
            current_lines.extend(pending)
            pending = []
        current_lines.append(line)
    flush()
    return [(language, block) for language, block in result if block]


def compact_chunks(text: str) -> list[tuple[str, str]]:
    """Keep multilingual-e5 inputs below its useful input window."""
    grouped: dict[str, list[str]] = {"zh-Hant": [], "en": []}
    for language, paragraph in language_blocks(text):
        grouped[language].append(paragraph)
    result: list[tuple[str, str]] = []
    for language, limit in (("zh-Hant", 650), ("en", 1500)):
        current: list[str] = []
        length = 0
        for paragraph in grouped.get(language, []):
            if len(paragraph) > limit:
                if current:
                    result.append((language, normalized("\n\n".join(current))))
                    current, length = [], 0
                result.extend((language, part) for part in split_long_text(paragraph, limit, 80))
            elif current and length + len(paragraph) + 2 > limit:
                result.append((language, normalized("\n\n".join(current))))
                current, length = [paragraph], len(paragraph)
            else:
                current.append(paragraph)
                length += len(paragraph) + (2 if length else 0)
        if current:
            result.append((language, normalized("\n\n".join(current))))
    return [(language, text) for language, text in result if len(text) >= 40]


def strongly_mixed(text: str) -> bool:
    """Detect interleaved bilingual columns, while allowing names and glosses."""
    han = len(re.findall(r"[\u3400-\u9fff]", text))
    latin = len(re.findall(r"[A-Za-z]", text))
    return han >= 20 and latin >= 100 and min(han, latin) / max(han, latin) >= 0.12


def message_title(text: str, message: int | None) -> tuple[str, str]:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    marker = next((i for i, line in enumerate(lines) if message and re.fullmatch(rf"Message\s*{message}", line, re.I)), -1)
    if marker < 0:
        return "", ""
    following = [line for line in lines[marker + 1:marker + 8] if not re.fullmatch(r"第.+篇", line)]
    english = next((line for line in following if re.search(r"[A-Za-z]", line)), "")
    chinese = next((line for line in following if re.search(r"[\u3400-\u9fff]", line)), "")
    return english, chinese


def life_study_rows(root: Path, document: dict):
    path = root / LIFE_STUDY["path"]
    pages = extract_life_study_pages(path)
    current_key = None
    current_titles = ("", "")
    for page_number, raw in enumerate(pages, start=1):
        footer = FOOTER_RE.search(raw)
        if not footer:
            # Nine source pages are blank or diagram-only and have no printed footer.
            if len(normalized(raw)) < 80 or page_number in {8067, 8068}:
                continue
            raise ValueError(f"Life-study footer not found on PDF page {page_number}")
        info = footer.groupdict()
        if info["message_page_zh"].isdigit() and info["message_page"] != info["message_page_zh"]:
            raise ValueError(f"Bilingual footer mismatch on PDF page {page_number}")
        message = int(info["message"]) if info["message"] else None
        section = f"Message {message}" if message else ("Appendix" if info["appendix"] else "Single Message")
        key = (info["book"].strip(), section)
        if key != current_key:
            if int(info["message_page"]) != 1:
                raise ValueError(f"Message begins after page 1 on PDF page {page_number}: {key}")
            current_key = key
            current_titles = message_title(raw, message)
        clean = normalized(FOOTER_RE.sub("", raw))
        heading_en = f"Life-study of {key[0]} > {section}"
        heading_zh = f"{info['book_zh'].strip()}生命读经 > " + (f"第{message}篇" if message else ("附录" if info["appendix"] else "单篇"))
        if current_titles[0]:
            heading_en += f" > {current_titles[0]}"
        if current_titles[1]:
            heading_zh += f" > {current_titles[1]}"
        counts: Counter[str] = Counter()
        for language, text in compact_chunks(clean):
            counts[language] += 1
            heading = heading_zh if language == "zh-Hant" else heading_en
            yield record(document, page_number, counts[language], language, text, heading, info["message_page"])


def ordinary_book_rows(root: Path, document: dict):
    path = root / document["source_path"]
    for page_number, raw in enumerate(extract_pdf_pages(path), start=1):
        clean = clean_pdf_page(raw)
        counts: Counter[str] = Counter()
        for language, text in make_page_chunks(clean, limit=1400):
            counts[language] += 1
            heading = document["title_en"] if language == "en" else document["title"]
            yield record(document, page_number, counts[language], language, text, heading)


def write_jsonl(path: Path, rows) -> int:
    count = 0
    with path.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            count += 1
    return count


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=root / "output/phase3")
    parser.add_argument("--life-only", action="store_true")
    parser.add_argument("--max-extra-chunks", type=int, default=20_000)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    life_path = root / LIFE_STUDY["path"]
    life_document = {
        **LIFE_STUDY,
        "language": "zh-Hant+en",
        "source_type": "bilingual_pdf",
        "source_path": LIFE_STUDY["path"],
        "checksum": sha256(life_path),
        "page_count": pdf_page_count(life_path),
        "rights_policy": "private_acceptance_only",
        "corpus_version": CORPUS_VERSION,
    }
    life_document.pop("path")
    documents = [life_document]
    chunks_path = args.out / "chunks.jsonl"
    language_counts: Counter[str] = Counter()
    document_counts: Counter[str] = Counter()
    total_bytes = 0
    total = 0
    with chunks_path.open("w", encoding="utf-8") as output:
        for row in life_study_rows(root, life_document):
            if strongly_mixed(row["text"]):
                raise ValueError(f"Interleaved Life-study languages in {row['id']}")
            output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
            language_counts[row["metadata"]["language"]] += 1
            document_counts[row["metadata"]["document_id"]] += 1
            total_bytes += len(row["text"].encode())
            total += 1

        if not args.life_only:
            remaining = args.max_extra_chunks
            for source_path in CORE_BOOK_PATHS:
                if remaining <= 0:
                    break
                path = root / source_path
                doc_id, title, title_en = title_parts(source_path)
                document = {
                    "id": doc_id,
                    "title": title,
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
                if len(rows) > remaining:
                    break
                documents.append(document)
                for row in rows:
                    output.write(json.dumps(row, ensure_ascii=False, sort_keys=True) + "\n")
                    language_counts[row["metadata"]["language"]] += 1
                    document_counts[row["metadata"]["document_id"]] += 1
                    total_bytes += len(row["text"].encode())
                    total += 1
                remaining -= len(rows)

    write_jsonl(args.out / "documents.jsonl", documents)
    # 10 KiB/record is deliberately conservative: 4 KiB float vector plus metadata/index overhead.
    current_records = 8_641 + 6_725 + 13_536
    estimated_storage = (current_records + total) * 10_240
    summary = {
        "corpus_version": CORPUS_VERSION,
        "documents": len(documents),
        "chunks": total,
        "life_study_chunks": document_counts[life_document["id"]],
        "extra_book_chunks": total - document_counts[life_document["id"]],
        "languages": dict(language_counts),
        "mixed_language_chunks": 0,
        "document_chunks": dict(document_counts),
        "text_bytes": total_bytes,
        "projected_total_records": current_records + total,
        "conservative_storage_bytes": estimated_storage,
        "conservative_storage_gib": round(estimated_storage / 2**30, 3),
        "starter_limit_gib": 2,
        "headroom_percent": round((1 - estimated_storage / 2**31) * 100, 1),
    }
    if estimated_storage >= 1.6 * 2**30:
        raise ValueError(f"Import package exceeds the 1.6 GiB safety ceiling: {summary}")
    (args.out / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
