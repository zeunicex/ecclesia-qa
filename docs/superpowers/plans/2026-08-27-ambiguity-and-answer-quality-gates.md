# Ambiguity and Answer Quality Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Execute this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prevent ambiguous or weakly sourced questions from receiving confident, confusing answers, while preserving the Bible → footnote → highly relevant reference-book retrieval order.

**Architecture:** Add a deterministic clarification gate before retrieval for genuinely ambiguous one-word theological subjects. Add evidence and answer-quality gates after synthesis so doctrinal and experiential answers cannot be marked supported from reference books alone or from malformed/off-target text. Add a source-id-only coverage card for “drinking the water of life” so the existing D1 corpus supplies exact Bible and footnote text before reference-book supplementation.

**Tech Stack:** Cloudflare Workers JavaScript, Workers AI, D1, Pinecone, Node.js assertion tests, Wrangler 4.

**Spec:** User feedback and screenshots in the current Codex task dated 2026-08-27.

## Global Constraints

- Preserve the retrieval order: Bible verses first, footnotes second, and only then highly relevant reference books.
- Do not claim “evidence supported” when the evidence does not answer the exact question.
- Keep source numbering contiguous from S1 after filtering and presentation.
- Avoid additional serial retrieval latency; independent searches remain concurrent.
- Do not hardcode new private corpus excerpts in source code; coverage anchors reference D1 source IDs only.

---

### Task 1: Clarify ambiguous “spirit” questions

**Files:**
- Modify: `cloud/src/index.js`
- Test: `cloud/test_worker.mjs`

**Interfaces:**
- Produces: `clarificationResult(question, locale): object | null`
- Consumes: `normalizeLocale`, `questionSubject`

- [x] **Step 1: Write failing tests**

```js
const ambiguousSpirit = await answerQuery({}, "灵是什么", "zh-Hans", {}, false);
assert.equal(ambiguousSpirit.answerable, false);
assert.equal(ambiguousSpirit.answerability_reason, "clarification_required");
assert.match(ambiguousSpirit.answer_markdown, /圣灵/);
assert.match(ambiguousSpirit.answer_markdown, /人的灵/);
assert.deepEqual(ambiguousSpirit.evidence, []);
```

- [x] **Step 2: Run the test and confirm it fails**

Run: `pnpm test`

- [x] **Step 3: Implement the clarification gate**

```js
function clarificationResult(question, locale) {
  const compact = toSimplified(String(question || "")).replace(/[\s？?。.!！]/g, "");
  if (!/^(?:灵是什么|什么是灵|灵指什么)$/.test(compact)) return null;
  const answer = locale === "zh-Hant"
    ? "你所問的「靈」可能指聖靈，也可能指人的靈。請說明你要問哪一個，我再按聖經、註腳和參考資料回答。"
    : "你所问的“灵”可能指圣灵，也可能指人的灵。请说明你要问哪一个，我再按圣经、脚注和参考资料回答。";
  return { mode: "clarification", evidence: [], answer_markdown: answer, answerable: false, answerability_reason: "clarification_required", generated: false, presentation: "study" };
}
```

- [x] **Step 4: Run the tests and confirm they pass**

Run: `pnpm test`

### Task 2: Enforce primary-source and answer-quality gates

**Files:**
- Modify: `cloud/src/index.js`
- Test: `cloud/test_worker.mjs`

**Interfaces:**
- Produces: `requiresPrimaryScripture(question): boolean`
- Produces: `answerQualityFailure(answer, question, evidence): string | null`
- Consumes: `questionIntent`, `questionSubject`, `sentenceParts`

- [x] **Step 1: Write failing tests for reference-only sufficiency and malformed Chinese**

```js
assert.equal(requiresPrimaryScripture("如何喝生命活水"), true);
assert.equal(requiresPrimaryScripture("倪柝声什么时候离开上海"), false);
assert.equal(answerQualityFailure("幸一些就要流水。对于一些小年人来说。", "如何喝生命活水", []), "malformed_answer");
```

- [x] **Step 2: Run the test and confirm it fails**

Run: `pnpm test`

- [x] **Step 3: Implement deterministic gates**

```js
function requiresPrimaryScripture(question) {
  const type = questionIntent(question).type;
  if (["time", "place", "person"].includes(type) && !directReference(question)) return false;
  return ["definition", "explanation", "significance", "cause", "purpose", "means", "comparison", "evidence"].includes(type);
}
```

After synthesis, reject a supported result when a primary-source-required question cites no Bible verse or footnote. Reject empty, citation-only, malformed, or HOW answers with no source-supported concrete means. Preserve the filtered evidence as review material but use `answerable: false` and a precise reason.

- [x] **Step 4: Strengthen the generation contract**

Add explicit requirements that Chinese output be grammatical, that HOW points describe an action actually stated in evidence, and that the model return unanswerable rather than repairing broken source fragments with invented wording.

- [x] **Step 5: Run the tests and confirm they pass**

Run: `pnpm test`

### Task 3: Add primary-source coverage for drinking living water

**Files:**
- Modify: `cloud/src/index.js`
- Test: `cloud/test_worker.mjs`

**Interfaces:**
- Extends: `DOCTRINE_CARDS`
- Consumes: `doctrineAnchorEvidence`, `composedAnswerResult`

- [x] **Step 1: Inspect exact D1 source IDs and texts**

Run read-only D1 queries for John 4:14, John 7:37-39, and Revelation 22:17 plus their footnotes. Use only rows that explicitly connect drinking/coming/taking to the water of life.

- [x] **Step 2: Write a failing end-to-end regression test**

The test must assert that “如何喝生命活水” returns a grammatical conclusion, cites at least one Bible verse, includes any available direct footnote before reference books, and never marks a reference-only answer as supported.

- [x] **Step 3: Add a source-id-only coverage card**

```js
{
  id: "drink_living_water",
  match: /(?:如何|怎么|怎样).*(?:喝|饮).*(?:生命水|生命活水)|how.*drink.*(?:living water|water of life)/i,
  aspects: [
    { id: "come_and_drink", description: "Locate the direct invitation to come, drink, or take the water of life." },
    { id: "believe_and_receive", description: "Locate the source's explicit connection between believing, receiving the Spirit, and living water." }
  ],
  anchors: [
    { source_id: "verse:rcv-zh-cn:John.7.37", language: "zh-Hans", aspects: ["come_and_drink"] },
    { source_id: "verse:rcv-zh-cn:John.7.38", language: "zh-Hans", aspects: ["believe_and_receive"] },
    { source_id: "verse:rcv-zh-cn:John.7.39", language: "zh-Hans", aspects: ["believe_and_receive"] },
    { source_id: "verse:rcv-zh-cn:Rev.22.17", language: "zh-Hans", aspects: ["come_and_drink"] },
    { source_id: "footnote:rcv-zh-cn:John.7.39.1", language: "zh-Hans", aspects: ["believe_and_receive"] }
  ]
}
```

- [x] **Step 4: Run the full test suite**

Run: `pnpm test`

### Task 4: Validate and deploy

**Files:**
- Modify: `docs/superpowers/plans/2026-08-27-ambiguity-and-answer-quality-gates.md`

**Interfaces:**
- Consumes: completed Worker changes and tests

- [x] **Step 1: Validate the Worker bundle**

Run: `pnpm dlx wrangler@4.126.0 deploy --config wrangler.jsonc --dry-run --keep-vars`

- [x] **Step 2: Deploy**

Run: `pnpm dlx wrangler@4.126.0 deploy --config wrangler.jsonc --keep-vars`

- [x] **Step 3: Verify production health and the two regression questions**

Check `/health`, then query “灵是什么” and “如何喝生命活水” against production with the private access key supplied locally by the existing environment.

- [x] **Step 4: Mark the plan complete and commit**

Run: `git add cloud/src/index.js cloud/test_worker.mjs docs/superpowers/plans/2026-08-27-ambiguity-and-answer-quality-gates.md`

Run: `git commit -m "fix: clarify ambiguous questions and enforce source quality"`
