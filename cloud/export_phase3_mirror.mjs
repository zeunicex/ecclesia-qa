#!/usr/bin/env node
import fs from "node:fs";
import readline from "node:readline";
import OpenCC from "opencc-js";

const root = new URL("../", import.meta.url);
const chunksPath = process.argv[2] || new URL("output/phase3/chunks.jsonl", root);
const outPath = process.argv[3] || new URL("output/cloud/d1-phase3-zh-hans.sql", root);
const convert = OpenCC.Converter({ from: "tw", to: "cn" });
const sql = value => value == null ? "NULL" : typeof value === "number" ? String(value) : `'${String(value).replaceAll("'", "''")}'`;
const output = fs.createWriteStream(outPath, { encoding: "utf8" });
output.write("-- Simplified-Chinese D1 search mirror for Traditional-Chinese Life-study text.\n");
output.write("DELETE FROM search_chunks WHERE source_id GLOB 'doc:book-life-study-bible:*:zhs-mirror';\n");
let count = 0;
for await (const line of readline.createInterface({ input: fs.createReadStream(chunksPath, "utf8"), crlfDelay: Infinity })) {
  const row = JSON.parse(line), metadata = row.metadata;
  if (metadata.language !== "zh-Hant") continue;
  const values = [
    `${row.id}:zhs-mirror`, metadata.source_type, "新旧约生命读经", convert(metadata.heading_path),
    metadata.page_start, metadata.page_end, "zh-Hans", convert(row.text)
  ];
  output.write(`INSERT INTO search_chunks (source_id,source_type,title,reference,pdf_page,pdf_page_end,language,text) VALUES (${values.map(sql).join(",")});\n`);
  count++;
}
await new Promise(resolve => output.end(resolve));
console.log(JSON.stringify({ search_mirrors: count, output: String(outPath) }));
