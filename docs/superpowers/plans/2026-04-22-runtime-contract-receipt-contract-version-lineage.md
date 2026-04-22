# Runtime Contract Receipt Contract Version Lineage Plan

> **For agentic workers:** Keep this change scoped to runtime contract verification, focused tests, and brief operator docs. Do not change dispatcher gate behavior in this plan.

**Goal:** Fail closed when runtime contract verification loads a delivery receipt whose `contract_version` is missing or no longer matches the alert artifact for the audited run.

**Architecture:** Extend the runtime contract view so receipt lineage includes `contract_version` alongside `alert_artifact_id`. The runtime contract loader should reject missing or mismatched receipt-to-alert contract versions, so audit tooling cannot treat a delivered run as valid when its persisted receipt comes from a different contract lineage than the alert artifact under review.

**Tech Stack:** Python 3.11+, stdlib JSON/pathlib, pytest, Markdown docs

---

### Task 1: Prove Contract-Version Lineage Fails Closed

**Files:**
- Modify: `lobster-intel/tests/test_runtime_contract_bundle.py`

- [ ] Add a focused test for missing `receipt.contract_version`.
- [ ] Add a focused test for mismatched `receipt.contract_version`.

### Task 2: Tighten Runtime Contract Verification

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`

- [ ] Require `receipt.contract_version` in runtime contract verification.
- [ ] Reject delivery receipts whose `contract_version` no longer matches `alert.contract_version`.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/docs/operations/reporting.md`

- [ ] Document that runtime contract verification now checks receipt-to-alert `contract_version` lineage too.
