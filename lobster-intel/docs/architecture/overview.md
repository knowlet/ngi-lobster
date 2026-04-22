# Architecture Overview

## Purpose

Lobster Intel is an intelligence platform for OpenClaw agents and lobster plugins. It exists to make evidence ingestion, knowledge compilation, runtime monitoring, and delivery explicit and maintainable.

## Four-layer model

### 1. Evidence Layer

Purpose: store raw truth without rewriting it.

Examples:
- Firehose event streams
- Polymarket raw pulls
- SQLite raw tables
- screenshots and OCR outputs
- PDFs, notes, transcripts, web captures

Rules:
- evidence is append-only or immutable
- evidence never gets silently rewritten into summaries
- all downstream products must point back to evidence

### 2. Compiled Knowledge Layer

Purpose: turn evidence into readable, queryable knowledge.

Examples:
- wiki pages
- source summaries
- entity graph
- schema files
- reusable judgments

Rules:
- compiled knowledge is derived, not canonical truth
- every important claim needs provenance
- drift with evidence must be detectable

### 3. Runtime Intelligence Layer

Purpose: maintain the current operating state of the system.

Examples:
- `state_config.json`
- `latest_ngi.json`
- `last_alert_state.json`
- freshness and DQ checks
- state transitions
- runtime drift reports

Rules:
- runtime state must be serializable and auditable
- monitor target selection must be explicit
- delivered alerts must be traceable to runtime decisions

### 4. Delivery Layer

Purpose: format and deliver outputs to humans and agents.

Examples:
- heartbeat responses
- cron-driven monitoring
- Telegram notifications
- morning and evening reports
- agent review loop outputs

Rules:
- delivery never owns business truth
- delivery renders runtime decisions, it does not invent them
- channel-specific formatting stays here

## Package boundaries

### `lobster-core`
Schemas, enums, data contracts, config loading, provenance models.

### `lobster-ingest`
Evidence collection and normalization.

### `lobster-compiler`
Wiki generation, schema generation, summaries, drift against evidence.

### `lobster-runtime`
State machine, monitor logic, NGI, DQ, freshness, alert decision engine.
Runtime also owns the analyzer registry that turns evidence artifacts into observation drafts before compare logic runs.
Analyzers may shape observations, but target selection, compare mode, and delivery eligibility remain runtime-owned decisions.

### `lobster-delivery`
Heartbeat rendering, chat formatting, reports, notification adapters.

### `lobster-plugins`
Plugin manifest, hook contracts, loader, capability validation.

## Plugin model

Plugins should attach through explicit hooks, not ad hoc script imports.

Suggested hook families:
- `on_ingest`
- `on_compile`
- `on_runtime_check`
- `on_alert`
- `on_delivery`
- `on_drift`

## Migration strategy

1. stop adding more ad hoc scripts
2. classify existing files into the four layers
3. extract shared schemas into `lobster-core`
4. split runtime logic from delivery
5. pluginize one working feature first, Gooaye tracker

## Anti-patterns to avoid

- giant bridge scripts as the center of truth
- wiki as the only source of truth in fast-moving scenarios
- delivery code mixed with monitoring logic
- mandatory vector infra before clear protocols exist
