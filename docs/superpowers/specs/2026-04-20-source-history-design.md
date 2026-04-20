# Source History And Replay Design

Date: 2026-04-20

## Context

NGI Lobster's current per-source runtime path writes durable artifacts under `lobster-intel/data/runtime/sources/<plugin-id>/`, but Phase 2 of the roadmap still has a gap: there is no generic way to replay a past source run or rebuild a source-level index from those files.

That gap matters because the product goal is still:

```text
openclaw plugins install -> source ingest plugins -> runtime spine -> auditable artifacts -> downstream delivery
```

If source artifacts are the truth contract, then source history must be inspectable and rebuildable without rerunning the plugin or trusting a side index.

## Problem

Today each source plugin run writes:

- `latest.json`
- `runs/<run_id>.json`

Those files are useful, but the runtime has no shared helper for:

- loading a historical run by `plugin_id` + `run_id`
- replaying the evidence payload into a stable machine-readable summary
- rebuilding a local SQLite index from `runs/*.json`

That leaves Phase 2's "source replay works from artifact files" and "source indexes rebuild cleanly from files" incomplete.

## Approaches

### 1. Re-run the plugin from config to reconstruct history

Pros:

- minimal new storage logic
- uses the same code path as live ingest

Cons:

- not replayable if external feeds changed
- violates artifact-first truth
- mixes historical inspection with live network access

Verdict: reject.

### 2. Add a generic source-history layer over runtime artifacts

Pros:

- keeps files as source of truth
- works offline
- supports replay and SQLite rebuild from the same artifact contract
- additive to existing source runner

Cons:

- requires one more shared module and CLI surface
- index schema must stay deliberately small

Verdict: recommended.

### 3. Build only an index rebuild command and skip replay helpers

Pros:

- smallest code change
- useful for analytics immediately

Cons:

- leaves no stable replay contract for operators or tests
- future tools would still parse artifact JSON ad hoc

Verdict: too narrow.

## Decision

Implement a generic `source_history` module in `lobster_runtime` plus a thin CLI script.

The module will:

- load a source run artifact from `lobster-intel/data/runtime/sources/<plugin-id>/runs/<run_id>.json`
- return a replay payload that preserves artifact lineage and summarizes evidence items
- rebuild `index.sqlite` from all run artifacts for one plugin

The CLI will expose two subcommands:

- `replay`
- `rebuild-index`

## Contract

### Replay contract

`replay_source_run(workspace_dir, plugin_id, run_id)` returns a JSON-serializable payload with:

- `plugin`
- `run_id`
- `ran_at_utc`
- `artifact_path`
- `state_path`
- `evidence_item_count`
- `new_count`
- `items`

`items` stays close to the original evidence record and includes:

- `source_id`
- `source_type`
- `external_id`
- `title`
- `url`
- `published_at_utc`
- `collected_at_utc`

This is a replay view, not a recomputation path. It does not re-run plugin code.

### Index contract

`rebuild_source_index(workspace_dir, plugin_id)` rebuilds:

- `lobster-intel/data/runtime/sources/<plugin-id>/index.sqlite`

Tables:

- `source_runs`
- `source_items`

`source_runs` stores one row per artifact file with run metadata and lineage path.
`source_items` stores one row per evidence item with stable synthetic item ids derived from the run and record identity.

The SQLite DB is rebuildable and non-authoritative. Files remain truth.

## Boundaries

- Source plugins continue to ingest and normalize evidence only.
- Replay and indexing live in runtime/support code, not delivery code.
- No delivery behavior changes are included in this slice.
- No source plugin contract rewrite is included in this slice.

## Tests

Add a dedicated `unittest`-based test file so this slice can be verified even in environments where `pytest` is not bootstrapped.

The tests should prove:

1. replay returns the expected historical payload from a stored run artifact
2. rebuild can recreate `index.sqlite` from `runs/*.json`
3. CLI `replay` and `rebuild-index` print stable JSON summaries

## Documentation

Update the runtime README and install guide to mention:

- source run artifacts are replayable from disk
- source indexes are rebuildable from `runs/*.json`
- the new CLI entrypoint for operators
