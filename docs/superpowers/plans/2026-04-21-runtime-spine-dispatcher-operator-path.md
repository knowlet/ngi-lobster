# Runtime Spine Dispatcher Operator Path Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Prove the real dispatcher-path acceptance cut by letting operator tooling consume `runtime_spine` run artifacts, emit dispatcher artifacts, and build one shared E2E bundle with delivery proof.

**Architecture:** Keep `write_dispatcher_artifact.py` and `build_dispatcher_e2e_bundle.py` as the operator entrypoints. Teach the writer to reconstruct dispatcher disposition fields from the workspace's runtime compare + alert artifacts when the input runtime run file has no embedded `alert_disposition`, then let the bundle builder stamp the operator-supplied `bundle_id` onto dispatcher payloads that are otherwise complete but still missing `e2e_run_id`.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-ingest:lobster-intel/packages/lobster-plugins:lobster-intel/packages/lobster-runtime ./.venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_alert_contract_view.py -q` (`23 passed`).

---

### Task 1: Freeze The Real Runtime-Path Gap In Tests

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add a failing acceptance test that installs real `runtime/runs`, `runtime/compare`, and runtime alert artifacts, then drives `write_dispatcher_artifacts()` twice before building one shared dispatcher bundle.
- [x] Run the focused dispatcher writer test file and verify RED on missing `runtime_payload.alert_disposition.decision`.

### Task 2: Reconstruct Dispatcher Fields From Runtime Spine Artifacts

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py`

- [x] Project dispatcher disposition fields from existing runtime compare + alert artifacts when the input runtime run file lacks `alert_disposition`.
- [x] Preserve `market_target`, `target_detail.market_yes_probability`, and `first_principles_probability` on the emitted dispatcher artifact so downstream contract tooling reads one consistent payload shape.
- [x] Stamp `bundle_id` as `e2e_run_id` when bundle builder reads a dispatcher payload that is otherwise complete but still missing the shared bundle id.
- [x] Run the dispatcher/runtime contract slice and verify GREEN.

### Task 3: Document The Operator Contract

**Files:**
- Modify: `lobster-intel/docs/operations/reporting.md`

- [x] Document that `write_dispatcher_artifact.py` can now start from `runtime/runs/<run-id>.json` plus the workspace's existing runtime compare/alert artifacts.
- [x] Document that `build_dispatcher_e2e_bundle.py` stamps the operator-provided `--bundle-id` when dispatcher payloads still lack `e2e_run_id`.
