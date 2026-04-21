# Install on another OpenClaw

This document explains how another OpenClaw instance can install and run the current NGI / Lobster Intel stack.

This is **v0**. It is honest about what is productized already, and what still needs manual wiring.

## What you get today

If you install this repo today, you get:

- Lobster Intel package skeleton
- minimal plugin contract
- minimal plugin loader
- minimal one-shot runtime
- delivery gate for background output
- first source plugin example: `gooaye-tracker`
- legacy NGI scripts for reference and migration

What you do **not** get yet:

- a polished one-command installer
- a fully packaged OpenClaw plugin registry entry
- stable linked-content transcript/article extraction
- final cron templates for every workflow

## 1. Clone the repo

```bash
git clone https://github.com/knowlet/ngi-lobster.git
cd ngi-lobster
```

If the repo is private, use the owner-approved account or token.

## 2. Python requirement

- Python `>= 3.11`

## 3. Recommended layout on the host

Example:

```text
~/.openclaw/
  workspace/
    projects/
      ngi-lobster/
```

This guide assumes the repo lives at:

```text
~/.openclaw/workspace/projects/ngi-lobster
```

## 4. Environment variables

Copy `.env.example` to your local `.env` or export variables in your shell.

### Firehose

Current code paths use **local Firehose event files**, not direct runtime API calls.

That means there are two layers:

1. **Firehose credentials** used by your external ingestion daemon / setup scripts
2. **A local `events.jsonl` file** consumed by NGI logic

Current legacy code expects the events file at:

```text
~/.openclaw/workspace/shared-projects/firehose-daemon/events.jsonl
```

If you want Firehose-backed NGI on another machine, you need to provide:

- `FIREHOSE_TAP_TOKEN` for your Firehose streaming / tap access
- optionally `FIREHOSE_MANAGEMENT_KEY` if you also manage rules programmatically

### Where to put Firehose keys

For now, the safest practical place is your local shell env or a private `.env` file that is **not committed**.

Example:

```bash
export FIREHOSE_TAP_TOKEN="fh_xxx"
export FIREHOSE_MANAGEMENT_KEY="fhm_xxx"
```

or in a private `.env`:

```dotenv
FIREHOSE_TAP_TOKEN=fh_xxx
FIREHOSE_MANAGEMENT_KEY=fhm_xxx
```

### What the code currently reads

- `scripts/firehose-setup.sh` checks `FIREHOSE_TAP_TOKEN`
- legacy NGI code reads the **local Firehose event file**
- it does **not** yet directly read Firehose credentials inside the main runtime path

So the real requirement today is:

1. get Firehose data streaming into `events.jsonl`
2. normalize that file into replayable source artifacts when you want Lobster-owned audit trails
3. let NGI read that file

You can now normalize one local Firehose snapshot into the same `lobster-intel/data/runtime/sources/` artifact shape used by source replay tooling:

```bash
python3 lobster-intel/scripts/normalize_firehose_events.py \
  --workspace . \
  --input-file ~/.openclaw/workspace/shared-projects/firehose-daemon/events.jsonl \
  --run-id 20260422T000000Z
```

Use a simple slash-free `run_id` such as `20260422T000000Z`; path separators and traversal fragments are rejected before artifacts are written.

That command writes:

- `lobster-intel/data/runtime/sources/firehose-tracker/runs/<run_id>.json`
- `lobster-intel/data/runtime/sources/firehose-tracker/latest.json`
- `lobster-intel/data/runtime/sources/firehose-tracker/state.json`

This is a normalization + replay bridge only. It does not yet replace Firehose ranking, filtering, or direct runtime ingestion.

When you build source-fusion artifacts, `lobster-intel/scripts/build_source_fusion.py` now reads `lobster-intel/data/runtime/sources/firehose-tracker/latest.json` by default so the saved fusion summary includes the analyzed Firehose event count, the normalized `firehose.source_run_id`, plus `firehose.latest_event_at_utc` and `firehose.latest_collected_at_utc` for auditability. It still does not promote Firehose into the ranking/filtering decision path by itself.

If you need to rebuild fusion output against a specific historical Firehose normalization run instead of the current `latest.json`, point the CLI at the workspace root and the historical `run_id`:

```bash
python3 lobster-intel/scripts/build_source_fusion.py \
  --workspace . \
  --firehose-run-id 20260423T030500Z \
  --output lobster-intel/data/runtime/fusion/firehose-20260423T030500Z.json
```

That replay path reuses `lobster-intel/data/runtime/sources/firehose-tracker/runs/<run_id>.json` and preserves the historical `firehose.source_run_id` plus latest Firehose timestamps inside the saved fusion artifact.

## 5. Python path for local package imports

Current v0 package loading can be tested with:

```bash
export PYTHONPATH="$PWD/lobster-intel/packages/lobster-core:$PWD/lobster-intel/packages/lobster-plugins:$PWD/lobster-intel/packages/lobster-runtime:$PWD/lobster-intel/packages/lobster-delivery"
```

## 6. Run the plugin once

Example:

```bash
python3 - <<'PY'
from lobster_runtime.run_once import run_plugin_once

result = run_plugin_once(
    'lobster-intel/plugins/gooaye-tracker',
    '.'
)
print(result)
PY
```

This should load the plugin manifest, resolve the entrypoint, and run one ingest cycle.

Or use the repo's demo script:

```bash
./scripts/demo_run_gooaye.sh
```

That is the current fastest smoke test for "is this actually runnable locally?"

## 7. OpenClaw-specific notes

For OpenClaw integration, keep the boundary clean:

- plugin extracts and normalizes data
- runtime decides what to do with it
- delivery is downstream

Do **not** let the plugin itself send Telegram / Discord / chat messages.

## 7.1 Native OpenClaw wrapper test

After installing the repo as a native OpenClaw plugin:

```bash
openclaw plugins install ./path/to/ngi-lobster
openclaw gateway restart
openclaw plugins inspect ngi-lobster
```

Current v0 wrapper also exposes a minimal tool:

- `ngi_lobster_demo`
- `ngi_lobster_run_default_workflow`

Their jobs are:

- `ngi_lobster_demo`: smoke-test the local runtime path
- `ngi_lobster_run_default_workflow`: run the default installed workflow, preserve the generated digest surface, execute the thesis runtime spine, and write runtime plus delivery artifacts

## 7.2 First batch source trackers

The repo now includes these installable ingest plugins:

- `gooaye-tracker`
- `polymarket-tracker`
- `official-statements-tracker`
- `watchlist-tracker`

Example config packs live under:

```text
lobster-intel/examples/source-packs/
```

Use them as the starting point for environment or runtime config wiring.

### Example env wiring

```bash
export OFFICIAL_STATEMENTS_FEEDS_JSON="$(cat lobster-intel/examples/source-packs/official-statements.json)"
export WATCHLIST_FEEDS_JSON="$(cat lobster-intel/examples/source-packs/watchlist.json)"
export POLYMARKET_MARKETS_JSON="$(cat lobster-intel/examples/source-packs/polymarket.json)"
export OFFICIAL_STATEMENTS_STATE_PATH="$PWD/lobster-intel/data/runtime/sources/official-statements.json"
export WATCHLIST_STATE_PATH="$PWD/lobster-intel/data/runtime/sources/watchlist.json"
export POLYMARKET_STATE_PATH="$PWD/lobster-intel/data/runtime/sources/polymarket.json"
```

These trackers are still **silent-ingest only**. They are source plugins, not alerting systems.

`official-statements-tracker` now supports cursor persistence via `OFFICIAL_STATEMENTS_STATE_PATH`.
`watchlist-tracker` and `polymarket-tracker` now support the same pattern via their respective `*_STATE_PATH` variables.

## 8. Current expected local artifacts

The first example plugin currently writes artifacts under:

```text
lobster-intel/data/evidence/
lobster-intel/data/compiled/
lobster-intel/data/runtime/
lobster-intel/data/delivery/
```

Per-plugin source runs should accumulate under:

```text
lobster-intel/data/runtime/sources/<plugin-id>/runs/
```

The default installed workflow now chains source ingest into thesis runtime evaluation, so a successful run should also refresh:

- `lobster-intel/data/runtime/<thesis-id>/latest.json`
- `lobster-intel/data/runtime/<thesis-id>/runs/<run-id>.json`
- `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json`
- `lobster-intel/data/delivery/<thesis-id>/receipts/<run-id>.json`

You can replay a historical source run as JSON:

```bash
./.venv/bin/python lobster-intel/scripts/source_history.py replay \
  --workspace . \
  --plugin-id watchlist-tracker \
  --run-id 20260420T010000Z
```

You can also rebuild a local SQLite index from those immutable run artifacts:

```bash
./.venv/bin/python lobster-intel/scripts/source_history.py rebuild-index \
  --workspace . \
  --plugin-id watchlist-tracker
```

For Gooaye image follow-up work, process the queued OCR / image-understanding items from the runtime artifact:

```bash
./.venv/bin/python lobster-intel/scripts/process_visual_evidence_queue.py \
  --workspace . \
  --thesis-id gooaye
```

This consumes `image_analysis_queue` from `lobster-intel/data/runtime/<thesis-id>/latest.json` and writes separate evidence, compiled markdown, and runtime receipt artifacts. Missing `image_url` values or OCR adapter errors are recorded in the artifact payload instead of silently mutating the source ingest record.

When you need to backfill historical queued image work instead of only the latest runtime artifact, run:

```bash
./.venv/bin/python lobster-intel/scripts/backfill_visual_evidence_queue.py \
  --workspace . \
  --thesis-id gooaye
```

That command scans `lobster-intel/data/runtime/<thesis-id>/runs/*.json`, skips runs that already have a matching visual-evidence receipt under `runtime/<thesis-id>/visual-evidence/runs/`, skips empty queues, and prints one machine-readable backlog summary.

When a runtime artifact exposes `linked_content_queue`, keep the fetch/extraction step downstream of the source plugin:

```bash
./.venv/bin/python lobster-intel/scripts/process_linked_content_queue.py \
  --workspace . \
  --thesis-id gooaye
```

That command reads `lobster-intel/data/runtime/<thesis-id>/latest.json` by default, processes queued linked items, and writes replayable artifacts under:

- `lobster-intel/data/evidence/<thesis-id>/linked-content/`
- `lobster-intel/data/compiled/<thesis-id>/linked-content/`
- `lobster-intel/data/runtime/<thesis-id>/linked-content/`

The runtime worker only fetches `http`/`https` targets, strips `script`/`style` noise from HTML text extraction, caps response size before decode, and can fetch queued items in parallel without changing artifact lineage.

When you need to backfill historical linked-content extraction work instead of only the latest runtime artifact, run:

```bash
./.venv/bin/python lobster-intel/scripts/backfill_linked_content_queue.py \
  --workspace . \
  --thesis-id gooaye
```

That command scans `lobster-intel/data/runtime/<thesis-id>/runs/*.json`, skips runs that already have a matching linked-content receipt under `runtime/<thesis-id>/linked-content/runs/`, skips empty queues, and prints one machine-readable backlog summary.

When you need to verify a real thesis delivery contract from workspace artifacts instead of example fixtures:

```bash
./.venv/bin/python lobster-intel/scripts/verify_runtime_contract_bundle.py \
  --workspace . \
  --thesis-id gooaye \
  --run-id 20260419T123000Z
```

That command reads:
- `lobster-intel/data/runtime/<thesis-id>/runs/<run-id>.json`
- `lobster-intel/data/runtime/<thesis-id>/compare/<run-id>.json`
- `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json`
- `lobster-intel/data/delivery/<thesis-id>/receipts/<run-id>.json`

and fails closed if any required contract field or receipt proof is missing.

When you already know the suppressed runtime run and the positive-control runtime run that should compose the current P0 acceptance bundle, materialize the full dispatcher path in one command:

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

That wrapper reads both `runtime/runs/<run-id>.json` artifacts, writes the suppressed dispatcher alert, writes the positive-control dispatcher alert plus receipt using the supplied delivery proof, records `target_contract_match` beside the dispatcher-visible target ids, then emits one shared dispatcher bundle under `lobster-intel/data/delivery/<thesis-id>/bundles/<bundle-id>.json`.

To verify the persisted bundle artifact directly after that run, point the contract verifier at the generated bundle file:

```bash
./.venv/bin/python lobster-intel/scripts/verify_alert_contract_bundle.py \
  lobster-intel/data/delivery/gooaye/bundles/bundle-20260421-operator.json
```

That verifier accepts either raw payload fixtures or the saved `dispatcher_e2e_bundle.v1` artifact, so operators can re-check the shared `e2e_run_id`, decisions, `target_contract_match`, and delivery proof without unpacking the bundle by hand.

When PO needs to confirm an already-reviewed run still points at the same active runtime target as the current contract in `latest.json`, audit that run directly:

```bash
./.venv/bin/python lobster-intel/scripts/verify_runtime_target_audit.py \
  --workspace . \
  --thesis-id gooaye \
  --run-id 20260419T123000Z
```

That command reads `lobster-intel/data/runtime/<thesis-id>/latest.json` as the current source of truth, compares it against the audited `runtime/runs/<run-id>.json` and `runtime/compare/<run-id>.json`, and exits non-zero if `compare.runtime_target_id` no longer matches the latest active target. Suppressed legacy fixtures may still keep a divergent `market_target_id`, but the runtime-facing target id must remain aligned with the latest contract.

## 8.2 Dispatcher acceptance cut

When you already know the suppressed runtime run and the positive-control runtime run that should compose the current dispatcher acceptance cut, materialize the full dispatcher path in one command:

```bash
python3 lobster-intel/scripts/run_dispatcher_acceptance.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260422-acceptance \
  --suppressed-run-id legacy-20260421T000000Z \
  --positive-run-id positive-20260421T000500Z
```

That wrapper reads both runtime artifacts, reuses the persisted positive-control receipt by default, writes dispatcher alert/receipt artifacts, and emits one shared bundle under `lobster-intel/data/delivery/<thesis-id>/bundles/`.

Receipt reuse now fails closed unless the persisted receipt still matches the requested positive run on `thesis_id`, `run_id`, and `contract_version`.

## 9. Cron status

There is **not yet** a final reusable cron recipe for outside installs.

Current recommendation:

- first validate `run_once`
- then wire a local cron / OpenClaw cron after confirming paths and outputs
- keep background output behind the delivery gate

## 10. What still needs productization

Before this becomes a smooth installable plugin for everyone, these still need work:

1. linked-content extraction
2. Firehose junk suppression / ranking
3. reusable cron recipes
4. a cleaner setup command
5. source cursor persistence wired into default runtime storage

## Bottom line

Another OpenClaw can already install this repo and run the first plugin example, but Firehose still requires operator setup and the full product installer does not exist yet.
