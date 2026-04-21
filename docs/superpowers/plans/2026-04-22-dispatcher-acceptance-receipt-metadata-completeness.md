# Dispatcher Acceptance Receipt Metadata Completeness Plan

> **For agentic workers:** Keep this change scoped to the dispatcher acceptance wrapper CLI, focused receipt-reuse tests, and the operator docs that describe the fail-closed contract.

**Goal:** Make persisted positive-control receipt reuse fail closed when required lineage metadata is missing, not only when present values mismatch.

**Architecture:** Treat `thesis_id`, `run_id`, and requested `contract_version` as required receipt metadata before any persisted receipt can be reused by `run_dispatcher_acceptance.py`. Reject incomplete persisted receipts before dispatcher artifacts or bundles are written so the acceptance bundle never mixes unverifiable delivery proof into the runtime contract path.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Prove Missing Metadata Fails Closed

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add a focused CLI regression test for missing persisted `contract_version`.
- [x] Add a focused CLI regression test for missing persisted `thesis_id`.

### Task 2: Tighten The Receipt Reuse Guard

**Files:**
- Modify: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [x] Reject persisted receipts that omit required lineage metadata.
- [x] Keep the existing explicit mismatch error for `contract_version` so operator failures stay legible.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that receipt reuse now fails closed on missing or mismatched `thesis_id`, `run_id`, and `contract_version`.
