# Firehose Artifact Path Safety Plan

> **For agentic workers:** Keep this change scoped to Firehose artifact path validation, focused tests, and short operator docs. Do not change Firehose ranking, filtering, or source-fusion decision math here.

**Goal:** Make Firehose normalization reject unsafe `plugin_id` and `run_id` values before writing runtime artifacts so artifact creation matches the same path-safety contract already enforced by source replay/index tooling.

**Architecture:** Reuse the same "simple relative path component only" rule at the Firehose ingest boundary, validate both runtime path components before file creation, and lock the contract with focused unit tests plus one short operator note on acceptable `run_id` format.

**Tech Stack:** Python 3.11+, stdlib `re`/`json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Unsafe Path Gap

**Files:**
- Modify: `lobster-intel/tests/test_firehose_events.py`

- [x] Add a focused test that rejects unsafe Firehose `plugin_id` inputs.
- [x] Add a focused test that rejects unsafe Firehose `run_id` inputs.

### Task 2: Validate Firehose Artifact Paths Before Writing

**Files:**
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/firehose.py`

- [x] Reject non-simple `plugin_id` path components before building runtime directories.
- [x] Reject non-simple `run_id` path components before writing `runs/<run_id>.json`.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that Firehose normalization expects a slash-free timestamp-like `run_id`.
