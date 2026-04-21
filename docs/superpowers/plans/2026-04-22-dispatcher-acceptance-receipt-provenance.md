# Dispatcher Acceptance Receipt Provenance Plan

> **For agentic workers:** Keep this change scoped to the dispatcher acceptance CLI, one focused CLI test, and brief operator guidance. Do not change dispatcher decision rules in this plan.

**Goal:** Fail closed when dispatcher acceptance reuses a persisted delivery receipt whose embedded metadata does not belong to the requested positive-control run.

**Architecture:** Reuse the existing `delivery/<thesis-id>/receipts/<positive-run-id>.json` lookup path, but validate the persisted receipt payload before merging overrides. Reject mismatched `run_id` or `thesis_id` with one concise CLI error so operators do not accidentally stamp the wrong delivery proof onto a shared E2E bundle.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, pytest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Provenance Gap

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_acceptance_cli.py`

- [x] Add a focused CLI test that corrupts the persisted positive receipt metadata while keeping the filename unchanged.
- [x] Require the CLI to exit non-zero and emit a clear provenance mismatch error instead of reusing the wrong proof.

### Task 2: Fail Closed On Mismatched Receipts

**Files:**
- Modify: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [x] Validate persisted receipt `run_id` and `thesis_id` before merging any CLI overrides.
- [x] Convert receipt-validation failures into one explicit CLI error line instead of a raw traceback.

### Task 3: Update Operator Guidance

**Files:**
- Modify: `lobster-intel/README.md`

- [x] Document that receipt reuse only happens when the persisted receipt metadata still matches the requested positive-control run.
