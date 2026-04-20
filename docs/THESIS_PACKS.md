# Thesis Packs

NGI Lobster is being built as an installable OpenClaw plugin product.

That means the default install path must preserve this flow:

```text
openclaw plugins install -> source ingest plugins -> runtime spine -> auditable artifacts -> downstream delivery
```

Thesis packs exist to make the runtime part of that path install-ready instead of manually wired.

## What a thesis pack is

A thesis pack is a JSON file that gives one thesis its runtime defaults:

- `thesis_id`
- `semantic_frame`
- `probability_direction`
- `state`
- `target_registry`

The runtime uses that pack to resolve the active market target before compare and delivery.

## Discovery order

When you run:

```bash
python3 lobster-intel/scripts/run_thesis_runtime.py --workspace . --thesis-id gooaye
```

the runtime discovers thesis packs in this order:

1. `lobster-intel/data/runtime/thesis-packs/<thesis-id>.json`
2. `lobster-intel/examples/thesis-packs/<thesis-id>.json`

If neither file exists, the runtime still runs, but it has no curated target registry to resolve against unless you pass `--registry-file`.

## Current example

The repo currently ships:

```text
lobster-intel/examples/thesis-packs/gooaye.json
```

That example gives the default `gooaye` workflow:

- a concrete semantic frame
- `ACTIVE_TRUCE` state
- `yes_is_peace` numeric direction
- a curated target registry entry for the June 30 market

## Override rules

Explicit CLI inputs win over pack defaults.

These flags override the pack:

- `--registry-file`
- `--semantic-frame`
- `--probability-direction`
- `--state`

Use this when the installed pack is a baseline but the operator needs a different runtime contract for a specific run.

## Why this exists

The runtime already supported `registry-first` target resolution, but the install-ready path had no default way to discover thesis-specific runtime truth.

That meant an operator could run the thesis runtime with only `--workspace` and `--thesis-id`, yet still fall into a generic or suppressed compare path because the target registry and semantic frame were not loaded.

Thesis packs close that gap without moving truth into delivery code and without bypassing the runtime artifact chain.
