import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";

const base = process.env.ECCLESIA_BASE_URL || "https://ecclesia-qa.ecclesia-qa-2026.workers.dev";
const key = process.env.ACCESS_KEY;
assert.ok(key, "ACCESS_KEY is required");

const path = new URL("./eval/phase2b.jsonl", import.meta.url);
const cases = (await readFile(path, "utf8")).trim().split("\n").map(JSON.parse);
const limit = Number(process.argv.find(value => value.startsWith("--limit="))?.split("=")[1] || cases.length);

function check(test, body) {
  const failures = [];
  if (!test.expected_modes.includes(body.mode)) failures.push(`mode=${body.mode}`);
  if (body.answerable !== test.answerable) failures.push(`answerable=${body.answerable}`);
  const ids = new Set(body.evidence.map(item => item.source_id));
  const types = new Set(body.evidence.map(item => item.source_type));
  if (test.source_ids_any && !test.source_ids_any.some(id => ids.has(id))) failures.push("expected source id missing");
  for (const type of test.source_types_all || []) if (!types.has(type)) failures.push(`source type ${type} missing`);
  if (test.answer_includes_any && !test.answer_includes_any.some(text => body.answer_markdown?.includes(text))) failures.push("expected answer text missing");
  if (test.answer_concepts) {
    const matched = test.answer_concepts.filter(group => group.some(text => body.answer_markdown?.includes(text))).length;
    if (matched < (test.answer_concepts_min || test.answer_concepts.length)) failures.push(`answer concepts=${matched}`);
  }
  const citations = [...String(body.answer_markdown || "").matchAll(/\[S(\d+)\]/g)].map(match => +match[1]);
  if (citations.some(number => number < 1 || number > body.evidence.length)) failures.push("invalid citation id");
  if (body.generated && body.evidence.length > 1 && body.reranker_model !== "@cf/baai/bge-reranker-base") failures.push("reranker missing");
  return failures;
}

const results = [];
for (const test of cases.slice(0, limit)) {
  const response = await fetch(`${base}/api/query`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify({ question: test.question, locale: test.locale })
  });
  const body = await response.json();
  const failures = response.ok ? check(test, body) : [`http=${response.status}`, body.error || "unknown error"];
  results.push({ id: test.id, passed: failures.length === 0, failures, mode: body.mode, answerable: body.answerable, evidence: body.evidence?.length || 0, model: body.model });
  console.error(`${failures.length ? "FAIL" : "PASS"} ${test.id}${failures.length ? `: ${failures.join(", ")}` : ""}`);
}

const passed = results.filter(item => item.passed).length;
console.log(JSON.stringify({ base, passed, total: results.length, pass_rate: passed / results.length, results }, null, 2));
if (passed !== results.length) process.exitCode = 1;
