# Runtime Spine Verification Gates Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Close the remaining MVP verification gaps from `docs/superpowers/specs/2026-04-17-ngi-runtime-spine-design.md` by proving actual thesis runtime artifacts satisfy the contract for artifact completeness, truth-only downstream consumption, and OpenClaw heartbeat receipt evidence.

**Architecture:** Reuse the existing runtime spine and delivery helpers, but add a fail-closed verification adapter that derives contract views directly from thesis runtime `runtime`, `compare`, `alert`, and `receipt` artifacts. Keep example-bundle verification for design review fixtures, while adding a runtime-artifact-backed verification path that operators can run against a real thesis run without hand-editing payloads.

**Tech Stack:** Python 3.11, pytest, runtime and delivery packages under `lobster-intel/packages/`, CLI scripts under `lobster-intel/scripts/`, JSON artifact files under `lobster-intel/data/`

**Status:** Implemented in the writable workspace on 2026-04-22. Runtime-backed verifier coverage landed in code and the operator docs now distinguish curated bundle verification from real artifact-chain verification.

---

### Task 1: Freeze The Runtime Verification Contract In Tests

**Files:**
- Create: `lobster-intel/tests/test_runtime_contract_bundle.py`
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Modify: `lobster-intel/tests/test_verify_alert_contract_bundle_cli.py`
- Test: `lobster-intel/tests/test_runtime_contract_bundle.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add a failing test for a real runtime-artifact contract view**

```python
def test_build_runtime_contract_view_accepts_real_thesis_runtime_artifacts(tmp_path: Path):
    result = run_thesis_runtime(
        ThesisRuntimeInput(
            thesis_id="gooaye",
            workspace_dir=tmp_path,
            official_statements=_source_payloads()[0],
            watchlist=_source_payloads()[1],
            polymarket=_source_payloads()[2],
            target_registry=_target_registry(),
            semantic_frame="military_operations_end_by_deadline",
            probability_direction="yes_is_peace",
            now_utc="2026-04-19T12:30:00+00:00",
        )
    )

    contract_view = build_runtime_contract_view(
        runtime_snapshot=result.runtime_snapshot,
        compare_artifact=result.compare_artifact,
        alert_artifact=result.alert_artifact,
        delivery_receipt=result.delivery_receipt,
    )

    assert contract_view["status"] == "ok"
    assert contract_view["view"]["runtime"]["compare_mode"] == "full_compare"
    assert contract_view["view"]["receipt"]["delivery_proof"]["boundary"] == "openclaw_heartbeat"
```

- [ ] **Step 2: Add a failing test for missing receipt proof**

```python
def test_build_runtime_contract_view_fails_closed_without_delivery_proof():
    result = build_runtime_contract_view(
        runtime_snapshot={"artifact_id": "runtime:1"},
        compare_artifact={"artifact_id": "compare:1"},
        alert_artifact={"artifact_id": "alert:1"},
        delivery_receipt={"artifact_id": "receipt:1", "sink": "openclaw_heartbeat"},
    )

    assert result["status"] == "contract_incomplete"
    assert "receipt.delivery_proof" in result["missing_fields"]
```

- [ ] **Step 3: Add a failing CLI proof test that loads a run from artifact files**

```python
def test_verify_runtime_contract_bundle_cli_accepts_real_runtime_run(tmp_path: Path):
    result = run_thesis_runtime(build_fixture_input(tmp_path))

    completed = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/verify_runtime_contract_bundle.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--run-id",
            result.run_id,
        ],
        cwd=ROOT,
        text=True,
        capture_output=True,
        check=False,
    )

    assert completed.returncode == 0, completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
```

- [ ] **Step 4: Run focused tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_runtime_spine.py -k contract -q`
Expected: FAIL because there is no runtime-artifact contract adapter or verifier CLI yet

### Task 2: Implement Runtime-Artifact Contract Verification

**Files:**
- Create: `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`
- Create: `lobster-intel/scripts/verify_runtime_contract_bundle.py`
- Test: `lobster-intel/tests/test_runtime_contract_bundle.py`

- [ ] **Step 1: Add a runtime contract view builder that validates actual thesis artifacts**

```python
def build_runtime_contract_view(
    *,
    runtime_snapshot: dict[str, Any],
    compare_artifact: dict[str, Any],
    alert_artifact: dict[str, Any],
    delivery_receipt: dict[str, Any],
) -> dict[str, Any]:
    view = {
        "runtime": {
            "artifact_id": runtime_snapshot.get("artifact_id"),
            "compare_mode": runtime_snapshot.get("compare_mode"),
            "active_target": runtime_snapshot.get("active_target"),
            "P_AI": runtime_snapshot.get("P_AI"),
            "market_implied_probability": runtime_snapshot.get("market_implied_probability"),
            "ngi_gap": runtime_snapshot.get("ngi_gap"),
        },
        "compare": {
            "artifact_id": compare_artifact.get("artifact_id"),
            "compare_mode": compare_artifact.get("compare_mode"),
            "fallback_reason_codes": compare_artifact.get("fallback_reason_codes"),
        },
        "alert": {
            "artifact_id": alert_artifact.get("artifact_id"),
            "should_send": alert_artifact.get("should_send"),
            "reason_code": alert_artifact.get("reason_code"),
        },
        "receipt": {
            "artifact_id": delivery_receipt.get("artifact_id"),
            "sink": delivery_receipt.get("sink"),
            "delivery_status": delivery_receipt.get("delivery_status"),
            "delivery_proof": delivery_receipt.get("delivery_proof"),
        },
    }
```

- [ ] **Step 2: Add a loader that reconstructs the contract bundle from workspace files**

```python
def load_runtime_contract_bundle(workspace_dir: str | Path, thesis_id: str, run_id: str) -> dict[str, Any]:
    runtime_root = Path(workspace_dir) / "lobster-intel" / "data" / "runtime" / thesis_id
    delivery_root = Path(workspace_dir) / "lobster-intel" / "data" / "delivery" / thesis_id
    runtime_snapshot = _load_json(runtime_root / "runs" / f"{run_id}.json")
    compare_artifact = _load_json(runtime_root / "compare" / f"{run_id}.json")
    alert_artifact = _load_json(delivery_root / "alerts" / f"{run_id}.json")
    delivery_receipt = _load_json(delivery_root / "receipts" / f"{run_id}.json")
    return build_runtime_contract_view(
        runtime_snapshot=runtime_snapshot,
        compare_artifact=compare_artifact,
        alert_artifact=alert_artifact,
        delivery_receipt=delivery_receipt,
    )
```

- [ ] **Step 3: Add a verifier CLI for real runtime runs**

```python
ap.add_argument("--workspace", default=".")
ap.add_argument("--thesis-id", required=True)
ap.add_argument("--run-id", required=True)
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_runtime_spine.py -k contract -q`
Expected: PASS

### Task 3: Prove Truth-Only Consumption And Operator Review Flow

**Files:**
- Modify: `lobster-intel/tests/test_verify_alert_contract_bundle_cli.py`
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `README.md`

- [ ] **Step 1: Document the two verification paths clearly**

```md
- `verify_alert_contract_bundle.py`: verifies curated review fixtures or example bundles
- `verify_runtime_contract_bundle.py`: verifies a real thesis runtime run directly from artifact files
```

- [ ] **Step 2: Document the truth-only rule for downstream consumers**

```md
Delivery and reporting must render the thesis runtime artifact chain rooted at
`lobster-intel/data/runtime/<thesis_id>/latest.json` and its sibling compare,
alert, and receipt artifacts. Consumers must fail closed instead of inventing
missing target identity, compare mode, or reason codes.
```

- [ ] **Step 3: Run final verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_verify_alert_contract_bundle_cli.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-runtime-spine-verification-gates.md lobster-intel/tests/test_runtime_contract_bundle.py lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_verify_alert_contract_bundle_cli.py lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py lobster-intel/scripts/verify_runtime_contract_bundle.py lobster-intel/docs/operations/reporting.md docs/INSTALL_OPENCLAW.md README.md
git commit -m "feat: add runtime spine verification gates"
```
