# Default Workflow Runtime Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the install-time default workflow run both source ingest and thesis runtime so a fresh workspace produces runtime and delivery artifacts plus a machine-readable summary.

**Architecture:** Keep `scripts/run_default_workflow.sh` as the top-level operator entrypoint, but make it invoke a new `lobster-intel/scripts/run_thesis_runtime.py` CLI after source ingest. Add a `lobster_runtime.runtime_spine` module that discovers installed source artifacts, resolves thesis settings/registry defaults, runs the runtime spine, and emits runtime, compare, alert, and delivery receipt artifacts.

**Tech Stack:** Bash, Python 3.11+, stdlib `json`/`argparse`/`pathlib`, existing `lobster-runtime` and `lobster-delivery` packages, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest ./.venv/bin/python -m pytest lobster-intel/tests/test_default_workflow.py lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_delivery_gate.py -q` (`8 passed`). Commit/push remains blocked here because this workspace is not a git repo.

---

### Task 1: Lock The Default Workflow Acceptance Contract

**Files:**
- Create: `lobster-intel/tests/test_default_workflow.py`

- [x] **Step 1: Write the failing acceptance test**

```python
def test_default_workflow_runs_thesis_runtime_spine(tmp_path: Path):
    result = subprocess.run(
        ["bash", str(repo / "scripts" / "run_default_workflow.sh")],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    assert result.returncode == 0, result.stderr
    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "full_compare"
    assert Path(payload["artifact_paths"]["runtime_latest"]).exists()
    assert Path(payload["artifact_paths"]["delivery_receipt"]).exists()
```

- [x] **Step 2: Run the focused test and verify RED**

Run: `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest ./.venv/bin/python -m pytest lobster-intel/tests/test_default_workflow.py -q`
Expected: FAIL because the default workflow still exits after ingest and no runtime-spine CLI exists

### Task 2: Add Runtime Spine Discovery And CLI

**Files:**
- Create: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py`
- Create: `lobster-intel/scripts/run_thesis_runtime.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/gate.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`

- [x] **Step 1: Implement discovered-source loading and thesis-pack defaults**
- [x] **Step 2: Implement runtime artifact persistence and heartbeat receipt emission**
- [x] **Step 3: Add the CLI wrapper and export the new runtime spine API**
- [x] **Step 4: Run the focused acceptance test and verify GREEN**

### Task 3: Wire The Default Workflow Entry Point

**Files:**
- Modify: `scripts/run_default_workflow.sh`
- Modify: `lobster-intel/README.md`

- [x] **Step 1: Chain ingest into thesis runtime execution**
- [x] **Step 2: Document that the default workflow now emits runtime and delivery artifacts**
- [x] **Step 3: Run final verification**

Run: `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest ./.venv/bin/python -m pytest lobster-intel/tests/test_default_workflow.py lobster-intel/tests/test_runtime_contract_bundle.py -q`
Expected: PASS
