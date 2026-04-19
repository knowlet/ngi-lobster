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
- native tool `ngi_lobster_list_installed_theses` exists to list bundled thesis ids, profile defaults, and linked registry paths
- native tool `ngi_lobster_run_installed_thesis_workflow` exists to run bundled source packs and then the thesis runtime spine
- `lobster-intel/examples/thesis-packs/gooaye.json` exists for install-ready thesis defaults
- bundled thesis defaults also live under `lobster-intel/examples/thesis-profiles/` and `lobster-intel/examples/target-registries/`
- the heavy NGI runtime is still being migrated from `lobster-intel/` Python code into a fuller native OpenClaw plugin surface

So the install surface is starting to look right, but runtime feature parity is not finished yet.

## Current state

The repo already contains:

- a minimal plugin contract
- a plugin loader
- a run-once runtime path
- a delivery gate
- a first ingest plugin example (`gooaye-tracker`)
- an install-ready thesis pack example for runtime target resolution
- legacy NGI scripts kept as migration references

## Current gaps

- linked-content extraction is still incomplete
- OCR backfill is still incomplete
- Firehose signal filtering still needs work
- live NGI cron still needs to be rebuilt as a product-grade path

## Install-ready runtime defaults

Default thesis runtime resolution now has an install-ready config surface:

- source tracker packs live under `lobster-intel/examples/source-packs/`
- thesis runtime packs live under `lobster-intel/examples/thesis-packs/`

When you run the default workflow or `lobster-intel/scripts/run_thesis_runtime.py` with only `--workspace` and `--thesis-id`, the runtime discovers installed source artifacts plus the matching thesis pack and uses that pack to load:

- semantic frame
- probability direction
- runtime state
- curated target registry entries

Operational details live in [docs/THESIS_PACKS.md](docs/THESIS_PACKS.md).
