# Lobster Intel

A maintainable intelligence platform for OpenClaw agents.

## What this is

Lobster Intel turns messy scripts and one-off fixes into a real system:
- immutable evidence ingestion
- compiled knowledge and schema
- runtime monitoring and state
- delivery through heartbeat, cron, and chat
- plugin hooks for other lobster agents

## Installation

If you want to run this on another OpenClaw instance, start with:

- `../docs/INSTALL_OPENCLAW.md`
- `../.env.example`

That guide explains current v0 setup, package paths, Firehose expectations, and what is still manual.

## Product goal

Build an intelligence operating system that is:
- maintainable
- auditable
- documented
- installable
- extensible by plugins

## Architecture

Lobster Intel is split into four operational layers:

1. **Evidence Layer**
   - raw documents
   - screenshots
   - Firehose events
   - market snapshots
   - transcripts
   - source captures

2. **Compiled Knowledge Layer**
   - wiki pages
   - summaries
   - entity graph
   - source mappings
   - reusable judgments

3. **Runtime Intelligence Layer**
   - current state
   - target selection
   - NGI / DQ / freshness
   - alerts
   - drift reports
   - state transitions

4. **Delivery Layer**
   - heartbeat
   - cron
   - Telegram push
   - recurring reports
   - agent review loop

## Package layout

```text
lobster-intel/
  docs/
  packages/
    lobster-core/
    lobster-ingest/
    lobster-compiler/
    lobster-runtime/
    lobster-delivery/
    lobster-plugins/
  plugins/
    gooaye-tracker/
  data/
    evidence/
    compiled/
    runtime/
    delivery/
```

## Milestone 1: lobster-intel-foundation

This milestone establishes:
- project naming and boundaries
- core documentation
- architecture and protocol docs
- first ADR
- first plugin scaffold
- base package skeleton

## Design principles

- Evidence is immutable.
- Compiled knowledge is not raw truth.
- Runtime state must be auditable.
- Delivery must stay separate from core logic.
- Plugins must declare capabilities and outputs.
- Semantic memory is optional, not foundational.

## Near-term plan

1. freeze and classify existing files into evidence / compiled / runtime / delivery
2. formalize state, alert, drift, and evidence schemas in `lobster-core`
3. separate runtime logic from delivery logic
4. convert Gooaye tracker into the first plugin example

## Status

Foundation scaffold created. Migration in progress.
