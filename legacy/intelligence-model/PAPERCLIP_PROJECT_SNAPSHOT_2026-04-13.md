# Project Snapshot — NGI / Lobster Intel (2026-04-13)

## Goal
Build an intelligence engine that finds information-gap signals, the kind of thing that behaves like a new Pentagon Pizza Index: public, non-consensus, hard to fake, and early.

## Current product direction
This project is being pushed toward productization, not one-off research.

Core product layers:
1. **Signal thesis layer** — what kinds of hidden signals we are hunting
2. **Source / ingestion layer** — where those signals enter the system
3. **Evidence chain** — raw artifact -> structured extraction -> runtime state -> delivery
4. **Decision layer** — NGI / fusion / monitor logic
5. **Automation layer** — skill ownership, cron, monitoring, review loop

## Current thesis buckets
- 區域微觀消費與活動
- 實體後勤與異常位移
- 枯燥採購與招募激增
- 數位基礎設施暗流
- 邊緣衍生品與聰明錢
- 決策圈數位排泄物

## Current source buckets
- Channel Post
- Stream Event
- Market Feed
- Mobility / Physical OSINT Feed
- Linked Content
- Visual Evidence
- Document Corpus

## What already works
### 1. Gooaye ingestion pipeline
- public Telegram channel posts are tracked
- artifacts are written to:
  - `lobster-intel/data/evidence/gooaye/`
  - `lobster-intel/data/compiled/gooaye/`
  - `lobster-intel/data/runtime/gooaye/`
  - `lobster-intel/data/delivery/gooaye/`
- media posts are explicitly marked with image-analysis queue state

### 2. NGI runtime foundations
- core decision loop has started moving into `lobster-runtime`
- legacy scripts are being wrapped instead of remaining the only source of truth

### 3. Manual signal ingestion proof
- Gooaye post `#6060` commodity board was manually extracted and written into `intelligence_store.sqlite`
- inserted as `first_principles_snapshots`
- topic: `iran_conflict`
- signal type: `energy`
- metrics included WTI, Brent, Murban, Natural Gas, Gasoline, Heating Oil, and a crude-oil escalation proxy

## Critical gaps
1. **Linked Content** is not yet reliably extracting full article / transcript content
2. **Visual Evidence** still lacks a stable OCR -> structured evidence -> runtime roundtrip
3. **Document Corpus** ingestion is basically missing
4. **NGI cron** is not currently product-grade
   - historical runs exist
   - live cron job disappeared from current cron store
   - earlier periods delivered, later periods became unstable, then the job vanished from live config

## Current artifacts
- `shared-projects/intelligence-model/NGI_SIGNAL_MAP_PROTOTYPE.md`
- `shared-projects/intelligence-model/latest_ngi.json`
- `shared-projects/intelligence-model/run_ngi_monitor.py`
- `lobster-intel/packages/lobster-runtime/`
- `scripts/process_gooaye_channel.py`

## Immediate next step
Run prototype validation on 5 real source types:
1. Gooaye (Channel Post)
2. Firehose conflict stream (Stream Event)
3. Polymarket / crude proxy (Market Feed)
4. Linked article / YouTube transcript (Linked Content)
5. Screenshot / table extraction (Visual Evidence)

Goal of that prototype:
- prove which sources generate real information-gap signals
- separate signal from noise
- decide what deserves skill + cron productization
