# Migration Map

## Purpose

Classify current system artifacts into the four target layers so migration work is explicit.

## Layer mapping

### Evidence Layer

Raw or near-raw inputs. These should be treated as immutable or append-only.

- `shared-projects/firehose-daemon/events.jsonl`
- `shared-projects/intelligence-model/intelligence_store.sqlite` raw tables
- `shared-projects/intelligence_store.sqlite`
- screenshots and OCR outputs under future evidence storage
- raw Polymarket pulls and API responses
- source documents, transcripts, web captures, reports before compilation

### Compiled Knowledge Layer

Derived human-readable or machine-readable knowledge artifacts.

- future `lobster-intel/data/compiled/`
- wiki pages and summaries
- schema files such as `entities.json`, `graph.json`, `tags.json`
- reusable state explanations
- report source syntheses

### Runtime Intelligence Layer

Current operating state, monitor outputs, and evaluative artifacts.

- `shared-projects/intelligence-model/state_config.json`
- `shared-projects/intelligence-model/latest_ngi.json`
- `shared-projects/intelligence-model/last_alert_state.json`
- DQ logic and freshness logic
- state transition logs
- drift reports

### Delivery Layer

Rendered outputs and delivery-specific triggers.

- heartbeat cron job content and handlers
- Gooaye tracker notifications
- morning and evening report delivery
- Telegram message formatting and push behavior

## Current migration candidates

### Move toward `lobster-runtime`
- `shared-projects/intelligence-model/ingest_intelligence.py` (split, ingest pieces may move to `lobster-ingest`)
- `shared-projects/intelligence-model/compute_ngi_fusion.py`
- `shared-projects/intelligence-model/compute_ngi_firehose.py`
- `shared-projects/intelligence-model/run_ngi_monitor.py`

### Move toward `lobster-delivery`
- heartbeat rendering logic
- cron-triggered chat summaries
- Gooaye tracker delivery formatting

### Move toward `lobster-plugins`
- Gooaye tracker as first plugin template
- Firehose geopol monitor
- Polymarket monitor
- TWSE close report hooks

## Known drift hotspots already seen

- old market framing lingering after target changes
- PM2 process status vs health endpoint truth
- current run vs stale historical run confusion
- channel delivery chatter leaking internal execution narration

## Migration rule

Until extraction is complete:
- preserve working behavior first
- move schemas before moving logic
- move runtime contracts before delivery formatting
- pluginize only after the feature has a stable contract
