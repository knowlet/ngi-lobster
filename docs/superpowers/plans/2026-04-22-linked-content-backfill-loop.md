# Linked Content Backfill Loop Plan

> **For agentic workers:** Keep this change scoped to the existing linked-content queue processor, one focused backfill CLI, its tests, and operator docs. Do not change the extractor contract in this plan.

**Goal:** Let operators backfill queued linked-content extraction work across existing runtime run artifacts without manually invoking the single-run processor for each historical run.

**Architecture:** Reuse `process_linked_content_queue()` as the single-run worker, then add a small backfill helper that scans `lobster-intel/data/runtime/<thesis-id>/runs/*.json`, skips runs that already have a matching linked-content receipt, and processes only runs whose `linked_content_queue` still needs artifacts. Expose that helper through a dedicated CLI and document the operator flow.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Backfill Contract

**Files:**
- Modify: `lobster-intel/tests/test_linked_content_platform.py`

- [x] Add a focused test that seeds multiple runtime runs and requires the backfill helper to process only runs without an existing linked-content receipt.
- [x] Add a focused CLI test that runs the backfill entrypoint and verifies the machine-readable summary.

### Task 2: Add The Backfill Helper And CLI

**Files:**
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/linked_content.py`
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/__init__.py`
- Create: `lobster-intel/scripts/backfill_linked_content_queue.py`

- [x] Add a helper that enumerates runtime runs, skips existing receipt-backed runs, and reuses `process_linked_content_queue()` for missing ones.
- [x] Print one JSON summary from the CLI so operators can audit processed vs skipped runs.

### Task 3: Document The Operator Backfill Path

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document the new backfill command and what it skips.
- [x] Update the install guide operator flow so linked-content follow-up work has parity with visual-evidence backfill.
