# Firehose Normalized Source Run Plan

> **For agentic workers:** Keep this change scoped to Firehose local-file normalization, replay-compatible source artifacts, focused tests, and short operator docs. Do not move Firehose ranking or alert decisions into delivery code.

**Goal:** Turn the current operator-managed `events.jsonl` handoff into a replayable Lobster source-run artifact so Firehose evidence can enter the runtime spine through audited files instead of ad hoc local conventions.

**Architecture:** Read one local Firehose JSONL snapshot, normalize each event into a minimal `firehose_event` source item contract, and write the result to `lobster-intel/data/runtime/sources/firehose-tracker/` using the same `latest.json` and `runs/<run_id>.json` layout that existing source replay/index tooling already understands.

**Tech Stack:** Python 3.11+, stdlib `json`/`hashlib`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Prove Firehose Input Becomes Replayable Source Truth

**Files:**
- Create: `lobster-intel/tests/test_firehose_events.py`

- [x] Add a focused test for normalizing local Firehose JSONL into a source-run artifact.
- [x] Add a focused CLI test that prints a usable summary after writing artifacts.

### Task 2: Add The Normalization Bridge

**Files:**
- Create: `lobster-intel/packages/lobster-ingest/lobster_ingest/firehose.py`
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py`
- Create: `lobster-intel/scripts/normalize_firehose_events.py`

- [x] Normalize local Firehose records into `firehose_event` items with stable external ids.
- [x] Write replay-compatible `runs/<run_id>.json`, `latest.json`, and `state.json` artifacts under `runtime/sources/firehose-tracker/`.
- [x] Expose the normalization helper through `lobster_ingest` and a small CLI.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`

- [x] Document that Firehose local files now have a normalization/replay bridge.
- [x] Keep the docs explicit that filtering/ranking is still a separate unfinished slice.
