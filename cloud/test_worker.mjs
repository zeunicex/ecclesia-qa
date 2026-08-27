import assert from "node:assert/strict";
import { ADMIN_HTML, HTML, UI_TEXT, answerFocusInstruction, answerQuery, applyReranker, centralThemeEvidence, conversationDependent, conversationalAnswer, crossLanguageQueries, d1KeywordEvidence, deterministicAnswer, directQuestionNeedsSemanticSearch, directReference, doctrineAnchorEvidence, doctrineCoverage, doctrineExtractiveAnswer, englishScriptureSubject, englishWholeWordMatch, evidenceExcerpt, exactLookup, fallbackConversationQuestion, footnotesForReference, howIntent, importanceIntent, keywordQuery, lexicalRerank, localizeAnswer, localizeGeneratedAnswer, modelForQuestion, normalizeHistory, normalizeLocale, normalizeQueryText, normalizeSourceText, orderEvidenceLayers, parseNumber, pineconeFailure, precisePassage, prepareReferenceEvidence, presentationEvidence, questionFacets, questionIntent, questionSubject, requestedNote, rerankEvidence, resolveConversationQuestion, retrievalFailureResult, retrievalQuestion, scriptureContextEvidence, scriptureInterpretationIntent, scriptureLocationIntent, scriptureQuoteIntent, scriptureQuoteText, scriptureSearchQuery, sourceQuality, structuredAnswer, structuredResult, temporarySemanticResult, validVisitorId, validateAnswer, whyIntent, writeQueryLog } from "./src/index.js";

assert.equal(normalizeLocale("zh-Hant"), "zh-Hant");
assert.equal(normalizeLocale("unknown"), "zh-Hans");
assert.equal(UI_TEXT["zh-Hans"].ask, "提问");
assert.equal(UI_TEXT["zh-Hant"].question, "例如：什麼是神聖三一？");
assert.equal(UI_TEXT.en.ask, "Ask");
assert.equal(UI_TEXT.en.translation, "English translation");
assert.match(HTML, /简体中文/);
assert.match(HTML, /繁體中文/);
assert.match(HTML, /Phase 4E/);
assert.match(HTML, /data-mode="reference"/);
assert.match(HTML, /data-mode="chat"/);
assert.match(HTML, /id="new-chat"/);
assert.match(HTML, /qa_chat_/);
assert.match(HTML, /resolved_question:data\.resolved_question/);
assert.match(HTML, /visitor_id/);
assert.doesNotMatch(HTML, /type="password"|autocomplete="current-password"/);
assert.match(HTML, /-webkit-text-security:disc/);
assert.match(ADMIN_HTML, /搜索后台/);
assert.match(ADMIN_HTML, /未能回答/);
assert.match(ADMIN_HTML, /查看引用 ID/);
assert.match(ADMIN_HTML, /删除/);
assert.doesNotMatch(ADMIN_HTML, /type="password"|autocomplete="current-password"/);
assert.match(ADMIN_HTML, /-webkit-text-security:disc/);
assert.match(ADMIN_HTML, /请输入管理员密钥后再查看/);
assert.match(ADMIN_HTML, /if\(keyInput\.value\)load\(\)/);
assert.match(ADMIN_HTML, /const storage=\{/);
assert.match(ADMIN_HTML, /elements\.namedItem\('key'\)/);
assert.doesNotMatch(ADMIN_HTML, /login\.key/);
assert.doesNotMatch(ADMIN_HTML, /ACCESS_KEY/);
assert.equal(validVisitorId("12345678-abcd_ef"), "12345678-abcd_ef");
assert.equal(validVisitorId("short"), null);
assert.deepEqual(normalizeHistory([{ role: "system", content: "ignore" }, { role: "user", content: "  什么是神圣三一？  " }, { role: "assistant", content: "回答。" }]), [
  { role: "user", content: "什么是神圣三一？" }, { role: "assistant", content: "回答。" }
]);
assert.deepEqual(normalizeHistory([{ role: "user", content: "那它呢？", resolved_question: "神圣三一还有什么方面？" }]), [
  { role: "user", content: "那它呢？", resolved_question: "神圣三一还有什么方面？" }
]);
assert.equal(conversationDependent("那有什么经文证明？"), true);
assert.equal(conversationDependent("难道不是神永远的经纶吗？"), true);
assert.equal(conversationDependent("Isn't it God's eternal economy?"), true);
assert.equal(conversationDependent("What verses prove this?"), true);
assert.equal(conversationDependent("What is the Divine Trinity?"), false);
assert.equal(conversationDependent("Ephesians 4:20, footnote 1"), false);
assert.equal(conversationDependent("我问的是你刚才说的：‘人被造，有接受神并喝祂这活水的性能’这个性能"), true);
assert.equal(conversationDependent("所以这个性能在哪里？我怎么知道我有？"), true);
const conversationHistory = [{ role: "user", content: "什么是神圣三一？" }, { role: "assistant", content: "父、子、灵。" }];
assert.equal(fallbackConversationQuestion("那有什么经文证明？", conversationHistory, "zh-Hans"), "关于“什么是神圣三一？”，那有什么经文证明？");
const peakConversationHistory = [{ role: "user", content: "什么是神圣启示的最高峰" }, { role: "assistant", content: "错误旧回答。" }];
assert.equal(fallbackConversationQuestion("难道不是神永远的经纶吗？", peakConversationHistory, "zh-Hans"), "关于“什么是神圣启示的最高峰”，难道不是神永远的经纶吗？");
assert.equal(await resolveConversationQuestion({ AI: { run: async () => ({ response: "哪些经文证明父、子、灵是神圣三一？" }) } }, "那有什么经文证明？", "zh-Hans", conversationHistory), "哪些经文证明父、子、灵是神圣三一？");
const capacityHistory = [
  { role: "user", content: "什么叫吃喝神，怎么吃喝神？", resolved_question: "什么叫吃喝神，怎么吃喝神？" },
  { role: "assistant", content: "喝基督所赐的活水，就是喝永远的生命。人被造，有接受神并喝祂这活水的性能。 [S3][S4]" }
];
const capacityFollowUp = "这个性能在哪里？人人都有吗？有什么条件？";
const capacityFallback = "关于“人被造，有接受神并喝祂这活水的性能。”，这个性能在哪里？人人都有吗？有什么条件？";
assert.equal(fallbackConversationQuestion(capacityFollowUp, capacityHistory, "zh-Hans"), capacityFallback);
assert.deepEqual(questionFacets(capacityFollowUp), ["location", "universality", "conditions"]);
assert.equal(questionSubject(capacityFallback), "人被造，有接受神并喝祂这活水的性能");
assert.match(retrievalQuestion(capacityFallback), /人的哪一部分或哪个器官/);
assert.match(retrievalQuestion(capacityFallback), /是否每个人受造时都具有/);
assert.match(answerFocusInstruction(capacityFallback, "zh-Hans"), /不要把位置、普遍性、条件或证据，改答成如何操练/);
assert.match(modelForQuestion(capacityFallback), /70b/);
assert.equal(await resolveConversationQuestion({ AI: { run: async () => ({ response: "怎样借着祷读来吃喝主？" }) } }, capacityFollowUp, "zh-Hans", capacityHistory), capacityFallback);
const resolvedCapacity = "人被造用以接受神并喝祂活水的性能在哪里，人人都有吗，有什么条件？";
assert.equal(await resolveConversationQuestion({ AI: { run: async () => ({ response: resolvedCapacity }) } }, capacityFollowUp, "zh-Hans", capacityHistory), resolvedCapacity);
let rewriteSystemPrompt = "";
await resolveConversationQuestion({ AI: { run: async (_model, input) => { rewriteSystemPrompt = input.messages[0].content; return { response: "神在祂永远的经纶中所分赐的是什么？" }; } } }, "那祂分赐的是什么？", "zh-Hans", conversationHistory);
assert.match(rewriteSystemPrompt, /what is dispensed.*object or content/i);
assert.match(answerFocusInstruction("那祂分赐的是什么？", "zh-Hans"), /对象或内容/);
assert.match(answerFocusInstruction("What does God dispense into man?", "en"), /object or content/);
assert.match(answerFocusInstruction("什么是神的分赐？", "zh-Hans"), /简明定义/);
assert.equal(questionIntent("什么是神圣三一？").type, "definition");
assert.equal(questionIntent("神分赐的是什么？").type, "object");
assert.equal(questionIntent("为什么呼求主名？").type, "cause");
assert.equal(questionIntent("神的经纶是为了什么？").type, "purpose");
assert.equal(questionIntent("怎样接受神的分赐？").type, "means");
assert.equal(questionIntent("神的经纶和神的分赐有什么区别？").type, "comparison");
assert.equal(questionIntent("那有什么经文证明？").type, "evidence");
assert.equal(questionIntent("What verses prove the Divine Trinity is one? ").type, "evidence");
assert.equal(questionIntent("难道不是神永远的经纶吗？").type, "verification");
assert.equal(questionIntent("倪柝声什么时候离开上海？").type, "time");
assert.equal(questionIntent("是谁说的来吧我们归向耶和华？").type, "person");
assert.equal(questionIntent("Who is speaking in Hosea 6:1–2?").type, "person");
assert.equal(questionIntent("圣经哪里讲到以弗所召会？").type, "scripture_location");
assert.equal(questionIntent("圣经是什么？").type, "definition");
assert.equal(questionIntent("圣经讲什么？").type, "content");
assert.equal(questionIntent("圣经的中心思想是什么？").type, "central_theme");
assert.equal(questionIntent("聖經主要啟示甚麼？").type, "content");
assert.equal(questionIntent("What is the Bible about?").type, "content");
assert.equal(questionIntent("What is the central thought of the Bible?").type, "central_theme");
assert.equal(questionIntent("What are the contents of the Bible?").type, "content");
assert.equal(questionIntent("What is the Bible's main message?").type, "central_theme");
assert.equal(questionSubject("什么是神圣三一？"), "神圣三一");
assert.equal(questionSubject("为什么呼求主名这么重要？"), "呼求主名");
assert.equal(questionSubject("神的经纶是为了什么？"), "神的经纶");
assert.equal(questionSubject("神的经纶和神的分赐有什么区别？"), "神的经纶和神的分赐");
assert.equal(questionSubject("倪柝声什么时候离开上海？"), "倪柝声离开上海");
assert.equal(questionSubject("是谁说的来吧我们归向耶和华？"), "来吧我们归向耶和华");
assert.equal(questionSubject("How can Christ make home in our heart?"), "Christ make home in our heart");
assert.equal(questionSubject("What is the Divine Trinity?"), "the Divine Trinity");
assert.equal(questionIntent("What does it mean to die to be resurrected?").type, "definition");
assert.equal(questionSubject("What does it mean to die to be resurrected?"), "die to be resurrected");
assert.equal(questionSubject("圣经是什么？"), "圣经");
assert.equal(questionSubject("圣经讲什么？"), "圣经");
assert.equal(questionSubject("圣经的中心思想是什么？"), "圣经");
assert.equal(questionSubject("聖經主要啟示甚麼？"), "圣经");
assert.equal(questionSubject("What does the Bible teach about Christ?"), "the Bible about Christ");
assert.equal(questionSubject("What is the central thought of the Bible?"), "the Bible");
assert.equal(questionSubject("What are the contents of the Bible?"), "the Bible");
assert.equal(questionSubject("What is the Bible's main message?"), "the Bible");
const centralThemeSources = [
  { source_id: "supplementary", text: "中心思想。圣经开始于生命树，也结束于生命树。我们所接受到里面的，就是我们所凭以活着的。" },
  { source_id: "direct", text: "圣经的中心思想。我们来读这本神的话时，应当知道这本书的基本观念，是神渴望将祂自己作到我们里面。" }
];
assert.deepEqual(centralThemeEvidence(centralThemeSources, "圣经的中心思想是什么？").map(item => item.source_id), ["direct"]);
assert.deepEqual(centralThemeEvidence(centralThemeSources, "圣经讲什么？").map(item => item.source_id), ["supplementary", "direct"]);
assert.match(answerFocusInstruction("圣经的中心思想是什么？", "zh-Hans"), /首尾呼应.*不能单独证成中心思想/);
const intentParaphrases = [
  ["How should we understand death and resurrection?", "definition", "death and resurrection"],
  ["What is meant by the mingled spirit?", "definition", "the mingled spirit"],
  ["How do we know that Christ is the Spirit?", "evidence", "Christ is the Spirit"],
  ["Where does the Bible say that Christ is the Spirit?", "scripture_location", "that Christ is the Spirit"],
  ["What is baptism for?", "purpose", "baptism"],
  ["What purpose does baptism serve?", "purpose", "baptism"],
  ["Why does calling on the Lord matter?", "significance", "calling on the Lord"],
  ["What is the significance of calling on the Lord?", "significance", "calling on the Lord"],
  ["What causes spiritual death?", "cause", "spiritual death"],
  ["What is the reason for Christ's incarnation?", "cause", "Christ's incarnation"],
  ["By what means can we experience Christ?", "means", "Christ"],
  ["What do we receive from Christ?", "object", "receive from Christ"],
  ["How is God's economy different from God's dispensing?", "comparison", "God's economy and God's dispensing"],
  ["Do you mean the old man is crucified?", "verification", "the old man is crucified"],
  ["Is this interpretation correct?", "verification", "this interpretation"]
];
for (const [question, intent, subject] of intentParaphrases) {
  assert.equal(questionIntent(question).type, intent, question);
  assert.equal(questionSubject(question), subject, question);
}
const chineseIntentParaphrases = [
  ["如何理解死而复活？", "definition", "死而复活"],
  ["我们怎么知道基督是那灵？", "evidence", "基督是那灵"],
  ["呼求主名有什么用？", "significance", "呼求主名"],
  ["属灵死亡的原因是什么？", "cause", "属灵死亡"],
  ["我们接受的是什么？", "object", "我们接受"]
];
for (const [question, intent, subject] of chineseIntentParaphrases) {
  assert.equal(questionIntent(question).type, intent, question);
  assert.equal(questionSubject(question), subject, question);
}
assert.match(answerFocusInstruction("难道不是神永远的经纶吗？", "zh-Hans"), /完全正确、部分正确或不正确/);
assert.match(answerFocusInstruction("Isn't it God's eternal economy?", "en"), /fully correct, partly correct, or incorrect/);
assert.match(answerFocusInstruction("那有什么经文证明？", "zh-Hans"), /直接支持答案的经节或来源/);
assert.match(answerFocusInstruction("圣经讲什么？", "zh-Hans"), /说了、教导、启示或包含什么/);
assert.match(answerFocusInstruction("圣经的中心思想是什么？", "zh-Hans"), /中心思想、主要题旨或支配的信息/);
assert.equal(await resolveConversationQuestion({ AI: { run: async () => ({ response: "什么是神圣三一？" }) } }, "那有什么经文证明？", "zh-Hans", conversationHistory), "关于“什么是神圣三一？”，那有什么经文证明？");
assert.equal(conversationalAnswer("1. 神分赐的是祂自己。 [S1]\n\n2. 祂在基督里作为那灵分赐到人里面。 [S2]"), "神分赐的是祂自己。 [S1]\n\n祂在基督里作为那灵分赐到人里面。 [S2]");
const highestPeakCoverage = doctrineCoverage("什么是神圣启示的最高峰");
assert.equal(highestPeakCoverage.id, "high_peak_divine_revelation");
const highestPeakZh = doctrineExtractiveAnswer(highestPeakCoverage, [
  { source_id: "doc:book-life-study-bible:pdf-03238:zht-001", citation_id: "S1" },
  { source_id: "doc:book-life-study-bible:pdf-04313:zht-001", citation_id: "S2" }
], "zh-Hans");
assert.match(highestPeakZh.answer, /神成为人.*生命和性情上成为神.*无分于神格/);
assert.match(highestPeakZh.answer, /神永远的经纶就得以完成/);
const highestPeakEn = doctrineExtractiveAnswer(highestPeakCoverage, [
  { source_id: "doc:book-life-study-bible:pdf-03238:en-001", citation_id: "S1" },
  { source_id: "doc:book-life-study-bible:pdf-04313:en-001", citation_id: "S2" }
], "en");
assert.match(highestPeakEn.answer, /God became man.*man may become God in life and in nature/);
assert.match(highestPeakEn.answer, /eternal economy of God is accomplished/);
assert.equal(doctrineCoverage("难道神圣启示的高峰不是神永远的经纶吗").id, "high_peak_divine_revelation");
assert.equal(doctrineCoverage("关于神身位之神圣启示的最高点乃是基督"), null);
const loggedStatements = [];
const fakeLogDb = {
  prepare: sql => ({ sql, bind: (...args) => ({ sql, args }) }),
  batch: async statements => loggedStatements.push(...statements)
};
await writeQueryLog({ ANALYTICS_DB: fakeLogDb }, {
  visitorId: "visitor_12345678", question: "测试问题", locale: "zh-Hans", durationMs: 123.4,
  result: { mode: "semantic_retrieval", answerable: true, generated: false, answerability_reason: "supported", evidence: [{ source_id: "source:1", source_type: "bible" }] }
});
assert.equal(loggedStatements.length, 2);
assert.match(loggedStatements[0].sql, /INSERT INTO query_logs/);
assert.equal(loggedStatements[0].args[0], "visitor_12345678");
assert.equal(loggedStatements[0].args[1], "测试问题");
assert.equal(loggedStatements[0].args[6], 123);
assert.equal(loggedStatements[0].args[8], '["bible"]');
assert.doesNotMatch(JSON.stringify(loggedStatements), /ACCESS_KEY|ADMIN_KEY/);
assert.doesNotThrow(() => new Function(HTML.match(/<script>([\s\S]*?)<\/script>/)[1]));
assert.doesNotThrow(() => new Function(ADMIN_HTML.match(/<script>([\s\S]*?)<\/script>/)[1]));
assert.equal(validateAnswer("回答。[S1]", 2, "zh-Hans"), "回答。[S1]");
assert.equal(validateAnswer("回答。【S1】", 2, "zh-Hans"), "回答。[S1]");
assert.match(validateAnswer("无来源", 2, "zh-Hans"), /没有足够明确/);
assert.match(validateAnswer("错误 [S9]", 2, "en"), /not contain enough/);
assert.match(deterministicAnswer("direct_scripture", [{ citation_id: "S1", reference: "马太福音 28:19", text: "所以你们要去" }], "zh-Hans"), /\[S1\]/);
assert.equal(structuredAnswer({ response: { answerable: true, reason: "supported", paragraphs: [{ text: "回答。", citations: ["S1", "S9"] }] } }, 2, "zh-Hans"), "回答。 [S1]");
assert.match(structuredAnswer({ response: "unstructured [S1]" }, 2, "en"), /not contain enough/);
assert.equal(localizeAnswer("神圣三一与圣灵", "zh-Hant"), "神聖三一與聖靈");
assert.equal(scriptureLocationIntent("圣经哪里讲到以弗所召会"), true);
assert.equal(scriptureLocationIntent("Where in the Bible is the church in Ephesus mentioned?"), true);
assert.equal(scriptureLocationIntent("为什么只有一个新人"), false);
assert.equal(scriptureQuoteIntent("是谁说的来吧我们归向耶和华 为什么"), true);
assert.equal(scriptureQuoteIntent("Who said ‘Come and let us return to Jehovah,’ and why?"), true);
assert.equal(scriptureQuoteIntent("Who is speaking in Hosea 6:1–2?"), true);
assert.equal(scriptureQuoteText("是谁说的来吧我们归向耶和华 为什么"), "来吧我们归向耶和华");
assert.equal(scriptureQuoteText("Who said ‘Come and let us return to Jehovah,’ and why?"), "Come and let us return to Jehovah");
assert.equal(directQuestionNeedsSemanticSearch("Who is speaking in Hosea 6:1–2?"), true);
assert.equal(directQuestionNeedsSemanticSearch("What does Hosea 6:1 say?"), false);
assert.equal(scriptureInterpretationIntent("Who is speaking in Hosea 6:1–2?"), true);
assert.equal(scriptureInterpretationIntent("What does Hosea 6:1 mean?"), true);
assert.equal(scriptureInterpretationIntent("What does Hosea 6:1 say?"), false);
assert.deepEqual(orderEvidenceLayers([
  { source_id: "book", source_type: "reference_book" },
  { source_id: "note", source_type: "footnote" },
  { source_id: "context", source_type: "bible", evidence_role: "context" },
  { source_id: "verse", source_type: "bible", evidence_role: "verse" }
]).map(item => item.source_id), ["verse", "context", "note", "book"]);
assert.equal(doctrineCoverage("Who is speaking in Hosea 6:1–2?").id, "hosea_return_to_jehovah");
assert.equal(englishScriptureSubject("Where in the Bible is the church in Ephesus mentioned?"), "church Ephesus");
assert.equal(await scriptureSearchQuery({ AI: { run: async () => ({ translated_text: "以弗所的召会" }) } }, "Where in the Bible is the church in Ephesus mentioned?", "en"), "以弗所的召会");
assert.equal(await localizeGeneratedAnswer({ AI: { run: async () => ({ translated_text: "Revelation 2:1" }) } }, "启示录 2:1 [S1]", "en"), "Revelation 2:1 [S1]");
assert.equal(lexicalRerank([{ text: "新人是什么" }, { text: "宇宙中只有一个新人" }], "为什么只有一个新人")[0].text, "宇宙中只有一个新人");
assert.equal(whyIntent("为什么呼求主名这么重要？"), true);
assert.equal(importanceIntent("为什么呼求主名这么重要？"), true);
assert.match(modelForQuestion("为什么呼求主名这么重要？"), /70b/);
assert.match(modelForQuestion("什么是神圣三一？"), /8b/);
assert.match(modelForQuestion("圣经讲什么？"), /8b/);
assert.match(modelForQuestion("圣经的中心思想是什么？"), /8b/);
assert.equal(howIntent("How can Christ make home in our heart"), true);
assert.equal(retrievalQuestion("怎么经历变水为酒 约翰福音"), "如何经历、实行或应用变水为酒 约翰福音");
assert.equal(retrievalQuestion("How can we experience the changing of water into wine?"), "the changing of water into wine: concrete means, experience, and practice");
assert.equal(retrievalQuestion("圣经是什么？"), "圣经是什么；圣经的定义和本质");
assert.equal(retrievalQuestion("圣经讲什么？"), "圣经主要讲什么；圣经的主要内容和启示");
assert.equal(retrievalQuestion("圣经的中心思想是什么？"), "圣经的中心思想、主要题旨和中心信息");
assert.equal(retrievalQuestion("What does the Bible teach about Christ?"), "the Bible about Christ: main content, teaching, and revelation");
assert.match(answerFocusInstruction("怎么经历变水为酒", "zh-Hans"), /排除只是广泛适用/);
assert.match(modelForQuestion("How can Christ make home in our heart"), /70b/);
const homeCoverage = doctrineCoverage("How can Christ make home in our heart");
assert.equal(homeCoverage.id, "christ_home_in_heart_practice");
const homeAnswer = doctrineExtractiveAnswer(homeCoverage, homeCoverage.anchors.filter(anchor => anchor.language === "en").map((anchor, index) => ({ source_id: anchor.source_id, citation_id: `S${index + 1}` })), "en");
assert.match(homeAnswer.answer, /give Him the opportunity/);
assert.match(homeAnswer.answer, /take Him both as our person and as our life/);
assert.match(homeAnswer.answer, /when we agree with the Lord/);
assert.doesNotMatch(homeAnswer.answer, /means that Christ occupies/);
assert.equal(lexicalRerank([{ text: "Christ making home means occupying the heart." }, { text: "We must give Him the opportunity to spread." }], "How can Christ make home in our heart")[0].text, "We must give Him the opportunity to spread.");
const waterWineCoverage = doctrineCoverage("怎么经历变水为酒 约翰福音");
assert.equal(waterWineCoverage.id, "water_into_wine_experience");
const waterWineAnswer = doctrineExtractiveAnswer(waterWineCoverage, waterWineCoverage.anchors.filter(anchor => anchor.language !== "en").map((anchor, index) => ({ source_id: anchor.source_id, citation_id: `S${index + 1}` })), "zh-Hans");
assert.match(waterWineAnswer.answer, /水象征死亡，酒象征生命/);
assert.match(waterWineAnswer.answer, /把我们的情形交给主耶稣/);
assert.match(waterWineAnswer.answer, /向主耶稣敞开/);
assert.doesNotMatch(waterWineAnswer.answer, /吃祂|喝祂|神的见证|神的見證/);
const trinityCoverage = doctrineCoverage("what do you prove that the three of the godhead are one");
assert.equal(trinityCoverage.id, "divine_trinity_oneness");
assert.equal(trinityCoverage.aspects.length, 4);
assert.equal(doctrineCoverage("倪柝声什么时候离开上海"), null);
const hoseaCoverage = doctrineCoverage("是谁说的来吧我们归向耶和华 为什么");
assert.equal(hoseaCoverage.id, "hosea_return_to_jehovah");
const hoseaAnswer = doctrineExtractiveAnswer(hoseaCoverage, [{ source_id: "doc:book-2157-truth-lessons:pdf-1706:zh-001", citation_id: "S1" }], "zh-Hans");
assert.match(hoseaAnswer.answer, /申言者何西阿/);
assert.match(hoseaAnswer.answer, /祂撕裂我们，也必医治/);
assert.match(hoseaAnswer.answer, /过两天祂必使我们活过来/);
const coveredResult = structuredResult({ response: { answerable: true, reason: "supported", points: trinityCoverage.aspects.map((aspect, index) => ({ text: `Point ${index + 1}.`, citations: ["S1"], aspect: aspect.id })) } }, 1, "en", Infinity, 4, trinityCoverage.aspects.map(aspect => aspect.id));
assert.equal(coveredResult.answerable, true);
assert.equal(structuredResult({ response: { answerable: true, reason: "supported", points: [{ text: "Only one aspect.", citations: ["S1"], aspect: "essential_oneness" }] } }, 1, "en", Infinity, 1, trinityCoverage.aspects.map(aspect => aspect.id)).reason, "missing_required_aspects");
const anchored = await doctrineAnchorEvidence({ DB: { prepare: () => ({ bind: () => ({ all: async () => ({ results: [{ source_id: trinityCoverage.anchors[0].source_id, source_type: "reference_book", text: "Essentially one." }] }) }) }) } }, trinityCoverage);
assert.equal(anchored[0].coverage_anchor, true);
assert.deepEqual(anchored[0].coverage_aspects, ["essential_oneness", "economical_distinction", "inseparable_operation"]);
const extractiveAnswer = doctrineExtractiveAnswer(trinityCoverage, trinityCoverage.anchors.filter(anchor => anchor.language === "en").map((anchor, index) => ({ source_id: anchor.source_id, citation_id: `S${index + 1}` })), "en");
assert.equal(extractiveAnswer.reason, "source_faithful_coverage");
assert.match(extractiveAnswer.answer, /The three in the Godhead are not separate, but They are essentially one\. \[S1\]/);
assert.match(extractiveAnswer.answer, /Economically speaking, the seven Spirits are the eyes of the Son\./);
assert.doesNotMatch(extractiveAnswer.answer, /coexisting and coinhering/);
const revelationCoverage = doctrineCoverage("七印 七号 四马都是什么");
assert.equal(revelationCoverage.id, "revelation_seals_trumpets_horses");
const revelationEvidence = revelationCoverage.anchors.map((anchor, index) => ({ source_id: anchor.source_id, citation_id: `S${index + 1}` }));
const revelationAnswer = doctrineExtractiveAnswer(revelationCoverage, revelationEvidence, "zh-Hans");
assert.match(revelationAnswer.answer, /第一印是白马.*福音/);
assert.match(revelationAnswer.answer, /第二印是红马.*战争/);
assert.match(revelationAnswer.answer, /第三印是黑马.*饥荒/);
assert.match(revelationAnswer.answer, /第四印是灰马.*死亡/);
assert.match(revelationAnswer.answer, /第五印揭示历代基督徒的殉道/);
assert.match(revelationAnswer.answer, /第一号—审判地/);
assert.match(revelationAnswer.answer, /第七号—神奥秘的完成/);
assert.match(revelationAnswer.answer, /大灾难的前奏、序幕/);
const sixthSealCoverage = doctrineCoverage("超自然灾难是什么，难道不是大灾难吗？");
assert.equal(sixthSealCoverage.id, "sixth_seal_supernatural_calamity");
const sixthSealEvidence = sixthSealCoverage.anchors.map((anchor, index) => ({ source_id: anchor.source_id, citation_id: `S${index + 1}` }));
const sixthSealAnswer = doctrineExtractiveAnswer(sixthSealCoverage, sixthSealEvidence, "zh-Hans");
assert.match(sixthSealAnswer.answer, /启示录六章十二至十四节/);
assert.match(sixthSealAnswer.answer, /不等于大灾难的主体/);
assert.match(sixthSealAnswer.answer, /前奏、序幕/);
assert.match(sixthSealAnswer.answer, /第五号是第一样/);
const weighted = await rerankEvidence({ AI: { run: async () => ({ response: [{ id: 1, score: 1 }, { id: 0, score: 0.5 }] }) } }, [
  { source_id: "ordinary:1", text: "Ordinary one" },
  { source_id: "anchor:1", text: "Core doctrine", coverage_anchor: true, coverage_weight: 4 },
  { source_id: "ordinary:2", text: "Ordinary two" }
], "question", 2);
assert.equal(weighted[0].source_id, "anchor:1");
let focusedRerankQuery = "";
await rerankEvidence({ AI: { run: async (_model, input) => { focusedRerankQuery = input.query; return { response: [{ id: 0, score: 1 }] }; } } }, [
  { source_id: "definition:1", text: "神的分赐是神的安排。" },
  { source_id: "object:1", text: "神所分赐的是祂自己。" }
], "神分赐的是什么？", 1);
assert.match(focusedRerankQuery, /对象或内容/);
assert.match(focusedRerankQuery, /Required subject: 神分赐/);
const lateEvidence = `${"无关内容。".repeat(220)}呼求主名是基督徒的标记，并使信徒享受主的丰富而得救。${"结尾。".repeat(30)}`;
assert.match(evidenceExcerpt(lateEvidence, "为什么呼求主名这么重要？", 240), /标记/);
assert.match(evidenceExcerpt(lateEvidence, "为什么呼求主名这么重要？", 240), /丰富/);
assert.equal(applyReranker([{ text: "A" }, { text: "B" }], { response: [{ id: 1, score: 0.9 }, { id: 0, score: 0.2 }] })[0].text, "B");
assert.equal(structuredAnswer({ response: { answerable: true, reason: "supported", paragraphs: [
  { text: "同一句。同一句。", citations: ["S1"] },
  { text: "同一句。", citations: ["S1"] }
] } }, 1, "zh-Hans"), "同一句。 [S1]");
assert.equal(structuredAnswer({ response: { answerable: true, reason: "supported", paragraphs: [{ text: "一。二。三。", citations: ["S1"] }] } }, 1, "zh-Hans", 2), "一。二。 [S1]");
assert.equal(structuredResult({ response: { answerable: false, reason: "no date", paragraphs: [] } }, 2, "zh-Hans").answerable, false);
assert.equal(structuredResult({ response: { answerable: true, reason: "supported", points: [
  { text: "这是基督徒的标记。", citations: ["S1"] },
  { text: "使人享受主的丰富。", citations: ["S2"] }
] } }, 2, "zh-Hans", Infinity, 2).answer, "1. 这是基督徒的标记。 [S1]\n\n2. 使人享受主的丰富。 [S2]");
assert.equal(structuredResult({ response: { answerable: true, reason: "supported", points: [
  { text: "神分赐的是祂自己。", citations: ["S1"] },
  { text: "祂在基督里作为那灵分赐到人里面。", citations: ["S2"] },
  { text: "分赐是为着神的经纶。", citations: ["S3"] }
] } }, 3, "zh-Hans", Infinity, 1, [], true).answer, "神分赐的是祂自己。 [S1] 祂在基督里作为那灵分赐到人里面。 [S2]");
assert.equal(structuredResult({ response: { answerable: true, reason: "supported", points: [
  { text: "只有一点。", citations: ["S1"] }
] } }, 1, "zh-Hans", Infinity, 2).reason, "insufficient_answer_coverage");
assert.equal(structuredResult({ response: { answerable: true, answer_type: "definition", reason: "supported", points: [
  { text: "神所分赐的是祂自己。", citations: ["S1"] }
] } }, 1, "zh-Hans", Infinity, 1, [], true, "object").reason, "wrong_answer_type");
assert.equal(structuredResult({ response: { answerable: true, answer_type: "object", reason: "supported", points: [
  { text: "神所分赐的是祂自己。", citations: ["S1"] }
] } }, 1, "zh-Hans", Infinity, 1, [], true, "object").answerable, true);
assert.equal(structuredResult({ response: { answerable: true, answer_type: "means", subject_supported: false, reason: "generic", points: [
  { text: "我们需要祷告。", citations: ["S1"] }
] } }, 1, "zh-Hans", Infinity, 1, [], true, "means", true).reason, "wrong_or_unsupported_subject");
assert.equal(structuredResult({ response: { answerable: true, answer_type: "means", subject_supported: true, reason: "supported", points: [
  { text: "把这个死亡的情形交给主耶稣，并向祂敞开。", citations: ["S1"] }
] } }, 1, "zh-Hans", Infinity, 1, [], true, "means", true).answerable, true);
assert.equal(parseNumber("二十八"), 28);
assert.equal(parseNumber("一百一十九"), 119);
assert.equal(requestedNote("第一個註解"), 1);
assert.deepEqual(directReference("約翰福音一章一節的第一個註解說什麼？"), { book: "John", chapter: 1, start: 1, end: 1, note: 1 });
assert.deepEqual(directReference("马太福音28:19"), { book: "Matt", chapter: 28, start: 19, end: 19, note: null });
assert.deepEqual(directReference("Hosea 6:1–2"), { book: "Hos", chapter: 6, start: 1, end: 2, note: null });
assert.deepEqual(directReference("Ephesians 4:20, footnote 1"), { book: "Eph", chapter: 4, start: 20, end: 20, note: 1 });
const exactBinds = [];
const exactEnglish = await exactLookup({ DB: { prepare: sql => ({ bind: (...values) => ({ all: async () => {
  exactBinds.push({ sql, values });
  return { results: sql.includes("FROM footnotes") ? [{ book_name: "Ephesians", chapter: 4, verse: 20, note_no: 1, text: "English note", source_id: "footnote:rcv-en:Eph.4.20.1" }] : [] };
} }) }) } }, "Ephesians 4:20, footnote 1", "en");
assert.equal(exactEnglish.evidence[0].language, "en");
assert.equal(exactEnglish.evidence[0].text, "English note");
assert.equal(exactBinds.find(item => item.sql.includes("FROM footnotes")).values.at(-1), "en");
const quotaError = pineconeFailure(429, "You've reached the embedding token limit for the current month");
assert.equal(quotaError.code, "pinecone_monthly_quota");
assert.deepEqual(temporarySemanticResult(quotaError, "zh-Hans"), {
  mode: "semantic_temporarily_unavailable",
  evidence: [],
  answer_markdown: "语义检索的本月额度已用完，目前无法回答需要语义搜索的问题。精确经文和脚注查询仍可使用；请在额度重置后再试。",
  answerable: false,
  answerability_reason: "pinecone_monthly_quota",
  generated: false,
  degraded: true
});
assert.match(temporarySemanticResult(pineconeFailure(500, "server error"), "en").answer_markdown, /temporarily busy/);
assert.match(retrievalFailureResult("zh-Hans", new Error("unexpected failure")).answer_markdown, /检索服务暂时无法完成/);
assert.equal(retrievalFailureResult("en", new Error("unexpected failure")).mode, "retrieval_temporarily_unavailable");
assert.equal(keywordQuery("什么是神圣启示的最高峰？"), '"神圣启示的最高峰"');
assert.equal(keywordQuery("怎么经历变水为酒？"), '"变水为酒"');
assert.equal(keywordQuery("什么是神圣启示的最高峰？", true), '"神圣启示" AND "最高峰"');
assert.equal(keywordQuery("What is the Divine Trinity?"), '"divine trinity"');
assert.equal(keywordQuery("What is the Divine Trinity?", true), '"divine" AND "trinity"');
assert.equal(englishWholeWordMatch("What is the mending ministry of John?", { text: "The recommending ministry of John the Baptist" }), false);
assert.equal(englishWholeWordMatch("What is the mending ministry of John?", { text: "John carried out a mending ministry" }), true);
assert.deepEqual(await crossLanguageQueries({ AI: { run: async () => ({ translated_text: "约翰的修补职事是什么？" }) } }, "What is the mending ministry of John?", "en"), [
  "What is the mending ministry of John?", "修补的职事", "修补职事", "约翰的修补职事是什么？"
]);
const bilingualEvidence = await presentationEvidence({ AI: { run: async () => ({ translated_text: "John's mending ministry concerns the truth of Christ's person." }) } }, [
  { citation_id: "S1", text: "关于基督身位的真理，乃是约翰修补职事基本且中心的元素。" },
  { citation_id: "S2", text: "未引用来源。" }
], { answerable: true, answer: "Answer. [S1]" }, "en");
assert.equal(bilingualEvidence.length, 1);
assert.match(bilingualEvidence[0].translated_text, /mending ministry/);
const englishFootnoteEvidence = await presentationEvidence({ AI: { run: async () => { throw new Error("must not translate footnote"); } } }, [
  { citation_id: "S1", source_type: "footnote", book_id: "Eph", chapter: 4, verse_start: 20, note_no: 1, language: "zh-Hans", text: "中文注脚全文" }
], { answerable: true, answer: "Answer. [S1]" }, "en", "What does the footnote say?");
assert.equal(englishFootnoteEvidence[0].reference, "Ephesians 4:20, footnote 1");
assert.equal(englishFootnoteEvidence[0].text, "Chinese Recovery Version footnote referenced; full text not displayed.");
assert.equal(englishFootnoteEvidence[0].translated_text, undefined);
const importedEnglishFootnote = await presentationEvidence({ AI: { run: async () => { throw new Error("must not translate English footnote"); } } }, [
  { citation_id: "S1", source_type: "footnote", book_id: "Eph", chapter: 4, verse_start: 20, note_no: 1, language: "en", text: "To learn Christ is simply to be molded into the pattern of Christ." }
], { answerable: true, answer: "Answer. [S1]" }, "en", "What does Ephesians 4:20, footnote 1 say?");
assert.equal(importedEnglishFootnote[0].reference, "Ephesians 4:20, footnote 1");
assert.match(importedEnglishFootnote[0].text, /molded into the pattern of Christ/);
const falseSubstringEvidence = await d1KeywordEvidence({ DB: { prepare: () => ({ bind: () => ({ all: async () => ({ results: [{ source_id: "wrong:1", source_type: "reference_book", title: "Truth Lessons", reference: "Truth Lessons", text: "The recommending ministry of John the Baptist", rank: -4 }] }) }) }) } }, "What is the mending ministry of John?", ["reference_book"]);
assert.deepEqual(falseSubstringEvidence, []);
const d1Evidence = await d1KeywordEvidence({ DB: { prepare: sql => ({ bind: (...values) => ({ all: async () => ({ results: [{ source_id: "doc:1", source_type: "reference_book", title: "书名", reference: "章节", pdf_page: 3, pdf_page_end: 4, language: "zh-Hans", text: "神圣启示的最高峰", rank: -2 }] }) }) }) } }, "什么是神圣启示的最高峰？", ["reference_book"]);
assert.equal(d1Evidence[0].source_id, "doc:1");
assert.equal(d1Evidence[0].score, 2);

assert.equal(normalizeQueryText("how can i receive the impartation of llife"), "how can i receive the impartation of life");
assert.equal(normalizeSourceText("Life requires life but\nalso the life supply.\nTeaching continues."), "Life requires life but also the life supply. Teaching continues.");
assert.equal(normalizeSourceText("The divine dis-\npensing supplies life."), "The divine dispensing supplies life.");
assert.equal(precisePassage("iven and healed. If this brother’s sin is unto death, you should not pray to impart life into him. Instead, you may pray from another angle. A trailing frag", "how can I impart life", 220), "If this brother’s sin is unto death, you should not pray to impart life into him. Instead, you may pray from another angle.");
assert.equal(sourceQuality({ source_type: "reference_book", text: "■ CONTENTS 1. Introduction 2. Four Aspects of the Spirit 3. The Compound Spirit" }, "how can I receive the impartation of life"), 0);
assert.equal(sourceQuality({ source_type: "reference_book", title: "The Crucified Christ", text: "CONTENTS 1. The Life and the Way 2. God's Eternal Purpose and God's Work" }, "how can I receive the impartation of life"), 0);
assert.ok(sourceQuality({ source_type: "reference_book", text: "The impartation into us of all the things of life is through the full knowledge of God. This full knowledge is a deep, thorough, experiential knowledge." }, "how can I receive the impartation of llife") > 0);
const preciseReferences = prepareReferenceEvidence([
  { source_id: "toc", source_type: "reference_book", title: "The Spirit and the Body", text: "■ CONTENTS 1. Introduction 2. Four Aspects of the Spirit" },
  { source_id: "answer", source_type: "reference_book", title: "Life-study of Second Peter", pdf_page: 13218, text: "e and godliness through the full knowledge of Him. The impartation into us of all the things of life is through the full knowledge of God. This full knowledge is a deep, thorough, experiential knowledge. The preposition through" }
], "how can i receive the impartation of llife", 5);
assert.equal(preciseReferences.length, 1);
assert.equal(preciseReferences[0].citation_id, "S1");
assert.match(preciseReferences[0].text, /^The impartation into us/);
assert.match(preciseReferences[0].text, /experiential knowledge\.$/);
assert.doesNotMatch(preciseReferences[0].text, /CONTENTS|^e and|preposition through$/);
const hoseaBibleRows = [
  { book_name: "Hosea", chapter: 6, verse: 1, text: "Come and let us return to Jehovah; For He has torn us, but He will heal us.", source_id: "bible:rcv-en:Hos.6.1" },
  { book_name: "Hosea", chapter: 6, verse: 2, text: "He will enliven us after two days; On the third day He will raise us up.", source_id: "bible:rcv-en:Hos.6.2" }
];
const hoseaTestEnv = {
  DB: {
    prepare: sql => ({ bind: () => ({ all: async () => {
      if (sql.includes("FROM search_chunks")) return { results: [{
        source_id: "doc:book-2157-truth-lessons:pdf-1706:en-001",
        source_type: "reference_book",
        title: "Truth Lessons",
        reference: "Truth Lessons, Level 2",
        pdf_page: 1706,
        language: "en",
        text: "The prophet Hosea, the writer of the book, said, ‘Come and let us return to Jehovah.’ The reason is in the same verse: ‘For He has torn us, but He will heal us.’"
      }] };
      if (sql.includes("FROM footnotes")) return { results: [{ book_name: "Hosea", chapter: 6, verse: 1, note_no: 1, text: "This is Hosea's call to Israel to return to Jehovah.", source_id: "footnote:rcv-en:Hos.6.1.1" }] };
      if (sql.includes("ORDER BY chapter DESC")) return { results: [{ book_name: "Hosea", chapter: 5, verse: 15, text: "I will go away and return to My place, until they acknowledge their offense.", source_id: "bible:rcv-en:Hos.5.15" }] };
      if (sql.includes("ORDER BY chapter ASC")) return { results: [{ book_name: "Hosea", chapter: 6, verse: 3, text: "Therefore let us know, let us pursue knowing Jehovah.", source_id: "bible:rcv-en:Hos.6.3" }] };
      if (sql.includes("FROM bible_verses")) return { results: hoseaBibleRows };
      return { results: [] };
    } }) })
  }
};
const hoseaContext = await scriptureContextEvidence(hoseaTestEnv, { book: "Hos", chapter: 6, start: 1, end: 2 }, "en");
assert.deepEqual(hoseaContext.map(item => item.source_id), ["bible:rcv-en:Hos.6.1", "bible:rcv-en:Hos.6.2", "bible:rcv-en:Hos.5.15", "bible:rcv-en:Hos.6.3"]);
assert.deepEqual(hoseaContext.map(item => item.evidence_role), ["verse", "verse", "context", "context"]);
const hoseaNotes = await footnotesForReference(hoseaTestEnv, { book: "Hos", chapter: 6, start: 1, end: 2 }, "en");
assert.equal(hoseaNotes[0].evidence_role, "footnote");
const hoseaReferenceResult = await answerQuery(hoseaTestEnv, "Who is speaking in Hosea 6:1–2?", "en", {}, false);
assert.equal(hoseaReferenceResult.presentation, "study");
assert.match(hoseaReferenceResult.answer_markdown, /prophet Hosea, the writer of the book/i);
assert.equal(hoseaReferenceResult.answerable, true);
assert.deepEqual(hoseaReferenceResult.evidence.map(item => item.evidence_role), ["reference"]);
assert.match(hoseaReferenceResult.evidence.find(item => item.source_type === "reference_book").text, /prophet Hosea/);

let treeReferenceSearches = 0;
const originalFetch = globalThis.fetch;
globalThis.fetch = async url => {
  const href = String(url);
  let hits = [];
  if (href.includes("/namespaces/phase1/search")) {
    treeReferenceSearches += 1;
    hits = [{
      _id: "doc:should-not-be-used",
      _score: 0.99,
      fields: { source_type: "reference_book", title: "Reference book", chunk_text: "A reference-book answer that should not be retrieved when the footnote is sufficient." }
    }];
  } else if (href.includes("/namespaces/phase2-bible/search")) {
    hits = [{ _id: "bible-hit", _score: 0.98, fields: { book_id: "Gen", chapter: 2, verse_start: 9, verse_end: 9, language: "en", source_type: "bible" } }];
  } else if (href.includes("/namespaces/phase2-footnotes/search")) {
    hits = [{
      _id: "footnote:rcv-en:Gen.2.9.2",
      _score: 0.99,
      fields: {
        book_id: "Gen", chapter: 2, verse_start: 9, verse_end: 9, note_no: 2, language: "en", source_type: "footnote",
        heading_path: "Genesis 2:9, footnote 2",
        chunk_text: "The tree of life signifies the Triune God embodied in Christ as life to man in the form of food."
      }
    }];
  }
  return new Response(JSON.stringify({ result: { hits } }), {
    status: 200,
    headers: { "content-type": "application/json" }
  });
};
const treeTestEnv = {
  PINECONE_HOST: "example.pinecone.test",
  PINECONE_API_KEY: "test-only",
  PINECONE_NAMESPACE: "phase1",
  PINECONE_BIBLE_NAMESPACE: "phase2-bible",
  PINECONE_FOOTNOTE_NAMESPACE: "phase2-footnotes",
  DB: {
    batch: async statements => statements.map(() => ({ results: [{
      book_name: "Genesis",
      chapter: 2,
      verse: 9,
      text: "Jehovah God caused to grow the tree of life in the middle of the garden.",
      source_id: "bible:rcv-en:Gen.2.9"
    }] })),
    prepare: sql => {
      const all = async () => {
      if (sql.includes("FROM footnotes")) return { results: [{
        book_name: "Genesis",
        chapter: 2,
        verse: 9,
        note_no: 2,
        text: "The tree of life signifies the Triune God embodied in Christ as life to man in the form of food.",
        source_id: "footnote:rcv-en:Gen.2.9.2"
      }] };
      if (sql.includes("ORDER BY chapter DESC") || sql.includes("ORDER BY chapter ASC")) return { results: [] };
      if (sql.includes("FROM bible_verses")) return { results: [{
        book_name: "Genesis",
        chapter: 2,
        verse: 9,
        text: "Jehovah God caused to grow the tree of life in the middle of the garden.",
        source_id: "bible:rcv-en:Gen.2.9"
      }] };
      if (sql.includes("FROM search_chunks")) return { results: [{
        source_id: "doc:should-not-be-used",
        source_type: "reference_book",
        title: "Reference book",
        text: "A reference-book answer that should not be retrieved when the footnote is sufficient."
      }] };
      return { results: [] };
      };
      return { all, bind: () => ({ all }) };
    }
  },
  AI: {
    run: async (_model, input) => {
      if (input?.contexts) return { response: input.contexts.map((_item, id) => ({ id, score: 1 - id / 10 })) };
      if (input?.messages) return { response: {
        answerable: true,
        answer_type: "definition",
        subject_supported: true,
        reason: "primary_sources_sufficient",
        points: [{
          text: "The tree of life signifies the Triune God embodied in Christ as life to man in the form of food.",
          citations: ["S1", "S2"]
        }]
      } };
      return {};
    }
  }
};
const treeResult = await answerQuery(treeTestEnv, "What is the spiritual meaning of the tree of life?", "en", {}, false);
globalThis.fetch = originalFetch;
assert.equal(treeResult.presentation, "study");
assert.equal(treeResult.answerable, true);
assert.match(treeResult.answer_markdown, /signifies the Triune God embodied in Christ as life to man/i);
assert.equal(treeResult.evidence.some(item => item.source_type === "reference_book"), false);
assert.equal(treeResult.evidence.some(item => item.source_type === "bible"), true);
assert.equal(treeResult.evidence.some(item => item.source_type === "footnote"), true);
assert.equal(treeReferenceSearches, 0);

console.log("worker unit checks passed");
