# Runtime Contract Receipt Alert Lineage Plan

> **For agentic workers:** Keep this change scoped to runtime contract verification, focused tests, and brief operator docs. Do not change dispatcher gate behavior in this plan.

**Goal:** Fail closed when runtime contract verification loads a delivery receipt whose `alert_artifact_id` is missing or no longer points at the alert artifact for the audited run.

**Architecture:** Treat `receipt.alert_artifact_id` as required lineage in the runtime contract view, not only in dispatcher acceptance receipt reuse. The runtime contract loader should reject missing or mismatched receipt-to-alert linkage so audit tooling cannot report a delivered run as valid when its persisted receipt is detached from the alert artifact under review.

**Tech Stack:** Python 3.11+, stdlib JSON/pathlib, pytest, Markdown docs

---

### Task 1: Prove Runtime Contract Lineage Fails Closed

**Files:**
- Modify: `lobster-intel/tests/test_runtime_contract_bundle.py`

- [x] Add a focused test for missing `receipt.alert_artifact_id`.
- [x] Add a focused test for mismatched `receipt.alert_artifact_id`.

### Task 2: Tighten Runtime Contract Verification

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`

- [x] Require `receipt.alert_artifact_id` in runtime contract verification.
- [x] Reject delivery receipts whose `alert_artifact_id` no longer matches `alert.artifact_id`.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/docs/operations/reporting.md`

- [x] Document that runtime contract verification now checks receipt-to-alert lineage too.

**Status:** Implemented in the writable workspace on 2026-04-22.
