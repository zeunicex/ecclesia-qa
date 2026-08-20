# Ecclesia Phase 4E cloud runtime

Current deployment:

- Cloudflare D1 `ecclesia-phase1` (`e3566bab-a3ee-4df2-aaf7-dc5f5db8c6f2`), APAC/Singapore
- Pinecone index `ecclesia-phase1`, namespace `phase1`, integrated `multilingual-e5-large`
- Pinecone Bible namespace `phase2-bible` for multilingual Scripture-location questions
- Pinecone footnote namespace `phase2-footnotes` for semantic Recovery Version footnote retrieval
- Workers AI `@cf/baai/bge-reranker-base` to rerank up to 16 excerpted candidates before generation
- Workers AI `@cf/meta/llama-3.1-8b-instruct-fp8-fast` for lower-cost straightforward questions
- Workers AI `@cf/meta/llama-3.3-70b-instruct-fp8-fast` for why, importance, comparison, and historical questions, plus fallback when the 8B result is unusable
- Workers AI `@cf/meta/m2m100-1.2b` for English ↔ Chinese Scripture-search and answer translation
- Protected Cloudflare Worker `ecclesia-qa`: <https://ecclesia-qa.ecclesia-qa-2026.workers.dev>

Validated remote counts after the 1.8 GiB priority prefix import:

- 216 documents
- 62,320 Bible rows: 31,102 English verses plus 31,218 Chinese rows, including 116 Psalm superscriptions
- 30,676 footnotes in D1 and Pinecone: 15,793 Chinese and 14,883 English
- 144,317 Pinecone reference-book records, including the corrected complete Life-study corpus, Batches A and B, all of Batch C, and the first 24 Batch D books
- 188,423 Pinecone records across all three namespaces; D1 `search_chunks` contains 188,427 rows

Phase 3 local import package:

- Complete bilingual *Life-study of the Bible*: 56,259 records
- 20 additional core ministry books: 16,193 records
- Projected total across Pinecone namespaces: 101,354 records
- Conservative projected storage: 0.967 GiB, leaving about 51.7% below the 2 GiB Starter downgrade limit

Phase 4B deployed counts:

- Pinecone `phase1`: 107,072 records
- Pinecone `phase2-bible`: 13,430 records (6,725 Chinese and 6,705 English chunks)
- Pinecone `phase2-footnotes`: 30,676 records (15,793 Chinese and 14,883 English Recovery Version footnotes)
- Pinecone all namespaces: 151,178 records
- D1 keyword index: 177,537 records, including Batch A's 50 books / 25,979 chunks, 6,705 English Bible chunks, and 14,883 English footnote chunks
- D1 database size after import: 755.03 MB

Phase 4C English footnote update:

- 14,883 English Recovery Version footnotes parsed from the supplied EPUB with 0 empty records; this includes single-chapter-book numbering and Psalm superscription notes
- D1 footnotes and keyword search now contain both English and Chinese sets
- D1 database size after deduplicated import: 824.70 MB
- English exact footnote queries select only English rows; Chinese queries select only Chinese rows
- English Pinecone import completed in `phase2-footnotes`; the local rebuild package is in `output/rcv-english-footnotes`

Phase 4D Life-study source repair:

- The bilingual PDF is extracted with `pdftotext -raw`, keeping the English and Traditional Chinese columns separate before chunking
- The rebuilt Life-study corpus contains 52,287 records: 27,120 English and 25,167 Traditional Chinese
- Full-corpus validation found 0 strongly mixed-language chunks, compared with 939 in the previous package
- D1 contains exactly 52,287 Life-study rows, and the known page-364 mixed ID now has one coherent Traditional Chinese row
- Pinecone removed 4,416 obsolete IDs and upserted all 52,287 corrected records; `phase1` now contains 103,100 records
- Across all three Pinecone namespaces there are 147,206 records; D1 `search_chunks` also contains 147,206 rows
- The local rebuild package and resumable migration state are in `output/phase4d-life-study` and `output/cloud/pinecone-phase4d-life-study-progress.json`

Priority Batch B expansion:

- The next 50 books were selected in the fixed order from `scripts/priority_manifest.py`; no lower-priority book skipped a higher-priority book
- The build produced 17,801 unique chunks: 5,425 Simplified Chinese, 12,374 English, and 2 bilingual metadata/title chunks; no document was deferred by the 1.6 GiB conservative safety ceiling
- D1 contains all 50 Batch B documents and 17,801 new search chunks; the remote database now has 133 documents, 165,011 search rows, and a reported size of 1,172.40 MB
- Pinecone `phase1` increased from 103,100 to 120,901 records; `describe_index_stats` reports 165,007 records across all namespaces, with the Bible and footnote namespaces unchanged
- The conservative projected Pinecone footprint is 1.574 GiB, leaving about 0.426 GiB below the 2 GiB planning ceiling; Pinecone reports vector counts but not actual byte usage for this serverless index
- The local package, D1 export, resumable state, and verified stats are in `output/phase4-batch-b`, `output/cloud/d1-phase4-b.sql`, `output/cloud/pinecone-phase4-b-progress.json`, and `output/cloud/pinecone-phase4-b-stats.json`

Remaining hierarchy import under the 1.8 GiB ceiling:

- Selection followed the reviewed C → D → E hierarchy as a strict prefix: all 59 Batch C books, followed by the first 24 Batch D books; no smaller lower-priority book skipped a higher-priority book
- The selected 83 books produced 23,416 unique chunks: 7,058 Simplified Chinese, 16,357 English, and 1 bilingual metadata/title chunk
- The last selected source is `book-2080`, *The Messenger of the Cross* (`《十字架的使者》`); the first deferred source is `book-2081`, *The Knowledge That Should Be in the Lord's Recovery* (`《主恢复中应有的认识》`)
- The selected prefix brings Pinecone to 188,423 records, a conservative 1.797 GiB estimate. Adding `book-2081`'s 643 chunks would reach 189,066 records or 1.803074 GiB, so it and all later books remain deferred
- D1 contains all 83 new documents and 23,416 new search chunks; the remote database now has 216 documents, 188,427 search rows, and a reported size of 1,298,726,912 bytes
- Pinecone `phase1` now contains 144,317 records; `phase2-bible` remains at 13,430 and `phase2-footnotes` at 30,676, for 188,423 total records
- The local package, split D1 import, resumable Pinecone state, and verified stats are in `output/phase4-remaining`, `output/cloud/d1-phase4-remaining-parts`, `output/cloud/pinecone-phase4-remaining-progress.json`, and `output/cloud/pinecone-phase4-remaining-stats.json`

Phase 4E dual question modes:

- **Reference search** preserves the original stateless question-and-evidence workflow
- **Conversation** keeps at most eight recent user/assistant messages in that browser's `localStorage`; no conversation history is written to D1
- Clear standalone questions use the existing retrieval path without another model call
- Context-dependent follow-ups are rewritten once with the 8B Workers AI model into a self-contained retrieval question, then pass through the same D1/Pinecone retrieval, reranker, answerability, and citation pipeline
- Each stored user turn now keeps the server's self-contained `resolved_question`, so a chain of pronouns no longer drifts back to the last elliptical wording. A phrase such as “this capacity” is anchored to the most recent exact use of “capacity,” while prior assistant text is used only to resolve the reference and never treated as evidence.
- A deterministic question-intent contract classifies definition, object, cause, purpose, means, significance, comparison, correction/verification, supporting-evidence, person, time, place, and Scripture-location questions. Follow-up rewriting, reranking, generation, and output validation share this contract, so topically related evidence cannot answer the wrong semantic role. A rewritten follow-up is rejected if it changes the original answer type.
- Multi-part follow-ups preserve explicit facets such as location, universality, conditions, personal possession, and evidential basis through rewriting, retrieval, reranking, and generation. Complex multi-facet questions use the quality model, while simple turns stay on the fast model.
- Every question also passes through one shared subject extractor. The extracted subject drives reference-book and footnote retrieval, evidence excerpts, lexical and model reranking, generation, and a required `subject_supported` answerability check. This is the default path for all topics; reviewed topic cards remain only as high-value acceptance fixtures that require several named aspects.
- Generated API responses expose `question_subject` beside `question_intent`, making subject-routing errors visible in testing and search analytics without another model call.
- Follow-up rewriting preserves grammatical focus and correction, so questions such as “what is dispensed?” are not changed into “what is dispensing?” or “why dispense?”, and “isn't it X?” must evaluate X against the preceding subject instead of echoing it.
- Conversation answers use one natural paragraph with at most two directly responsive claims instead of a numbered outline; reference-search formatting is unchanged
- Pinecone rate limits, 5xx responses, network failures, and malformed responses fall back to D1; if all retrieval paths fail temporarily, the conversation receives a localized retry message instead of a generic 502
- Every conversational answer retains collapsible Bible, footnote, and reference-book evidence cards; **New conversation** clears the local context
- The API remains backward-compatible: requests without `mode: "chat"` use reference search

## Rebuild

```bash
python3 cloud/export_d1.py
npx --yes wrangler@latest d1 execute ecclesia-phase1 --remote --file=cloud/schema.sql --config=cloud/wrangler.jsonc
npx --yes wrangler@latest d1 execute ecclesia-phase1 --remote --file=output/cloud/d1-data.sql --config=cloud/wrangler.jsonc
PINECONE_API_KEY=... python3 cloud/pinecone_import.py
PINECONE_API_KEY=... python3 cloud/pinecone_import.py --namespace phase2-bible --state output/cloud/pinecone-bible-progress.json --source-type bible
PINECONE_API_KEY=... python3 cloud/pinecone_import.py --namespace phase2-footnotes --state output/cloud/pinecone-footnotes-progress.json --source-type footnote
python3 scripts/parse_rcv_english_epub.py --epub /path/to/recovery-version.epub
npx --yes wrangler@latest d1 execute ecclesia-phase1 --remote --file=output/rcv-english-footnotes/d1-english-footnotes.sql --config=cloud/wrangler.jsonc
PINECONE_API_KEY=... python3 cloud/pinecone_import.py --chunks output/rcv-english-footnotes/chunks.jsonl --documents output/rcv-english-footnotes/documents.jsonl --namespace phase2-footnotes --state output/cloud/pinecone-footnotes-en-progress.json --source-type footnote
python3 cloud/export_phase3_d1.py
node cloud/export_phase3_mirror.mjs
npx --yes wrangler@latest d1 execute ecclesia-phase1 --remote --file=output/cloud/d1-phase3.sql --config=cloud/wrangler.jsonc
npx --yes wrangler@latest d1 execute ecclesia-phase1 --remote --file=output/cloud/d1-phase3-zh-hans.sql --config=cloud/wrangler.jsonc
PINECONE_API_KEY=... python3 cloud/pinecone_import.py --chunks output/phase3/chunks.jsonl --documents output/phase3/documents.jsonl --namespace phase1 --state output/cloud/pinecone-phase3-progress.json --source-type reference_book
python3 scripts/phase3_build.py --life-only --out output/phase4d-life-study
python3 cloud/export_phase3_d1.py --chunks output/phase4d-life-study/chunks.jsonl --documents output/phase4d-life-study/documents.jsonl --out output/cloud/d1-phase4d-life-study.sql
python3 scripts/phase4_build.py --batch B
python3 cloud/export_phase3_d1.py --chunks output/phase4-batch-b/chunks.jsonl --documents output/phase4-batch-b/documents.jsonl --out output/cloud/d1-phase4-b.sql
./cloud/import_batch_b.command
python3 scripts/phase4_build.py --batch remaining --current-records 165007 --ceiling-gib 1.8 --out output/phase4-remaining
python3 cloud/export_phase3_d1.py --chunks output/phase4-remaining/chunks.jsonl --documents output/phase4-remaining/documents.jsonl --out output/cloud/d1-phase4-remaining.sql
./cloud/import_batch_b.command --remaining
```

Secrets are not stored in this repository. `PINECONE_API_KEY` is already configured as an encrypted Worker secret.

## Private test UI

The UI and `/api/query` are live. The API requires the `ACCESS_KEY` Worker secret; `/health` is intentionally public. To rotate the private UI password:

```bash
npx --yes wrangler@latest secret put ACCESS_KEY --config=cloud/wrangler.jsonc
```

The private search dashboard is available at `/admin` and uses a separate `ADMIN_KEY` Worker secret. It records authenticated questions, anonymous browser IDs, locale, retrieval mode, answerability, latency, and cited source IDs in the separate `ecclesia-analytics` D1 database for 90 days. It never records either access key or full IP addresses.

```bash
npx --yes wrangler@latest secret put ADMIN_KEY --config=cloud/wrangler.jsonc
```

On the project Mac, `open_admin.command` retrieves the admin key from macOS Keychain, copies it to the clipboard, and opens `/admin`; the key itself is never stored in the repository.

The API returns `answerable`, `answerability_reason`, `answer_markdown`, and numbered evidence cards (`S1`, `S2`, …). Direct Scripture and reviewed-topic lookups are deterministic. Semantic queries retrieve a wider candidate set, extract question-relevant passages from long chunks, use the dedicated reranker, and then ask the generation model to abstain unless the exact requested fact is explicitly supported. JSON Schema requires every generated point to carry its own directly supporting source IDs. Importance questions request distinct supported reasons instead of one generic paragraph.

Each query response includes a `Server-Timing` header with exact lookup, retrieval, reranking, generation, and presentation/translation durations. This makes latency regressions visible without adding a paid monitoring service.

Supported answer locales are Simplified Chinese (`zh-Hans`), Traditional Chinese (`zh-Hant`), and English (`en`).
Traditional Chinese answers pass through the pure-JavaScript OpenCC `cn` → `tw` converter so script consistency does not depend on model behavior.
English exact verse lookups use the imported English Recovery Version text. English exact footnote lookups now use and display the imported English note text; a Chinese-only fallback is still labeled as a Chinese Recovery Version footnote and is never displayed as though it were an English source.

The retrieval runtime keeps Scripture, footnote, and reference-book paths distinct. Doctrine questions can combine reviewed Bible-topic verses, semantic footnotes, and ministry-book passages before reranking. Footnote questions with an explicit verse use D1; conceptual footnote questions use `phase2-footnotes`.

Core doctrine coverage cards distinguish relevance from indispensability. A matched card pins reviewed anchor passages before reranking and requires one cited point per essential aspect. When reviewed bilingual extracts are available, the answer uses those source sentences directly instead of asking a model to paraphrase them; model synthesis remains only as a fallback. Deployed cards cover the Divine Trinity's oneness and the practical way for Christ to make His home in the believers' hearts. General HOW questions retrieve a wider pool, prioritize actionable source language, and explicitly reject definition-only answers. Regression cases are included in `eval/phase2b.jsonl`.

Pinecone HTTP 429 responses degrade to a localized `semantic_temporarily_unavailable` result instead of a generic 502. Exact D1 verse and footnote lookups remain available. Evidence cards label Bible, footnote, and reference-book sources and show verse/note locations or book titles with physical PDF pages.

## Checks

```bash
cd cloud
npm test
npm run eval:central-theme
ACCESS_KEY=... npm run eval
```

On the project Mac, the access key can be kept in macOS Keychain instead of shell history or repository files:

```bash
./run_full_eval.command
```

If the key is not already present, `run_full_eval.command` prompts for it without placing it in the command line, saves it in macOS Keychain, runs the focused gate, unit checks, and authenticated end-to-end suite, and writes non-secret production and Preview JSON results to `output/eval/phase2b-baseline.json` and `output/eval/phase2b-preview.json`. The key is read into the process environment only for the duration of the evaluation and is never printed or written.

`eval/phase2b.jsonl` contains 32 adjudicated cases across Simplified Chinese, Traditional Chinese, and English, including exact lookups, English Recovery Version footnotes, Scripture location, doctrine, semantic footnotes, unsupported history, false premises, missing references, multi-point answer coverage, multilingual central-theme answers, forbidden citations/claims, and central-theme abstention.

### Quality-change gate

Every new retrieval, intent, evidence, answerability, or generation rule must be treated as an error-class change rather than a one-question patch:

1. Add a labeled batch containing positive forms, multilingual/paraphrased forms, related-but-insufficient evidence, and cases that must abstain.
2. Record the previous behavior before changing the rule.
3. Run the focused batch, `npm test`, and the full authenticated `npm run eval` suite.
4. Compare correct-answer recall, correct rejection, false rejection, citation/support precision, and unrelated regressions.
5. Do not commit or deploy unless the focused suite improves overall, its declared thresholds pass, and the full suite has no new regression.

`eval/central_theme_evidence.jsonl` is the first focused gate: 40 adjudicated Simplified Chinese, Traditional Chinese, and English evidence relationships. `npm run eval:central-theme` compares the pre-gate baseline with the candidate rule and fails unless direct-support recall is at least 95%, correct rejection and support precision are at least 90%, false rejection is at most 5%, overall accuracy improves, and non-central-theme retrieval remains unchanged. This focused test validates evidence eligibility only; it does not replace the authenticated end-to-end suite.

The 2026-08-20 non-production Preview acceptance passed the focused gate at 40/40 and the four targeted multilingual central-theme cases at 4/4. The full authenticated suite improved from 24/32 on the production baseline to 28/32 on Preview, with no new failing case in the final comparison. The Preview version was not promoted to production traffic.

Do not remove the access-key requirement or publicly expose excerpts until the rights policy is reviewed.
