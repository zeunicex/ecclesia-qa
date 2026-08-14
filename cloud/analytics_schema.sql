CREATE TABLE IF NOT EXISTS query_logs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
  visitor_id TEXT,
  question TEXT NOT NULL,
  locale TEXT NOT NULL,
  mode TEXT,
  answerable INTEGER NOT NULL DEFAULT 0,
  generated INTEGER NOT NULL DEFAULT 0,
  duration_ms INTEGER NOT NULL DEFAULT 0,
  evidence_count INTEGER NOT NULL DEFAULT 0,
  source_types_json TEXT NOT NULL DEFAULT '[]',
  source_ids_json TEXT NOT NULL DEFAULT '[]',
  answerability_reason TEXT
);

CREATE INDEX IF NOT EXISTS idx_query_logs_created_at ON query_logs(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_query_logs_answerable ON query_logs(answerable, created_at DESC);
