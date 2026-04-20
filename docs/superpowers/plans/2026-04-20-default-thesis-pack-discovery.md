# Default Thesis Pack Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the install-ready default workflow discover thesis-specific runtime defaults and target registry entries so the runtime can resolve an active target without manual CLI wiring.

**Architecture:** Add a thesis-pack discovery path on top of the current runtime source discovery flow. Keep explicit CLI overrides authoritative, but allow installed example packs to supply the semantic frame, probability direction, state, and target registry for a thesis when the operator only provides `--workspace` and `--thesis-id`.

**Tech Stack:** Python 3.11, stdlib `json`/`pathlib`, existing `lobster_runtime` CLI/tests, pytest

---

### Task 1: Lock Thesis-Pack Discovery With Tests

**Files:**
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Modify: `lobster-intel/tests/test_default_workflow.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_default_workflow.py`

- [ ] **Step 1: Write the failing runtime-input discovery test**

```python
def test_load_thesis_runtime_inputs_discovers_thesis_pack_defaults(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    _install_runtime_source_artifacts(tmp_path, official, watchlist, polymarket)
    thesis_pack_path = tmp_path / "lobster-intel" / "examples" / "thesis-packs" / "gooaye.json"
    thesis_pack_path.parent.mkdir(parents=True, exist_ok=True)
    thesis_pack_path.write_text(json.dumps(_thesis_pack()), encoding="utf-8")

    payload = runtime_spine.load_thesis_runtime_inputs(tmp_path, thesis_id="gooaye")

    assert payload["target_registry"] == _target_registry()
    assert payload["thesis_settings"]["semantic_frame"] == "military_operations_end_by_deadline"
    assert payload["registry_resolution"]["mode"] == "thesis_pack_discovered"
```

- [ ] **Step 2: Run the focused runtime-input test and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py -k thesis_pack -q`
Expected: FAIL because `load_thesis_runtime_inputs()` does not return thesis-pack defaults yet

- [ ] **Step 3: Write the failing default workflow test**

```python
def test_default_workflow_uses_installed_thesis_pack(tmp_path: Path):
    repo = _prepare_isolated_repo(tmp_path)
    result = subprocess.run([...], cwd=repo, text=True, capture_output=True, check=False)

    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "full_compare"
    assert payload["input_contract"]["registry_resolution"]["mode"] == "thesis_pack_discovered"
```

- [ ] **Step 4: Run the focused default workflow test and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_default_workflow.py -q`
Expected: FAIL because the default workflow currently discovers source artifacts only and does not load an installed thesis pack

### Task 2: Add Thesis-Pack Discovery And Install-Ready Example

**Files:**
- Create: `lobster-intel/examples/thesis-packs/gooaye.json`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Modify: `lobster-intel/scripts/run_thesis_runtime.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_default_workflow.py`

- [ ] **Step 1: Add the install-ready thesis pack example**

```json
{
  "thesis_id": "gooaye",
  "semantic_frame": "military_operations_end_by_deadline",
  "probability_direction": "yes_is_peace",
  "state": "ACTIVE_TRUCE",
  "target_registry": [
    {
      "market_id": "1517836",
      "market_slug": "military-operations-end-by-june-30",
      "market_question": "Military operations end by June 30?",
      "semantic_frame": "military_operations_end_by_deadline",
      "probability_direction": "yes_is_peace",
      "aliases": ["military-operations-end-by-june-30"],
      "resolution_mode": "registry_first"
    }
  ]
}
```

- [ ] **Step 2: Teach runtime input loading to discover thesis packs**

```python
def load_thesis_runtime_inputs(..., thesis_id: str | None = None, ...) -> dict[str, Any]:
    thesis_pack = _load_discovered_thesis_pack(workspace_dir, thesis_id)
    registry_payload = thesis_pack.get("target_registry") or []
    thesis_settings = {
        "semantic_frame": thesis_pack.get("semantic_frame"),
        "probability_direction": thesis_pack.get("probability_direction"),
        "state": thesis_pack.get("state"),
    }
```

- [ ] **Step 3: Apply thesis-pack defaults in the CLI while preserving explicit overrides**

```python
semantic_frame = args.semantic_frame or runtime_inputs["thesis_settings"].get("semantic_frame") or "generic_thesis_frame"
probability_direction = (
    args.probability_direction or runtime_inputs["thesis_settings"].get("probability_direction") or "yes_is_peace"
)
state = args.state or runtime_inputs["thesis_settings"].get("state") or "ACTIVE_TRUCE"
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_default_workflow.py -q`
Expected: PASS

### Task 3: Document The Install-Ready Thesis-Pack Path

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`
- Create: `docs/THESIS_PACKS.md`

- [ ] **Step 1: Document the thesis-pack concept and default discovery path**

```markdown
The install-ready path now includes a thesis pack under `lobster-intel/examples/thesis-packs/`.
The runtime discovers `<thesis-id>.json` there when no explicit registry file is passed.
```

- [ ] **Step 2: Run the focused documentation-linked verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_default_workflow.py -q`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-default-thesis-pack-discovery.md lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_default_workflow.py lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py lobster-intel/scripts/run_thesis_runtime.py lobster-intel/examples/thesis-packs/gooaye.json README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md docs/THESIS_PACKS.md
git commit -m "feat: add thesis pack discovery defaults"
```
