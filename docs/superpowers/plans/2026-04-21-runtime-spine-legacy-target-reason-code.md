# Runtime Spine Legacy Target Reason Code Alignment

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Align real `runtime_spine` suppressions with the product contract by emitting `legacy_target_mismatch` on target-identity mismatch, then prove the shared dispatcher bundle still reconstructs one suppressed + one delivered fixture from actual runtime runs.

**Architecture:** Keep the dispatcher artifact writer and bundle bridge unchanged. Fix the source of truth in `lobster_runtime.runtime_spine.compare_targets()` so the compare artifact carries the canonical mismatch reason code already required by delivery and review tooling. Add one runtime-spine integration test that runs the spine twice, then builds the shared dispatcher E2E bundle from those real artifacts.

**Tech Stack:** Python 3.11+, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest ./.venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine_dispatcher_path.py lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_alert_target_contract.py -q` (`26 passed`).

---

### Task 1: Freeze The Contract Gap In A Real Runtime-Path Test

**Files:**
- Create: `lobster-intel/tests/test_runtime_spine_dispatcher_path.py`

- [x] Add an integration test that runs `run_thesis_runtime()` once for a legacy-target suppression and once for a positive-control delivery.
- [x] Assert the suppressed runtime alert uses `reason_code=legacy_target_mismatch`.
- [x] Assert `write_dispatcher_e2e_bundle()` reconstructs one shared bundle with delivery proof from those real runtime artifacts.

### Task 2: Align Runtime Compare Reasons With The Product Contract

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`

- [x] Replace the internal target-identity suppression reason with the canonical dispatcher-visible contract code `legacy_target_mismatch`.
- [x] Keep compare-mode behavior unchanged aside from the surfaced reason code.

### Task 3: Verify The Dispatcher/Contract Slice

**Files:**
- Verify only

- [x] Run the new focused runtime-spine integration test and verify RED before the fix.
- [x] Re-run the new test and the dispatcher/runtime contract slice after the fix and verify GREEN.
