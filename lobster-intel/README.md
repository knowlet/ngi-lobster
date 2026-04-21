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
    polymarket-tracker/
    official-statements-tracker/
    watchlist-tracker/
  examples/
    source-packs/
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

## Current source plugin set

The current ingest family is now:

- `gooaye-tracker`
- `polymarket-tracker`
- `official-statements-tracker`
- `watchlist-tracker`

These are intentionally **silent-ingest** plugins. They do not send delivery output themselves.

## Install-ready source pack examples

Example source pack configs now live under:

```text
lobster-intel/examples/source-packs/
```

- `official-statements.json`
- `watchlist.json`
- `polymarket.json`

The product intent is:

- source plugins fetch and normalize evidence
- runtime stores cursor / source state
- delivery remains downstream

## Linked content queue processing

Runtime payloads may carry a `linked_content_queue` for follow-up extraction work. The queue processor reads the latest runtime artifact for a thesis, fetches each linked URL, and writes:

- evidence JSON under `lobster-intel/data/evidence/<thesis-id>/linked-content/`
- compiled markdown under `lobster-intel/data/compiled/<thesis-id>/linked-content/`
- a runtime receipt under `lobster-intel/data/runtime/<thesis-id>/linked-content/`

Run it with:

```bash
./.venv/bin/python lobster-intel/scripts/process_linked_content_queue.py \
  --workspace . \
  --thesis-id gooaye
```

The fetch path is intentionally constrained to `http`/`https`, caps response bodies before decode, strips `script`/`style` noise from HTML text extraction, and parallelizes queue fetches while preserving deterministic artifact writes.

## Visual evidence queue processing

Runtime payloads may also carry an `image_analysis_queue` for downstream OCR or image-understanding work. The visual-evidence processor reads the latest runtime artifact for a thesis and writes:

- evidence JSON under `lobster-intel/data/evidence/<thesis-id>/visual-evidence/`
- compiled markdown under `lobster-intel/data/compiled/<thesis-id>/visual-evidence/`
- a runtime receipt under `lobster-intel/data/runtime/<thesis-id>/visual-evidence/`

Run it with:

```bash
./.venv/bin/python lobster-intel/scripts/process_visual_evidence_queue.py \
  --workspace . \
  --thesis-id gooaye
```

The source ingest step still only declares pending image-analysis work. The downstream worker writes a separate audit trail and fails closed when queued items are missing `image_url` or the OCR adapter errors.

## Dispatcher artifact writing

Runtime payloads can now be materialized into real dispatcher delivery artifacts before PO review or contract verification.

Run it with:

```bash
./.venv/bin/python lobster-intel/scripts/write_dispatcher_artifact.py \
  --workspace . \
  --thesis-id gooaye \
  --runtime-file lobster-intel/data/runtime/gooaye/runs/positive-20260421T000500Z.json \
  --sink openclaw_heartbeat \
  --delivery-status delivered \
  --proof-boundary openclaw_heartbeat \
  --proof-id heartbeat:positive-20260421T000500Z
```

This writes `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json` for any dispatcher decision, and writes `receipts/<run-id>.json` only when the decision is `would_send`. The receipt path fails closed unless `delivery_proof.boundary` and a canonical `proof_id` can be reconstructed.

## Dispatcher E2E bundle building

Delivery alert artifacts can be grouped into one auditable dispatcher review bundle when PO needs the suppressed legacy control and the delivered positive control under the same shared `e2e_run_id`.

Run it with:

```bash
./.venv/bin/python lobster-intel/scripts/build_dispatcher_e2e_bundle.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260421-01 \
  --run-id legacy-20260421T000000Z \
  --run-id positive-20260421T000500Z
```

This reads `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json`, verifies the contract bundle fail-closed, and writes one machine-readable artifact under `lobster-intel/data/delivery/<thesis-id>/bundles/`.
When the alert artifacts came directly from `runtime_spine`, the builder also reads the matching `runtime`, `compare`, and optional `receipt` artifacts so the shared bundle can be reconstructed without hand-editing an `alert_disposition` wrapper first.

## Dispatcher acceptance CLI

When operators already know the suppressed legacy-control run id and the positive-control run id, one higher-level CLI can materialize both dispatcher artifacts and the shared review bundle in one step.

```bash
./.venv/bin/python lobster-intel/scripts/run_dispatcher_acceptance.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260421-operator \
  --suppressed-run-id legacy-20260421T000000Z \
  --positive-run-id positive-20260421T000500Z \
  --sink openclaw_heartbeat \
  --delivery-status delivered \
  --proof-boundary openclaw_heartbeat \
  --proof-id heartbeat:positive-20260421T000500Z
```

This reads the matching `runtime/runs/<run-id>.json` artifacts, emits the dispatcher alert/receipt records under `lobster-intel/data/delivery/<thesis-id>/`, then writes the shared bundle artifact under `bundles/` and prints one machine-readable summary for operator review.

## Source history operations

Runtime source artifacts under `lobster-intel/data/runtime/sources/<plugin-id>/runs/` are now replayable and indexable.

Use the helper CLI to inspect one historical run:

```bash
./.venv/bin/python lobster-intel/scripts/source_history.py replay \
  --workspace . \
  --plugin-id watchlist-tracker \
  --run-id 20260420T010000Z
```

Use the same CLI to rebuild a per-plugin SQLite index from the immutable run artifacts:

```bash
./.venv/bin/python lobster-intel/scripts/source_history.py rebuild-index \
  --workspace . \
  --plugin-id watchlist-tracker
```

This keeps runtime truth in JSON artifacts while giving operators a fast local query surface.
