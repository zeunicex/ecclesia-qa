import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
import { centralThemeEvidence } from "./src/index.js";

const path = new URL("./eval/central_theme_evidence.jsonl", import.meta.url);
const cases = (await readFile(path, "utf8")).trim().split("\n").map(JSON.parse);
assert.equal(cases.length, 40, "central-theme gate requires 40 labeled cases");

function measure(classify) {
  let tp = 0, tn = 0, fp = 0, fn = 0;
  const failures = [];
  for (const test of cases) {
    const accepted = classify(test);
    if (accepted && test.expected_support) tp++;
    else if (!accepted && !test.expected_support) tn++;
    else if (accepted) { fp++; failures.push(test.id); }
    else { fn++; failures.push(test.id); }
  }
  const positives = tp + fn;
  const negatives = tn + fp;
  return {
    correct_answer_rate: tp / positives,
    correct_rejection_rate: tn / negatives,
    false_rejection_rate: fn / positives,
    support_precision: tp / (tp + fp),
    overall_accuracy: (tp + tn) / cases.length,
    failures
  };
}

const before = measure(() => true);
const after = measure(test => centralThemeEvidence([{ text: test.evidence }], test.question).length === 1);
const nonTheme = [{ text: "A" }, { text: "B" }];
assert.equal(centralThemeEvidence(nonTheme, "圣经讲什么？").length, nonTheme.length, "non-central-theme retrieval must be unchanged");
assert.ok(after.overall_accuracy > before.overall_accuracy, "candidate must improve overall accuracy");
assert.ok(after.correct_answer_rate >= 0.95, "direct-support recall must be at least 95%");
assert.ok(after.correct_rejection_rate >= 0.9, "correct rejection must be at least 90%");
assert.ok(after.false_rejection_rate <= 0.05, "false rejection must be at most 5%");
assert.ok(after.support_precision >= 0.9, "accepted evidence precision must be at least 90%");

console.log(JSON.stringify({ suite: "central_theme_evidence", cases: cases.length, before, after, non_theme_regressions: 0 }, null, 2));
