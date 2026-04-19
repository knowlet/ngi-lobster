# NGI Runtime Spine Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the thesis-scoped NGI runtime spine so one run produces auditable evidence, observation, fusion, runtime, compare, alert, and delivery receipt artifacts with replayable compare logic and a rebuildable SQLite index.

**Architecture:** Add a runtime-spine orchestration module in `lobster_runtime` that consumes current source runtime artifacts, maps them into thesis evidence and observations, computes fusion and compare outcomes, persists the thesis artifact chain, and hands delivery through the heartbeat gate. Keep the existing source plugin flow intact and layer the thesis runtime core on top of it.

**Tech Stack:** Python 3.11, stdlib `json`/`sqlite3`/`hashlib`, existing `lobster_runtime`, `lobster_delivery`, and `pytest`/`unittest` tests

---

### Task 1: Lock The Spine Contract With Tests

**Files:**
- Create: `lobster-intel/tests/test_runtime_spine.py`
- Modify: `lobster-intel/tests/test_source_runner_e2e.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Write the failing contract tests**

```python
def test_runtime_spine_run_writes_full_artifact_chain(tmp_path):
    result = run_thesis_runtime(build_fixture_input(tmp_path))
    assert result["runtime_snapshot"]["compare_mode"] == "full_compare"
    assert Path(result["paths"]["runtime_latest"]).exists()
    assert Path(result["paths"]["delivery_receipt"]).exists()


def test_compare_engine_routes_full_degraded_and_suppressed():
    assert compare_targets(full_case).compare_mode == "full_compare"
    assert compare_targets(degraded_case).compare_mode == "degraded_compare"
    assert compare_targets(suppressed_case).compare_mode == "suppressed"


def test_runtime_index_can_be_rebuilt_from_artifacts(tmp_path):
    result = run_thesis_runtime(build_fixture_input(tmp_path))
    db_path = rebuild_runtime_index(tmp_path, result["thesis_id"])
    db_path.unlink()
    rebuilt = rebuild_runtime_index(tmp_path, result["thesis_id"])
    assert rebuilt.exists()
```

- [ ] **Step 2: Run the new tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py -q`
Expected: FAIL with missing `run_thesis_runtime`, `compare_targets`, or rebuild helpers

- [ ] **Step 3: Extend the source-runner E2E test for thesis runtime output**

```python
output = subprocess.check_output(
    [
        str(repo / ".venv" / "bin" / "python"),
        "lobster-intel/scripts/run_thesis_runtime.py",
        "--workspace",
        ".",
        "--thesis-id",
        "gooaye",
    ],
    cwd=repo,
    text=True,
)
payload = json.loads(output)
assert payload["compare_mode"] in {"full_compare", "degraded_compare", "suppressed"}
assert Path(repo / payload["runtime_latest_path"]).exists()
```

- [ ] **Step 4: Run the focused E2E test and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: FAIL because the thesis runtime CLI does not exist yet

- [ ] **Step 5: Commit**

```bash
git add lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_source_runner_e2e.py
git commit -m "test: define runtime spine contract"
```

### Task 2: Implement Thesis Runtime Spine Orchestration

**Files:**
- Create: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Create: `lobster-intel/scripts/run_thesis_runtime.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add the runtime spine module with artifact writers and compare engine**

```python
def run_thesis_runtime(inp: ThesisRuntimeInput) -> ThesisRuntimeResult:
    evidence = build_evidence_artifacts(inp)
    observations = build_observation_artifacts(inp, evidence)
    fusion = build_runtime_fusion(inp, observations)
    active_target = resolve_active_target(inp, observations)
    compare = compare_targets(...)
    alert = decide_alert(...)
    receipt = deliver_runtime_alert(...)
    persist_artifacts(...)
    return ThesisRuntimeResult(...)
```

- [ ] **Step 2: Add the thesis runtime CLI**

```python
ap.add_argument("--thesis-id", required=True)
ap.add_argument("--workspace", default=".")
ap.add_argument("--official", default="lobster-intel/data/runtime/sources/official-statements-tracker/latest.json")
ap.add_argument("--watchlist", default="lobster-intel/data/runtime/sources/watchlist-tracker/latest.json")
ap.add_argument("--polymarket", default="lobster-intel/data/runtime/sources/polymarket-tracker/latest.json")
```

- [ ] **Step 3: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: PASS

- [ ] **Step 4: Refactor only after green**

```python
def artifact_path(root: Path, category: str, thesis_id: str, *parts: str) -> Path:
    ...
```

- [ ] **Step 5: Commit**

```bash
git add lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py lobster-intel/scripts/run_thesis_runtime.py
git commit -m "feat: add thesis runtime spine"
```

### Task 3: Add Replay, Delivery Boundary, And Rebuild Helpers

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add replay and lineage helpers**

```python
def replay_compare_from_artifacts(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, Any]:
    runtime_snapshot = json.loads(...)
    fusion_artifact = json.loads(...)
    return compare_targets(...)


def trace_run_lineage(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, list[str]]:
    return {"receipt_to_alert": [...], "alert_to_compare": [...], "fusion_to_evidence": [...]}
```

- [ ] **Step 2: Add the heartbeat delivery boundary receipt path**

```python
heartbeat_payload = json.dumps(minimum_alert_payload, ensure_ascii=False)
validated_output = validate_background_output(heartbeat_payload)
receipt = {
    "sink": "openclaw_heartbeat",
    "delivery_status": "delivered" if should_send else "suppressed",
    "sink_receipt_id": f"heartbeat:{run_id}",
    "boundary_output": validated_output,
}
```

- [ ] **Step 3: Add SQLite rebuild support**

```python
with sqlite3.connect(index_path) as conn:
    conn.execute(
        "create table if not exists runtime_runs (run_id text primary key, thesis_id text, compare_mode text, artifact_path text)"
    )
```

- [ ] **Step 4: Run full verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py lobster-intel/tests/test_runtime_spine.py
git commit -m "feat: add replayable runtime artifact chain"
```
