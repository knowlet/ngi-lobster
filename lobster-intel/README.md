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

NGI Lobster exists to turn the current NGI workflow into an installable OpenClaw plugin product.

That means:
- `openclaw plugins install` is the primary install surface
- runtime artifacts under `lobster-intel/data/` are live runtime truth
- source plugins ingest and normalize evidence
- runtime computes thesis state, target resolution, compare mode, and alert decisions
- delivery stays downstream of runtime truth

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
    polymarket-tracker/
    official-statements-tracker/
    watchlist-tracker/
  examples/
    source-packs/
    thesis-profiles/
    target-registries/
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
- Plugins must declare capabilities, tracker contracts, and outputs.
- Semantic memory is optional, not foundational.

## Near-term plan

1. freeze and classify existing files into evidence / compiled / runtime / delivery
2. formalize state, alert, drift, and evidence schemas in `lobster-core`
3. separate runtime logic from delivery logic
4. convert Gooaye tracker into the first plugin example

## Status

Foundation scaffold created. Migration in progress.

## Current source plugin set

The current ingest family is now:

- `gooaye-tracker`
- `polymarket-tracker`
- `official-statements-tracker`
- `watchlist-tracker`

These are intentionally **silent-ingest** plugins. They do not send delivery output themselves.

Each ingest manifest now separates:

- `capabilities`: host-facing dependency hints such as `web_fetch`, `ocr`, `image_understanding`
- `tracker`: Lobster-owned source contract for source family, replayability, cursor state mode, and follow-up runtime queues

That keeps plugin onboarding and follow-up processing machine-readable without moving decision logic into delivery code.

## Install-ready source pack examples

Example source pack configs now live under:

```text
lobster-intel/examples/source-packs/
```

- `official-statements.json`
- `watchlist.json`
- `polymarket.json`

Bundled thesis defaults now also live under:

```text
lobster-intel/examples/thesis-profiles/
lobster-intel/examples/target-registries/
```

These fixtures let the installed OpenClaw workflow resolve thesis-specific runtime defaults without moving decision logic into delivery code.
The native OpenClaw wrapper can now expose those bundled thesis profiles as an install-time catalog, including human-readable `title` / `summary` metadata plus linked registry inspection.

Default runtime thesis registries now also live under:

```text
lobster-intel/data/runtime/thesis-registry/
```

That lets `run_thesis_runtime` discover a thesis-owned registry contract automatically from runtime data before relying on explicit override flags.

The installed workflow also auto-wires source cursor persistence into:

- `lobster-intel/data/runtime/sources/official-statements.json`
- `lobster-intel/data/runtime/sources/watchlist.json`
- `lobster-intel/data/runtime/sources/polymarket.json`

That keeps repeated installed runs replayable and auditable without pushing cursor logic into delivery code or relying on ad hoc host env wiring.

The product intent is:

- source plugins fetch and normalize evidence
- runtime stores cursor / source state
- delivery remains downstream

## Source replay and index rebuild

Per-plugin runtime artifacts under `lobster-intel/data/runtime/sources/<plugin-id>/` are now intended to be auditable runtime truth, not disposable cache.

Operators can inspect a historical run directly from disk:

```bash
python3 lobster-intel/scripts/source_history.py replay --workspace . --plugin-id watchlist-tracker --run-id 20260415T013020Z
```

They can also rebuild a local SQLite index from `runs/*.json` without rerunning the source plugin:

```bash
python3 lobster-intel/scripts/source_history.py rebuild-index --workspace . --plugin-id watchlist-tracker
```

This keeps replayability and lineage in the runtime layer while leaving delivery downstream of the same artifact truth.
