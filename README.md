# Ecclesia QA

Ecclesia QA is a multilingual, citation-first Bible and ministry reference chatbot. It supports Simplified Chinese, Traditional Chinese, and English through two interfaces:

- **Reference search** for a direct answer with Bible, footnote, and reference-book evidence cards.
- **Conversation** for contextual follow-up questions while retaining cited evidence.

The runtime uses Cloudflare Workers, Workers AI, D1, and Pinecone. Exact Bible and footnote lookups remain in D1; semantic questions retrieve Bible, footnote, and reference-book candidates separately, rerank them, check answerability, and generate only source-supported claims.

## Repository layout

```text
cloud/              Cloudflare Worker, schemas, tests, evaluation, and import tools
scripts/            Corpus parsers and staged build tools
README.md           Project overview
```

The copyrighted source books, Bible files, generated corpus chunks, database exports, import progress, access keys, and API keys are intentionally excluded from Git.

## Local checks

```bash
cd cloud
npm ci
npm test
npx wrangler deploy --dry-run
```

See [`cloud/README.md`](cloud/README.md) for the architecture, corpus stages, deployment bindings, rebuild commands, privacy model, and acceptance checks.

## Secrets

The Worker expects encrypted Cloudflare secrets named `ACCESS_KEY`, `ADMIN_KEY`, and `PINECONE_API_KEY`. Never commit their values. Configure them with `wrangler secret put`.

## Data and rights

This repository contains application code and metadata schemas only. It does not grant redistribution rights for any Bible text, footnotes, ministry publications, or imported source files. Keep the deployed interface access-controlled until the applicable sharing policy has been reviewed.
