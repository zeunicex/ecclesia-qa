#!/usr/bin/env python3
"""Write the fixed, human-reviewable Phase 4 import priority manifest."""

from __future__ import annotations

import json
import re
from pathlib import Path


BATCH_A = "2017 2025 2029 2030 2031 2032 2033 2034&5 2036 2038 2039 2041 2047 2050 2051 2052 2054 2059 2062 2063 2067 2069 2070g 2082 2084 2091 2092 2144 2147 2148 2153 2154 2164 2166 2171 2174 2175 2176 2178 2179 2180 2181 2185 2188 2194 2195 2196 2198 2202 2203".split()
BATCH_B = "2205 2206 2208 2209 2210 2215 2216 2218 2220 2221 2222 2223 2224 2225 2238 2239 2240 2241 2242 2243 2244 2247 2252 2253 2254 2255 2256 2267 2274 2277 2281 2282 2283 2285 2287 2288 2289 2290 2294 2295 2296 2297 2300 2301 2304 2306 2307 2309 2311 2313".split()
FOUNDATIONAL = set("2040 2042 2073 2074 2075 2087 2152 2190 2199 2200 2318 2324 2325 2327 2328 2329 2330 2332 2336 2337 2338 2340 2343 2344 2347 2350 2352 2358 2363 2365 2366 2367 2368 2369 2370 2373 2374 2375 2376 2380 2382 2383 2388 2389 2393 2396 2397 2398 2399 2401 2402 2404 2405 2406 2407 2409".split())
LOW = set("2076 2156 2158 2159 2163 2167 2168 2169 2170 2192 2278 2279 2293 2293-1 2293-2 2321 2323 2335 2342 2353 2378".split())
ROOT_BATCH_C = {"shenjinglundefuyin.pdf", "恢复本新约圣经52题.pdf", "道路.pdf"}
ROOT_LOW = {"2020-DST-en&chs-hwmr.pdf", "2021-MDC-en&chs-hwmr.pdf", "2021-MDC-hwmr-chs.pdf", "LetterGraduatingSeniors.pdf"}


def title(path: Path) -> tuple[str, str]:
    match = re.match(r"\(([^)]+)\)", path.name)
    code = match.group(1) if match else path.stem
    value = re.sub(r"^\([^)]+\)", "", path.stem)
    value = re.sub(r"\s*\(chs\)$", "", value, flags=re.I)
    return code, value.split("-", 1)[0].strip()


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    existing = set()
    for jsonl in (root / "output/phase1/documents.jsonl", root / "output/phase3/documents.jsonl"):
        existing.update(json.loads(line)["source_path"] for line in jsonl.read_text(encoding="utf-8").splitlines())
    numbered = [path for path in root.glob("*xx-en&chs*/*.pdf") if not path.name.startswith("._") and str(path.relative_to(root)) not in existing]
    root_files = [root / name for name in ROOT_BATCH_C | ROOT_LOW if (root / name).exists()]
    rows = []
    for path in sorted(numbered + root_files):
        code, name = title(path)
        if code in BATCH_A:
            batch = "A"
        elif code in BATCH_B:
            batch = "B"
        elif code in FOUNDATIONAL or path.name in ROOT_BATCH_C:
            batch = "C"
        elif code in LOW or path.name in ROOT_LOW:
            batch = "E"
        else:
            batch = "D"
        rows.append({"batch": batch, "code": code, "title": name, "source_path": str(path.relative_to(root))})
    expected = set(BATCH_A + BATCH_B)
    found = {row["code"] for row in rows}
    assert expected <= found, sorted(expected - found)
    assert len(rows) == 304, len(rows)

    descriptions = {
        "A": "最高优先：覆盖最常见的基础真理、救恩、基督、那灵、生命、召会及初信问题。",
        "B": "高优先：补全神的经纶、神圣分赐、生机救恩、新耶路撒冷、国度与建造。",
        "C": "中高优先：重要专题及各卷圣经的深入补充。",
        "D": "中优先：实行、事奉、祷告、福音、生命长大及较窄专题。",
        "E": "最低优先：特定年份训练、特会、特定对象或重复性较高；先入 D1，容量足够才入 Pinecone。",
    }
    lines = ["# Phase 4 参考书导入优先级", "", "固定范围：剩余 304 本正式参考资料；不含诗歌、生命读经重复分卷、macOS `._` 文件和已导入书籍。", ""]
    for batch in "ABCDE":
        selected = [row for row in rows if row["batch"] == batch]
        lines += [f"## Batch {batch}（{len(selected)} 本）", "", descriptions[batch], ""]
        lines += [f"- {row['code']}《{row['title']}》" for row in selected]
        lines.append("")
    out = root / "output/phase3/PHASE4_PRIORITY.md"
    out.write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps({batch: sum(row["batch"] == batch for row in rows) for batch in "ABCDE"}, ensure_ascii=False))
    print(out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
