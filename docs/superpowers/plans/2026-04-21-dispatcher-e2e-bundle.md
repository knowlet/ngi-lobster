# Dispatcher E2E Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runtime-artifact-backed dispatcher E2E bundle builder that groups suppressed and delivered controls under one shared machine-readable bundle id.

**Architecture:** Keep the existing alert contract view and runtime contract view unchanged. Add a new `dispatcher_bundle` helper under `lobster_delivery` that loads multiple run artifacts from the workspace, normalizes them into alert contract views, verifies shared contract fields, and writes one auditable bundle artifact plus a thin CLI for operators.

**Tech Stack:** Python 3.11+, stdlib `json`/`argparse`/`pathlib`, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and re-verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest .venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_runtime_contract_bundle.py -q` (`17 passed`). Commit/push remains blocked here because this workspace is not a git repo.

---

### Task 1: Lock The Dispatcher Bundle Contract In Tests

**Files:**
- Create: `lobster-intel/tests/test_dispatcher_e2e_bundle.py`

- [x] **Step 1: Write the failing happy-path bundle test**

```python
def test_write_dispatcher_e2e_bundle_writes_bundle_artifact(tmp_path: Path):
    result = write_dispatcher_e2e_bundle(
        workspace_dir=tmp_path,
        thesis_id="gooaye",
        run_ids=["legacy-20260421T000000Z", "positive-20260421T000500Z"],
        bundle_id="bundle-20260421-01",
    )

    assert result["status"] == "ok"
    assert result["bundle"]["e2e_run_id"] == "bundle-20260421-01"
    assert (tmp_path / result["bundle_artifact_path"]).exists()
```

- [x] **Step 2: Write the failing fail-closed mismatch test**

```python
def test_write_dispatcher_e2e_bundle_fails_closed_on_mismatched_bundle_id(tmp_path: Path):
    with pytest.raises(ValueError, match="shared e2e_run_id"):
        write_dispatcher_e2e_bundle(
            workspace_dir=tmp_path,
            thesis_id="gooaye",
            run_ids=["legacy-20260421T000000Z", "positive-20260421T000500Z"],
            bundle_id="bundle-20260421-02",
        )
```

- [x] **Step 3: Write the failing CLI coverage test**

```python
payload = json.loads(
    subprocess.check_output(
        [
            sys.executable,
            "lobster-intel/scripts/build_dispatcher_e2e_bundle.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--bundle-id",
            "bundle-20260421-01",
            "--run-id",
            "legacy-20260421T000000Z",
            "--run-id",
            "positive-20260421T000500Z",
        ],
        text=True,
    )
)
assert payload["status"] == "ok"
```

- [x] **Step 4: Run focused tests and verify RED**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_e2e_bundle.py -q`
Expected: FAIL because the dispatcher bundle helper and CLI do not exist yet

### Task 2: Implement Runtime-Backed Dispatcher Bundle Helpers

**Files:**
- Create: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`
- Create: `lobster-intel/scripts/build_dispatcher_e2e_bundle.py`

- [x] **Step 1: Load alert runtime artifacts per run id and normalize them into contract views**

```python
def load_dispatcher_payloads(workspace_dir: str | Path, thesis_id: str, run_ids: list[str]) -> list[dict[str, Any]]:
    delivery_root = Path(workspace_dir) / "lobster-intel" / "data" / "delivery" / thesis_id / "alerts"
    return [_load_json(delivery_root / f"{run_id}.json") for run_id in run_ids]
```

- [x] **Step 2: Enforce one shared bundle id and write an auditable artifact**

```python
bundle_payload = {
    "schema": "lobster.delivery.dispatcher_e2e_bundle.v1",
    "recorded_at_utc": recorded_at_utc,
    "thesis_id": thesis_id,
    "run_ids": run_ids,
    "contract_version": result["bundle"]["contract_version"],
    "e2e_run_id": result["bundle"]["e2e_run_id"],
    "fixtures": result["bundle"]["fixtures"],
}
```

- [x] **Step 3: Add a CLI that builds from `delivery/alerts/<run-id>.json`**

```python
parser.add_argument("--workspace", default=".")
parser.add_argument("--thesis-id", required=True)
parser.add_argument("--bundle-id", required=True)
parser.add_argument("--run-id", action="append", dest="run_ids", required=True)
```

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_e2e_bundle.py -q`
Expected: PASS

### Task 3: Document Operator Flow

**Files:**
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `lobster-intel/README.md`

- [x] **Step 1: Document how to build the shared dispatcher bundle artifact**

```md
Operators can build one auditable dispatcher E2E bundle directly from `delivery/alerts/<run-id>.json` artifacts by running:

./.venv/bin/python lobster-intel/scripts/build_dispatcher_e2e_bundle.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260421-01 \
  --run-id legacy-20260421T000000Z \
  --run-id positive-20260421T000500Z
```

- [x] **Step 2: Run final verification**

Run: `./.venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_runtime_contract_bundle.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-04-21-dispatcher-e2e-bundle.md lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_bundle.py lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py lobster-intel/scripts/build_dispatcher_e2e_bundle.py lobster-intel/docs/operations/reporting.md lobster-intel/README.md
git commit -m "feat: add dispatcher e2e bundle builder"
```
