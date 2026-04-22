# Dispatcher Acceptance Receipt Alert Artifact Integrity Plan

> **For agentic workers:** Keep this change scoped to the dispatcher acceptance wrapper CLI, focused receipt-reuse tests, and operator docs. Do not change runtime gate behavior in this plan.

**Goal:** Fail closed when dispatcher acceptance reuses a persisted positive-control receipt whose `alert_artifact_id` is missing or no longer points at the requested positive run.

**Architecture:** Treat `alert_artifact_id` as required persisted receipt lineage alongside `thesis_id`, `run_id`, and `contract_version`. Validate that the persisted receipt still points at `alert:<thesis_id>:<positive_run_id>` before the wrapper rewrites dispatcher artifacts or bundles, so acceptance evidence cannot silently reuse a receipt detached from the current alert contract path.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, unittest, Markdown docs

---

### Task 1: Prove Alert Artifact Lineage Fails Closed

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add a focused CLI regression test for persisted receipts missing `alert_artifact_id`.
- [x] Add a focused CLI regression test for persisted receipts whose `alert_artifact_id` no longer matches the requested positive run.

### Task 2: Tighten Persisted Receipt Reuse

**Files:**
- Modify: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [x] Require `alert_artifact_id` before reusing a persisted receipt.
- [x] Reject persisted receipts whose `alert_artifact_id` no longer points at `alert:<thesis_id>:<positive_run_id>`.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/docs/operations/reporting.md`

- [x] Document that receipt reuse now also validates persisted `alert_artifact_id` lineage.

**Status:** Implemented in the writable workspace on 2026-04-22.
