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
- native tool `ngi_lobster_run_default_workflow` now runs ingest plus thesis runtime and emits runtime/delivery artifacts
- the heavy NGI runtime is still being migrated from `lobster-intel/` Python code into a fuller native OpenClaw plugin surface

So the install surface is starting to look right, but runtime feature parity is not finished yet.

## Dispatcher acceptance cut shortcut

The current P0 product cut is still the same dispatcher-path acceptance proof. From repo root, run:

```bash
npm run test:dispatcher-cut
```

That one command executes the focused dispatcher acceptance / contract test set against the local `.venv`, so PO can quickly re-check the highest-priority cut before asking for review or upstreaming.

When PO only needs to re-check the live `latest_ngi.json` explain-contract surface before the full dispatcher bundle, use:

```bash
npm run test:latest-ngi-cut
```

That shortcut keeps the active runtime contract blocker on one small, repeatable validation path.

When PO needs to re-check the same-bundle proof for the current highest-priority cut — shared `e2e_run_id`, suppress/pass fixtures, and bundle-level contract verification — use:

```bash
npm run test:e2e-bundle-cut
```

That shortcut keeps the real dispatcher-path evidence bundle on one repeatable acceptance command before review or merge.

When PO needs one fast gate for current live ops health — DQ pass/fail, market snapshot freshness, and same-target NGI divergence from `latest_ngi.json` — use:

```bash
npm run test:ops-health-cut
```

That shortcut keeps the current operational blocker on one repeatable local validation path instead of reassembling ad hoc checks each heartbeat.

## Current state

The repo already contains:

- a minimal plugin contract
n- a plugin loader
- a run-once runtime path
- a delivery gate
- a first ingest plugin example (`gooaye-tracker`)
- legacy NGI scripts kept as migration references

## Current gaps

- Firehose local `events.jsonl` normalization now writes replayable source-run artifacts, but signal filtering still needs work
- live NGI cron still needs to be rebuilt as a product-grade path
- tracked git history, remote sync, and PR flow are still split from this writable workspace
