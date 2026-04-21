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
    thesis-packs/
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
lobster-intel/examples/thesis-packs/
lobster-intel/examples/thesis-profiles/
lobster-intel/examples/target-registries/
```

These fixtures let the installed OpenClaw workflow resolve thesis-specific runtime defaults without moving decision logic into delivery code.
The native OpenClaw wrapper can now expose those bundled thesis profiles as an install-time catalog, including human-readable `title` / `summary` metadata plus linked registry inspection.
That catalog now also reports `contractStatus` and `validationErrors`, and the installed thesis workflow fails closed when a profile is missing required runtime defaults or per-source config declarations.

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

When the Python runtime is invoked directly with only `--workspace` and `--thesis-id`, it can also discover install-ready thesis packs from `lobster-intel/examples/thesis-packs/` and use them to recover runtime defaults plus bundled registry entries.

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

Each rebuild invocation closes its SQLite handle before returning, so repeated automation runs can refresh the index without leaving descriptor cleanup to process shutdown.

This keeps replayability and lineage in the runtime layer while leaving delivery downstream of the same artifact truth.

## Linked-content queue processing

Gooaye runtime artifacts can now expose `linked_content_queue` as downstream runtime work instead of forcing the source tracker to fetch articles or transcripts inline.

Operators can process the current queue from the latest runtime artifact:

```bash
python3 lobster-intel/scripts/process_linked_content_queue.py --workspace . --thesis-id gooaye
```

Or they can point the worker at a prior runtime snapshot for backfill:

```bash
python3 lobster-intel/scripts/process_linked_content_queue.py --workspace . --thesis-id gooaye --runtime-file lobster-intel/data/runtime/gooaye/runs/<run-id>.json
```

That worker writes:

- evidence artifacts under `lobster-intel/data/evidence/<thesis_id>/linked-content/`
- compiled markdown under `lobster-intel/data/compiled/<thesis_id>/linked-content/`
- runtime receipts under `lobster-intel/data/runtime/<thesis_id>/linked-content/`

The fetch path is intentionally constrained to `http`/`https`, caps response bodies before decode, strips `script`/`style` noise from HTML text extraction, and parallelizes queue fetches while preserving deterministic artifact writes.

This keeps the tracker ingest-only while making linked-content follow-up replayable and auditable from runtime truth.

## Dispatcher acceptance bundle

When operators already know the suppressed legacy-control run id and the positive-control run id that should compose the current P0 acceptance cut, materialize the dispatcher artifacts plus one shared E2E bundle in one command:

```bash
python3 lobster-intel/scripts/run_dispatcher_acceptance.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260422-acceptance \
  --suppressed-run-id legacy-20260421T000000Z \
  --positive-run-id positive-20260421T000500Z
```

The wrapper reuses `delivery/receipts/<positive-run-id>.json` by default, preflights the shared contract bundle in memory, then writes dispatcher alert/receipt artifacts and emits one shared bundle under `lobster-intel/data/delivery/<thesis-id>/bundles/`.

Receipt reuse fails closed when the persisted receipt metadata is incomplete or no longer matches the requested positive-control run. The current guard requires `thesis_id`, `run_id`, and `contract_version` before reusing the delivery proof.
