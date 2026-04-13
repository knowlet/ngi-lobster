PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS topics (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  slug TEXT NOT NULL UNIQUE,
  name TEXT NOT NULL,
  category TEXT NOT NULL, -- geopolitics | market | ai | security | company | macro
  description TEXT,
  status TEXT DEFAULT 'active',
  created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP,
  updated_at_utc TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS sources (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  source_type TEXT NOT NULL, -- api | web | daemon | file | agent | exchange
  source_name TEXT NOT NULL,
  base_url TEXT,
  trust_level TEXT DEFAULT 'medium', -- low | medium | high
  notes TEXT,
  created_at_utc TEXT DEFAULT CURRENT_TIMESTAMP,
  UNIQUE(source_type, source_name)
);

CREATE TABLE IF NOT EXISTS market_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER,
  source_id INTEGER,
  symbol TEXT NOT NULL,
  market_type TEXT NOT NULL, -- index | stock | futures | rate | fx | commodity | crypto
  price REAL,
  change_pct_24h REAL,
  volume REAL,
  open_interest REAL,
  session_label TEXT,
  snapshot_at_utc TEXT NOT NULL,
  collected_at_utc TEXT NOT NULL,
  raw_json TEXT,
  FOREIGN KEY(topic_id) REFERENCES topics(id),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_market_snapshots_symbol_time ON market_snapshots(symbol, snapshot_at_utc DESC);

CREATE TABLE IF NOT EXISTS prediction_market_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER,
  source_id INTEGER,
  platform TEXT NOT NULL, -- polymarket
  market_id TEXT,
  market_slug TEXT,
  market_name TEXT NOT NULL,
  contract_deadline_utc TEXT,
  yes_probability REAL,
  no_probability REAL,
  spread_pct REAL,
  volume_24h REAL,
  open_interest REAL,
  change_pp_24h REAL,
  snapshot_at_utc TEXT NOT NULL,
  collected_at_utc TEXT NOT NULL,
  raw_json TEXT,
  FOREIGN KEY(topic_id) REFERENCES topics(id),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_prediction_market_topic_time ON prediction_market_snapshots(topic_id, snapshot_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_prediction_market_platform_market ON prediction_market_snapshots(platform, market_id, snapshot_at_utc DESC);

CREATE TABLE IF NOT EXISTS first_principles_snapshots (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER,
  source_id INTEGER,
  signal_type TEXT NOT NULL, -- adsb | shipping | energy | official_signal | osint | derived
  metric_name TEXT NOT NULL,
  metric_value REAL,
  metric_unit TEXT,
  score REAL,
  snapshot_at_utc TEXT NOT NULL,
  collected_at_utc TEXT NOT NULL,
  raw_json TEXT,
  FOREIGN KEY(topic_id) REFERENCES topics(id),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_fp_topic_signal_time ON first_principles_snapshots(topic_id, signal_type, snapshot_at_utc DESC);

CREATE TABLE IF NOT EXISTS firehose_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER,
  source_id INTEGER,
  received_at_utc TEXT NOT NULL,
  publish_time_utc TEXT,
  tag TEXT,
  priority TEXT,
  title TEXT,
  url TEXT,
  snippet TEXT,
  raw_json TEXT NOT NULL,
  FOREIGN KEY(topic_id) REFERENCES topics(id),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_firehose_received ON firehose_events(received_at_utc DESC);
CREATE INDEX IF NOT EXISTS idx_firehose_tag ON firehose_events(tag, received_at_utc DESC);

CREATE TABLE IF NOT EXISTS official_statements (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  topic_id INTEGER,
  source_id INTEGER,
  actor_name TEXT NOT NULL,
  actor_role TEXT,
  org_name TEXT,
  statement_type TEXT, -- speech | post | press_release | interview
  headline TEXT,
  body_text TEXT,
  url TEXT,
  statement_at_utc TEXT,
  collected_at_utc TEXT NOT NULL,
  sentiment_score REAL,
  escalation_score REAL,
  raw_json TEXT,
  FOREIGN KEY(topic_id) REFERENCES topics(id),
  FOREIGN KEY(source_id) REFERENCES sources(id)
);
CREATE INDEX IF NOT EXISTS idx_official_actor_time ON official_statements(actor_name, statement_at_utc DESC);

CREATE TABLE IF NOT EXISTS report_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_kind TEXT NOT NULL, -- morning | evening | intel_note
  run_date TEXT NOT NULL,
  workflow_status TEXT,
  source_path TEXT,
  headline TEXT,
  summary_text TEXT,
  artifact_text TEXT,
  delivered INTEGER DEFAULT 0,
  delivered_to TEXT,
  created_at_utc TEXT NOT NULL,
  updated_at_utc TEXT NOT NULL
);
CREATE UNIQUE INDEX IF NOT EXISTS idx_report_kind_date ON report_runs(report_kind, run_date);

CREATE TABLE IF NOT EXISTS report_data_links (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  report_run_id INTEGER NOT NULL,
  topic_id INTEGER,
  data_table TEXT NOT NULL,
  data_row_id INTEGER,
  note TEXT,
  FOREIGN KEY(report_run_id) REFERENCES report_runs(id) ON DELETE CASCADE,
  FOREIGN KEY(topic_id) REFERENCES topics(id)
);
CREATE INDEX IF NOT EXISTS idx_report_links_report ON report_data_links(report_run_id);

-- Existing table `ngi_runs` may already exist. Keep it, but create if absent.
CREATE TABLE IF NOT EXISTS ngi_runs (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  timestamp_utc TEXT NOT NULL,
  market_name TEXT,
  market_prob REAL,
  fp_prob REAL,
  ngi REAL,
  ngi_percentage REAL,
  adsb_count INTEGER,
  adsb_peace_score REAL,
  adsb_used INTEGER,
  firehose_events_analyzed INTEGER,
  firehose_peace_score REAL,
  threshold REAL,
  threshold_crossed INTEGER,
  alert_decision TEXT,
  alert_reason TEXT,
  reasons_json TEXT,
  market_misses_json TEXT,
  watch_next_json TEXT,
  raw_json TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_ngi_time ON ngi_runs(timestamp_utc DESC);

INSERT OR IGNORE INTO topics (slug, name, category, description) VALUES
('us_iran_ceasefire', 'US x Iran ceasefire', 'geopolitics', 'US-Iran ceasefire / de-escalation probability tracking'),
('iran_conflict', 'Iran conflict escalation', 'geopolitics', 'Regional escalation, military action, Hormuz, retaliation'),
('crude_oil_end_march', 'Crude oil end-of-March targets', 'market', 'Oil price threshold and energy-risk tracking'),
('ai_bigtech', 'AI big tech strategic moves', 'ai', 'OpenAI, Anthropic, Nvidia, Google, Apple, Amazon major developments'),
('openalice_status', 'OpenAlice service status', 'ai', 'Local OpenAlice availability and health tracking');

INSERT OR IGNORE INTO sources (source_type, source_name, base_url, trust_level, notes) VALUES
('api', 'polymarket', 'https://gamma-api.polymarket.com', 'medium', 'Prediction market API / web snapshots'),
('api', 'opensky', 'https://opensky-network.org', 'medium', 'ADS-B / aircraft state source'),
('daemon', 'firehose', 'http://localhost:8787', 'medium', 'Firehose daemon and events stream'),
('agent', 'ngi_monitor', NULL, 'high', 'Local NGI derivation pipeline'),
('agent', 'report_automation', NULL, 'high', 'Morning/evening report workflow outputs'),
('service', 'openalice', 'http://localhost:3002', 'high', 'OpenAlice local service health');
