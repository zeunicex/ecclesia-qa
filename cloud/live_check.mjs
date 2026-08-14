import assert from "node:assert/strict";

const base = "https://ecclesia-qa.ecclesia-qa-2026.workers.dev";
const key = process.env.ACCESS_KEY;
assert.ok(key, "ACCESS_KEY is required");

async function ask(question, locale) {
  const response = await fetch(`${base}/api/query`, {
    method: "POST",
    headers: { "content-type": "application/json", authorization: `Bearer ${key}` },
    body: JSON.stringify({ question, locale })
  });
  const body = await response.json();
  assert.equal(response.status, 200, JSON.stringify(body));
  assert.equal(body.locale, locale);
  assert.ok(Array.isArray(body.evidence));
  return {
    question,
    locale,
    mode: body.mode,
    generated: body.generated,
    evidence: body.evidence.length,
    answer: body.answer_markdown?.slice(0, 260),
    generation_error: body.generation_error
  };
}

const unauthorized = await fetch(`${base}/api/query`, { method: "POST" });
assert.equal(unauthorized.status, 401);

const checks = [];
checks.push(await ask("马太福音28:19", "zh-Hans"));
checks.push(await ask("什么是神圣三一？", "zh-Hans"));
checks.push(await ask("什麼是神聖三一？", "zh-Hant"));
checks.push(await ask("What is the Divine Trinity?", "en"));
checks.push(await ask("倪柝声弟兄什么时候离开上海的？", "zh-Hans"));
checks.push(await ask("圣经哪里讲到以弗所召会", "zh-Hans"));
checks.push(await ask("Where in the Bible is the church in Ephesus mentioned?", "en"));
checks.push(await ask("为什么只有一个新人", "zh-Hans"));

assert.equal(checks.at(-3).mode, "scripture_retrieval");
assert.match(checks.at(-3).answer, /启示录 2:1/);
assert.equal(checks.at(-2).mode, "scripture_retrieval");
assert.match(checks.at(-2).answer, /Revelation 2:1/);
assert.match(checks.at(-1).answer, /因为/);

console.log(JSON.stringify({ unauthorized: 401, checks }, null, 2));
