# Real Dispatcher Bundle Bridge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the dispatcher E2E bundle builder consume real `runtime_spine` artifacts instead of requiring a hand-crafted `alert_disposition` payload shape.

**Architecture:** Keep `build_e2e_contract_bundle_view` unchanged. Add a bridge in `dispatcher_bundle` that reads `delivery/alerts/<run-id>.json` and, when the alert is a raw runtime artifact, reconstructs contract fields from `runtime/runs`, `runtime/compare`, and `delivery/receipts`, stamping the operator-supplied `bundle_id` as the shared `e2e_run_id`.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest .venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_runtime_contract_bundle.py -q` (`22 passed`). Commit/push remains blocked here because this workspace is not a git repo.

---

### Task 1: Lock The Bridge Requirement In Tests

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_e2e_bundle.py`

- [x] Add a failing acceptance test that installs raw `runtime_spine` alert, compare, runtime, and receipt artifacts under a temp workspace.
- [x] Run the focused dispatcher bundle test file and verify RED.

### Task 2: Reconstruct Contract Payloads From Real Artifacts

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py`

- [x] Detect when an alert artifact lacks `alert_disposition` and project it into the existing contract shape.
- [x] Rehydrate `runtime_target_id`, `runtime_target_name`, `alert_target_id`, and `delivery_proof` from workspace artifacts.
- [x] Stamp the operator-provided `bundle_id` onto the projected payload as the shared `e2e_run_id`.
- [x] Run the focused dispatcher bundle tests and verify GREEN.

### Task 3: Document Operator Flow

**Files:**
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `lobster-intel/README.md`

- [x] Document that the bundle builder can now consume raw runtime-spine artifacts directly.
- [x] Run the delivery/contract verification slice after doc touch-ups.
- [ ] Commit

```bash
git add docs/superpowers/plans/2026-04-21-real-dispatcher-bundle-bridge.md lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py lobster-intel/docs/operations/reporting.md lobster-intel/README.md
git commit -m "feat: bridge real dispatcher artifacts into e2e bundles"
```
