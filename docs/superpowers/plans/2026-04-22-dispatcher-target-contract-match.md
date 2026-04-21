# Dispatcher Target Contract Match Plan

> **For agentic workers:** Keep this change scoped to the existing dispatcher contract view, artifact projection, focused tests, and operator docs. Do not change runtime target-selection behavior in this plan.

**Goal:** Expose one dispatcher-visible boolean-equivalent target match result so PO can audit suppress/pass outcomes from the saved acceptance artifacts without manually comparing ids.

**Architecture:** Reuse the compare artifact as the source of truth when projecting runtime-backed dispatcher artifacts, persist the derived boolean as `target_contract_match`, and let contract views infer the same field from `runtime_target_id` plus `alert_target_id` when older payloads omitted it. Document the new field in the dispatcher acceptance workflow.

**Tech Stack:** Python 3.11+, stdlib JSON/pathlib, pytest/unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Contract Gap

**Files:**
- Modify: `lobster-intel/tests/test_alert_contract_view.py`
- Modify: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add focused assertions that suppressed fixtures expose `target_contract_match=False` and delivered fixtures expose `target_contract_match=True`.
- [x] Require the persisted dispatcher bundle path to surface the same boolean field on both fixtures.

### Task 2: Persist And Project The Field

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/contract.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py`

- [x] Persist `target_contract_match` when dispatcher artifacts are projected from runtime plus compare artifacts.
- [x] Infer `target_contract_match` from `runtime_target_id == alert_target_id` inside the alert contract view for compatibility with older payloads.

### Task 3: Update Operator Guidance

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that dispatcher acceptance artifacts and bundle verification now surface `target_contract_match`.
- [x] Keep the docs focused on how operators audit the saved bundle, not on implementation internals.
