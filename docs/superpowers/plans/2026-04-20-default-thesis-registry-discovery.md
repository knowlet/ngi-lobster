# Default Thesis Registry Discovery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make `run_thesis_runtime` and the OpenClaw wrapper discover a thesis-specific target registry automatically so install-time runs default to the `registry-first` contract instead of `suppressed` compare mode.

**Architecture:** Extend runtime input loading with a deterministic default registry search rooted in `lobster-intel/data/runtime/thesis-registry/` and keyed by `thesis_id`. Keep explicit `--registry-file` overrides authoritative, add an install-ready sample registry artifact for `gooaye`, and surface the resolved registry path in CLI and plugin outputs. Update docs so the install path explains where thesis registries live and how they participate in runtime truth.

**Tech Stack:** Python 3.11 runtime CLI, Node/OpenClaw wrapper, JSON runtime artifacts, pytest-style tests

---

### Task 1: Lock Default Registry Discovery With Tests

**Files:**
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add a helper that installs a thesis registry under the workspace runtime tree**

```python
def _install_thesis_registry(workspace: Path, thesis_id: str, entries: list[dict]) -> Path:
    registry_path = workspace / "lobster-intel" / "data" / "runtime" / "thesis-registry" / f"{thesis_id}.json"
    registry_path.parent.mkdir(parents=True, exist_ok=True)
    registry_path.write_text(json.dumps(entries), encoding="utf-8")
    return registry_path
```

- [ ] **Step 2: Change the installed-artifact CLI test to expect discovered registry resolution**

```python
registry_path = _install_thesis_registry(tmp_path, "gooaye", _target_registry())
...
assert payload["compare_mode"] == "full_compare"
assert payload["input_contract"]["registry_resolution"]["mode"] == "discovered"
assert payload["input_contract"]["registry_resolution"]["path"] == str(registry_path)
```

- [ ] **Step 3: Add a regression test proving explicit `--registry-file` still wins**

```python
payload = load_thesis_runtime_inputs(
    tmp_path,
    registry_file=explicit_registry_path,
    thesis_id="gooaye",
)
assert payload["registry_resolution"]["mode"] == "explicit"
assert payload["target_registry"][0]["market_id"] == "explicit-target"
```

- [ ] **Step 4: Run the focused test target and verify RED**

Run: `python3 -m pytest lobster-intel/tests/test_runtime_spine.py -q`
Expected: FAIL because default registry discovery is not implemented yet

### Task 2: Implement Runtime Discovery

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Modify: `lobster-intel/scripts/run_thesis_runtime.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add deterministic default registry path helpers**

```python
def _default_registry_candidates(workspace_dir: str | Path, thesis_id: str) -> list[Path]:
    data_root = _workspace_data_dir(workspace_dir) / "runtime" / "thesis-registry"
    return [
        data_root / f"{thesis_id}.json",
        data_root / thesis_id / "registry.json",
    ]
```

- [ ] **Step 2: Teach `load_thesis_runtime_inputs` to discover registries when no explicit file is passed**

```python
elif thesis_id:
    for registry_path in _default_registry_candidates(workspace_dir, thesis_id):
        if registry_path.exists():
            registry_resolution = {"path": str(registry_path), "mode": "discovered", "exists": True}
            registry_payload = cast(list[dict[str, Any]], _load_json_file(registry_path))
            break
```

- [ ] **Step 3: Pass `thesis_id` through the CLI loader path**

```python
runtime_inputs = load_thesis_runtime_inputs(
    args.workspace,
    thesis_id=args.thesis_id,
    ...
)
```

- [ ] **Step 4: Run the focused test target and verify GREEN**

Run: `python3 -m pytest lobster-intel/tests/test_runtime_spine.py -q`
Expected: PASS

### Task 3: Ship Install-Ready Registry Artifacts And Docs

**Files:**
- Create: `lobster-intel/data/runtime/thesis-registry/gooaye.json`
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`

- [ ] **Step 1: Add a default Gooaye thesis registry artifact under runtime data**

```json
[
  {
    "market_id": "1517836",
    "market_slug": "military-operations-end-by-june-30",
    "market_question": "Military operations end by June 30?",
    "semantic_frame": "military_operations_end_by_deadline",
    "probability_direction": "yes_is_peace",
    "aliases": ["operations end by june 30", "june 30 end market"],
    "resolution_mode": "registry_first"
  }
]
```

- [ ] **Step 2: Update top-level docs to describe the default thesis registry path**

```markdown
Default thesis registries now live under `lobster-intel/data/runtime/thesis-registry/`.
`ngi_lobster_run_thesis_runtime` discovers `<thesis_id>.json` automatically when `--registry-file` is not provided; explicit overrides remain authoritative.
```

- [ ] **Step 3: Run a direct CLI smoke and confirm discovered registry metadata**

Run: `python3 lobster-intel/scripts/run_thesis_runtime.py --workspace . --thesis-id gooaye`
Expected: JSON output includes `input_contract.registry_resolution.mode = "discovered"`

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-default-thesis-registry-discovery.md lobster-intel/tests/test_runtime_spine.py lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py lobster-intel/scripts/run_thesis_runtime.py lobster-intel/data/runtime/thesis-registry/gooaye.json README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md
git commit -m "feat: discover default thesis registry"
```
