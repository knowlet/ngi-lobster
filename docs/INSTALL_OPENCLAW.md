# Install on another OpenClaw

This document explains how another OpenClaw instance can install and run the current NGI / Lobster Intel stack.

This is **v0**. It is honest about what is productized already, and what still needs manual wiring.

## Project goal

The goal of this repo is not only to ship a runnable intelligence script.

The goal is to productize NGI as an installable OpenClaw plugin:

- install through `openclaw plugins install`
- ingest evidence through pluginized source trackers
- compute runtime truth through the NGI runtime spine
- compare against the active market target on the correct semantic frame
- keep delivery downstream of runtime truth

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

- a fully packaged OpenClaw plugin registry entry
- stable OCR backfill
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

## 2.1 Cleaner local commands

The repo now exposes cleaner package-level commands for the current install surface:

```bash
npm run bootstrap-runtime
npm run run-installed-workflow -- --thesis-id regional-escalation
```

Both commands are now self-describing via `--help`.

If you prefer executable bins after package install, these are also exposed:

```bash
ngi-lobster-bootstrap-runtime
ngi-lobster-run-installed-workflow --thesis-id regional-escalation
```

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
2. let NGI read that file

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
- `ngi_lobster_list_installed_theses`
- `ngi_lobster_run_default_workflow`
- `ngi_lobster_run_thesis_runtime`
- `ngi_lobster_run_installed_thesis_workflow`

Their jobs are:

- `ngi_lobster_demo`: smoke-test the local runtime path
- `ngi_lobster_list_installed_theses`: list bundled thesis ids, titles, summaries, and registry paths, or inspect one thesis in detail with `thesisId`
- `ngi_lobster_run_default_workflow`: run the default installed workflow and write artifacts/digest
- `ngi_lobster_run_thesis_runtime`: run the thesis runtime spine against installed source artifacts or explicit overrides
- `ngi_lobster_run_installed_thesis_workflow`: run the bundled or explicit source-pack trackers first, then invoke the thesis runtime spine against the freshly written source artifacts and bundled or explicit thesis defaults

Bundled thesis defaults are resolved from:

- `lobster-intel/examples/thesis-profiles/<thesis-id>.json`
- `lobster-intel/examples/target-registries/<thesis-id>.json`

That means the installed workflow can carry a stable runtime contract for `semantic_frame`, `probability_direction`, `state`, and target registry without requiring those flags on every run.

The bundled thesis profiles can now also expose operator-facing metadata such as:

- `title`
- `summary`
- linked registry path and market list

The install surface now treats those bundled thesis profiles as a contract instead of loose metadata:

- `ngi_lobster_list_installed_theses` exposes `contractStatus` and `validationErrors`
- `ngi_lobster_run_installed_thesis_workflow` fails closed if a thesis profile is missing or incomplete
- the reference contract is documented in `docs/THESIS_PROFILES.md`

That gives an installed OpenClaw a discovery surface before it commits to a thesis run.

Default runtime thesis registries now live under:

- `lobster-intel/data/runtime/thesis-registry/<thesis-id>.json`

`ngi_lobster_run_thesis_runtime` and `run_thesis_runtime.py` discover that file automatically before falling back to a suppressed no-registry run.
If you need a one-off override, pass `registryFilePath` or `--registry-file`; the explicit path still wins.

The installed workflow now also wires default source cursor persistence automatically:

- `lobster-intel/data/runtime/sources/official-statements.json`
- `lobster-intel/data/runtime/sources/watchlist.json`
- `lobster-intel/data/runtime/sources/polymarket.json`

Repeated installed-workflow runs reuse those cursor files without extra `*_STATE_PATH` environment-variable wiring.

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

Per-plugin source runtime directories now also support replay and rebuild under:

```text
lobster-intel/data/runtime/sources/<plugin-id>/latest.json
lobster-intel/data/runtime/sources/<plugin-id>/runs/<run_id>.json
lobster-intel/data/runtime/sources/<plugin-id>/index.sqlite
```

`latest.json` and `runs/*.json` are the truth artifacts. `index.sqlite` is derived state and can be rebuilt from those files with `source_history.py rebuild-index`.

## 9. Cron status

There is now a stable installed-workflow entrypoint for outside installs:

```bash
node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation
```

That command reuses the same bundled source packs, bundled thesis defaults, source cursor paths, and thesis runtime contracts as the native OpenClaw tool surface, but it can be called directly by local cron.

Example cron line:

```cron
*/15 * * * * cd /path/to/ngi-lobster && /usr/bin/env node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation >> lobster-intel/data/runtime/regional-escalation-cron.log 2>&1
```

Current recommendation:

- first run the CLI manually and inspect the JSON result plus artifact paths
- then wire local cron or OpenClaw cron against that stable entrypoint
- keep background output behind the delivery gate

## 10. What still needs productization

Before this becomes a smooth installable plugin for everyone, these still need work:

1. linked-content extraction
2. OCR backfill loop
3. Firehose junk suppression / ranking
4. additional cron recipes beyond the installed thesis workflow
5. broader install packaging beyond the current package commands
## Bottom line

Another OpenClaw can already install this repo and run the first plugin example, but Firehose still requires operator setup and the full product installer does not exist yet.
