#!/usr/bin/env python3
"""Idempotently import selected corpus chunks into Pinecone integrated inference."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


API_VERSION = "2026-04"
CONTROL_VERSION = "2025-10"


def request(url: str, api_key: str, *, method: str = "GET", body: bytes | None = None, content_type: str = "application/json") -> dict:
    headers = {"Api-Key": api_key, "X-Pinecone-Api-Version": API_VERSION if ".svc." in url else CONTROL_VERSION}
    if body is not None:
        headers["Content-Type"] = content_type
    for attempt in range(6):
        try:
            with urllib.request.urlopen(urllib.request.Request(url, data=body, headers=headers, method=method), timeout=90) as response:
                payload = response.read()
                return json.loads(payload) if payload else {}
        except urllib.error.HTTPError as error:
            detail = error.read().decode("utf-8", errors="replace")
            if error.code not in {429, 500, 502, 503, 504} or attempt == 5:
                raise RuntimeError(f"Pinecone {error.code}: {detail}") from error
        except urllib.error.URLError:
            if attempt == 5:
                raise
        time.sleep(min(2 ** attempt, 16))
    raise AssertionError("unreachable")


def ensure_index(api_key: str, name: str) -> dict:
    url = f"https://api.pinecone.io/indexes/{urllib.parse.quote(name)}"
    try:
        index = request(url, api_key)
    except RuntimeError as error:
        if "Pinecone 404" not in str(error):
            raise
        payload = json.dumps({
            "name": name,
            "cloud": "aws",
            "region": "us-east-1",
            "deletion_protection": "enabled",
            "embed": {
                "model": "multilingual-e5-large",
                "metric": "cosine",
                "field_map": {"text": "chunk_text"},
                "write_parameters": {"input_type": "passage", "truncate": "END"},
                "read_parameters": {"input_type": "query", "truncate": "END"},
            },
        }).encode()
        request("https://api.pinecone.io/indexes/create-for-model", api_key, method="POST", body=payload)
        index = {}
    for _ in range(36):
        index = request(url, api_key)
        if index.get("status", {}).get("ready") and index.get("host"):
            return index
        time.sleep(5)
    raise TimeoutError(f"Index {name} was not ready after 3 minutes")


def load_documents(path: Path) -> dict[str, dict]:
    with path.open(encoding="utf-8") as handle:
        return {row["id"]: row for row in map(json.loads, handle)}


def selected_records(chunks: Path, documents: dict[str, dict], source_types: set[str]):
    with chunks.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            row = json.loads(line)
            metadata = row["metadata"]
            if metadata["source_type"] not in source_types:
                continue
            document = documents[metadata["document_id"]]
            record = {
                "_id": row["id"],
                "chunk_text": row["text"],
                "document_id": metadata["document_id"],
                "title": document["title"],
                "title_en": document.get("title_en") or "",
                "language": metadata["language"],
                "source_type": metadata["source_type"],
                "corpus_version": metadata["corpus_version"],
                "checksum": metadata["checksum"],
            }
            for field in ("page_start", "page_end", "book_id", "chapter", "verse_start", "verse_end", "note_no", "heading_path"):
                if metadata.get(field) is not None:
                    record[field] = metadata[field]
            yield line_number, record


def fingerprint(path: Path, source_types: set[str]) -> str:
    stat = path.stat()
    return hashlib.sha256(f"{path.resolve()}:{stat.st_size}:{stat.st_mtime_ns}:{sorted(source_types)}".encode()).hexdigest()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--chunks", type=Path, default=root / "output/phase1/chunks.jsonl")
    parser.add_argument("--documents", type=Path, default=root / "output/phase1/documents.jsonl")
    parser.add_argument("--state", type=Path, default=root / "output/cloud/pinecone-progress.json")
    parser.add_argument("--index", default="ecclesia-phase1")
    parser.add_argument("--namespace", default="phase1")
    parser.add_argument("--source-type", action="append")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--api-key-file", type=Path, help=argparse.SUPPRESS)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--reset", action="store_true")
    args = parser.parse_args()
    source_types = set(args.source_type or ["reference_book"])
    docs = load_documents(args.documents)
    signature = fingerprint(args.chunks, source_types)
    state = {"fingerprint": signature, "last_line": 0, "upserted": 0}
    if args.state.exists() and not args.reset:
        loaded = json.loads(args.state.read_text(encoding="utf-8"))
        if loaded.get("fingerprint") == signature:
            state = loaded
    records = ((line, record) for line, record in selected_records(args.chunks, docs, source_types) if line > state["last_line"])
    if args.limit:
        import itertools
        records = itertools.islice(records, args.limit)
    if args.dry_run:
        sample = []
        for line, record in records:
            sample.append({"line": line, "id": record["_id"], "bytes": len(json.dumps(record, ensure_ascii=False).encode())})
            if len(sample) == 3:
                break
        print(json.dumps({"source_types": sorted(source_types), "sample": sample}, ensure_ascii=False, indent=2))
        return 0

    api_key = os.environ.get("PINECONE_API_KEY") or (args.api_key_file.read_text().strip() if args.api_key_file else "")
    if not api_key:
        raise SystemExit("PINECONE_API_KEY is required")
    index = ensure_index(api_key, args.index)
    host = index["host"]
    url = f"https://{host}/records/namespaces/{urllib.parse.quote(args.namespace)}/upsert"
    batch: list[tuple[int, dict]] = []
    for line, record in records:
        batch.append((line, record))
        if len(batch) < 96:
            continue
        body = ("\n".join(json.dumps(item, ensure_ascii=False) for _, item in batch) + "\n").encode()
        request(url, api_key, method="POST", body=body, content_type="application/x-ndjson")
        state.update(last_line=batch[-1][0], upserted=state["upserted"] + len(batch), host=host, index=args.index, namespace=args.namespace)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
        if state["upserted"] % 960 == 0:
            print(f"upserted={state['upserted']} last_line={state['last_line']}", flush=True)
        batch = []
    if batch:
        body = ("\n".join(json.dumps(item, ensure_ascii=False) for _, item in batch) + "\n").encode()
        request(url, api_key, method="POST", body=body, content_type="application/x-ndjson")
        state.update(last_line=batch[-1][0], upserted=state["upserted"] + len(batch), host=host, index=args.index, namespace=args.namespace)
        args.state.parent.mkdir(parents=True, exist_ok=True)
        args.state.write_text(json.dumps(state, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(state, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
