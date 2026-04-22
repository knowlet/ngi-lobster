# ngi-lobster

A cleaned private repo for the current NGI + Lobster Intel productization effort.

## Goal

Turn the current NGI workflow into an installable, open-source-friendly plugin system for OpenClaw-style agents.

This repo is not just research notes. It is the productization track.

## Repo layout

- `lobster-intel/`: plugin-oriented intelligence platform scaffold
- `legacy/intelligence-model/`: current NGI workflow code and reference artifacts being migrated into the plugin/runtime architecture

## What is intentionally excluded

- local databases
- logs
- venvs
- secrets / tokens
- personal memory files
- runtime state dumps

## Start here

- Product / plugin architecture: `lobster-intel/README.md`
- OpenClaw install + config guide: `docs/INSTALL_OPENCLAW.md`
- Product cut: `docs/PRODUCT_CUT_V0.md`
- Thesis profile contract: `docs/THESIS_PROFILES.md`
- Example environment variables: `.env.example`

## Native OpenClaw install surface

This repo now includes a **native OpenClaw plugin wrapper** so the install path can converge on:

```bash
openclaw plugins install ./path/to/ngi-lobster
```

Current status:

- `openclaw.plugin.json` exists
- `package.json` exists
- `index.js` native wrapper entry exists
- native tool `ngi_lobster_demo` exists for local smoke testing
- native tool `ngi_lobster_list_installed_theses` exists to inspect bundled thesis ids, titles, linked registry defaults, and contract health before running them
- native tool `ngi_lobster_run_installed_thesis_workflow` exists to run bundled source packs and then the thesis runtime spine, but now fails closed when the thesis profile contract is incomplete
- stable CLI `node scripts/run_installed_thesis_workflow.js --thesis-id <id>` exists for outside installs and cron jobs
- package-level helper commands now exist: `npm run bootstrap-runtime` and `npm run run-installed-workflow -- --thesis-id <id>`
- `lobster-intel/examples/thesis-packs/gooaye.json` exists for install-ready runtime defaults when the Python thesis runtime is called directly
- bundled thesis defaults now live under `lobster-intel/examples/thesis-profiles/` and `lobster-intel/examples/target-registries/`
- bundled thesis profiles now act as install-surface contracts, including source config paths and runtime defaults
- bundled thesis profiles now carry human-readable titles and summaries for operator discovery
- installed thesis catalog entries now expose `contractStatus` and `validationErrors`
- thesis runtime registry discovery now defaults to `lobster-intel/data/runtime/thesis-registry/<thesis_id>.json`
- installed source trackers now persist cursor state by default under `lobster-intel/data/runtime/sources/*.json`
- the heavy NGI runtime is still being migrated from `lobster-intel/` Python code into a fuller native OpenClaw plugin surface

So the install surface is starting to look right, but runtime feature parity is not finished yet.

## Current state

The repo already contains:

- a minimal plugin contract
- a plugin loader
- a run-once runtime path
- a thesis runtime spine with registry-first target resolution
- a delivery gate
- a first ingest plugin example (`gooaye-tracker`)
- an install-ready thesis pack example for direct runtime resolution
- legacy NGI scripts kept as migration references

## Current gaps

- linked-content queue processing now writes replayable artifacts, but richer transcript/article extraction is still incomplete
- OCR backfill is still incomplete
- Firehose signal filtering still needs work
- live NGI cron still needs to be rebuilt as a product-grade path

## Install-ready runtime defaults

Default thesis runtime resolution now has an install-ready config surface:

- source tracker packs live under `lobster-intel/examples/source-packs/`
- thesis runtime packs live under `lobster-intel/examples/thesis-packs/`

When you run `lobster-intel/scripts/run_thesis_runtime.py` with only `--workspace` and `--thesis-id`, the runtime can discover the matching thesis pack and use it to load:

- semantic frame
- probability direction
- runtime state
- curated target registry entries

If no explicit or bundled registry entry matches, runtime may still promote a discovered market candidate as `live_search_fallback` when that candidate already matches the requested semantic frame and probability direction.
That fallback remains runtime-owned truth recorded in artifacts, and compare stays `degraded_compare` until a curated registry entry exists.

Operational details live in `docs/THESIS_PACKS.md`.

## Verification paths

The repo now exposes two fail-closed verification paths for runtime truth:

- `python3 lobster-intel/scripts/verify_alert_contract_bundle.py ...` validates curated review fixtures or shared E2E bundle files
- `python3 lobster-intel/scripts/verify_runtime_contract_bundle.py --workspace . --thesis-id <id> --run-id <run_id>` validates one real runtime run directly from `lobster-intel/data/runtime/` and `lobster-intel/data/delivery/`

Downstream reports, dispatchers, and review tooling must consume those runtime artifacts as the source of truth. If target identity, compare mode, receipt lineage, or delivery proof is missing, the verifier and any consumer should fail closed instead of inventing replacement fields in delivery-only code.
