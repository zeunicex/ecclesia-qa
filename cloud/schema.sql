PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS documents (
  id TEXT PRIMARY KEY,
  title TEXT NOT NULL,
  title_en TEXT,
  language TEXT NOT NULL,
  source_type TEXT NOT NULL,
  checksum TEXT NOT NULL,
  corpus_version TEXT NOT NULL,
  rights_policy TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS bible_verses (
  book_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  verse INTEGER NOT NULL,
  translation TEXT NOT NULL,
  language TEXT NOT NULL,
  book_name TEXT NOT NULL,
  text TEXT NOT NULL,
  source_id TEXT NOT NULL,
  PRIMARY KEY (book_id, chapter, verse, translation, language)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS footnotes (
  book_id TEXT NOT NULL,
  chapter INTEGER NOT NULL,
  verse INTEGER NOT NULL,
  note_no INTEGER NOT NULL,
  translation TEXT NOT NULL,
  language TEXT NOT NULL,
  book_name TEXT NOT NULL,
  heading_text TEXT NOT NULL,
  text TEXT NOT NULL,
  source_id TEXT NOT NULL,
  PRIMARY KEY (book_id, chapter, verse, note_no, translation, language)
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS topics (
  id TEXT PRIMARY KEY,
  references_json TEXT NOT NULL
) WITHOUT ROWID;

CREATE TABLE IF NOT EXISTS topic_aliases (
  language TEXT NOT NULL,
  alias TEXT NOT NULL,
  topic_id TEXT NOT NULL,
  PRIMARY KEY (language, alias)
) WITHOUT ROWID;

CREATE VIRTUAL TABLE IF NOT EXISTS search_chunks USING fts5(
  source_id UNINDEXED,
  source_type UNINDEXED,
  title,
  reference UNINDEXED,
  pdf_page UNINDEXED,
  pdf_page_end UNINDEXED,
  language UNINDEXED,
  text,
  tokenize='trigram'
);
