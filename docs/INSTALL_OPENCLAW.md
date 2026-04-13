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

## 8. Current expected local artifacts

The first example plugin currently writes artifacts under:

```text
lobster-intel/data/evidence/
lobster-intel/data/compiled/
lobster-intel/data/runtime/
lobster-intel/data/delivery/
```

## 9. Cron status

There is **not yet** a final reusable cron recipe for outside installs.

Current recommendation:

- first validate `run_once`
- then wire a local cron / OpenClaw cron after confirming paths and outputs
- keep background output behind the delivery gate

## 10. What still needs productization

Before this becomes a smooth installable plugin for everyone, these still need work:

1. linked-content extraction
2. OCR backfill loop
3. Firehose junk suppression / ranking
4. reusable cron recipes
5. a cleaner setup command

## Bottom line

Another OpenClaw can already install this repo and run the first plugin example, but Firehose still requires operator setup and the full product installer does not exist yet.
