# Runtime Live Search Fallback Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let the thesis runtime resolve a conservative `live_search_fallback` target from discovered market candidates when no registry match exists, so installed runs can still emit an auditable `degraded_compare` instead of dropping straight to `suppressed`.

**Architecture:** Keep runtime as target owner by deriving the fallback target inside `resolve_active_target()` rather than in delivery or wrapper code. The fallback path must stay explicit in runtime artifacts by setting `resolution_mode="live_search_fallback"` and `fallback_used=true`, and it must only activate when candidate metadata aligns with the requested semantic/numeric contract.

**Tech Stack:** Python 3.11, stdlib `json`/`pathlib`, existing `lobster_runtime`, pytest

**Status:** Implemented in the writable workspace on 2026-04-22. Runtime now resolves conservative live-search fallbacks from aligned discovered market candidates, emits `degraded_compare` for that path, and documents the safety boundary in the install/runtime docs.

---

## Execution Summary

This slice landed as:

- `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- `lobster-intel/tests/test_runtime_spine.py`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `lobster-intel/README.md`

Verified with:

- `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py -q`
- `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`

---

### Task 1: Lock The Fallback Contract With Tests

**Files:**
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [x] **Step 1: Add a failing resolver test for a semantically aligned fallback candidate**

```python
def test_resolve_active_target_uses_live_search_fallback_when_registry_missing():
    inp = ThesisRuntimeInput(
        thesis_id="gooaye",
        workspace_dir=".",
        target_registry=[],
        semantic_frame="military_operations_end_by_deadline",
        probability_direction="yes_is_peace",
    )
    observations = [
        {
            "artifact_id": "observation:market:1517836",
            "event_type": "market_candidate",
            "extractive_rationale": "Military operations end by June 30?",
            "metadata": {
                "market_id": "1517836",
                "market_slug": "military-operations-end-by-june-30",
                "market_question": "Military operations end by June 30?",
                "semantic_frame": "military_operations_end_by_deadline",
                "probability_direction": "yes_is_peace",
                "yes_probability": 0.72,
                "active": True,
                "closed": False,
            },
        }
    ]

    active_target, market_candidate = runtime_spine.resolve_active_target(inp, observations)

    assert active_target["resolution_mode"] == "live_search_fallback"
    assert active_target["fallback_used"] is True
    assert active_target["market_id"] == market_candidate["market_id"] == "1517836"
```

- [x] **Step 2: Add a failing CLI integration test for discovered artifacts without a registry**

```python
def test_run_thesis_runtime_cli_uses_live_search_fallback_without_registry(tmp_path: Path):
    official, watchlist, polymarket = _source_payloads()
    _install_runtime_source_artifacts(tmp_path, official, watchlist, polymarket)

    result = subprocess.run(
        [
            sys.executable,
            "lobster-intel/scripts/run_thesis_runtime.py",
            "--workspace",
            str(tmp_path),
            "--thesis-id",
            "gooaye",
            "--semantic-frame",
            "military_operations_end_by_deadline",
            "--probability-direction",
            "yes_is_peace",
            "--now-utc",
            "2026-04-19T12:30:00+00:00",
        ],
        cwd=repo,
        text=True,
        capture_output=True,
        check=False,
    )

    payload = json.loads(result.stdout)
    assert payload["compare_mode"] == "degraded_compare"
```

- [x] **Step 3: Run focused tests and verify RED**

Run: `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py -q`
Expected: FAIL because `resolve_active_target()` still returns `None` when registry resolution is unavailable

### Task 2: Implement Conservative Fallback Resolution

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [x] **Step 1: Add candidate ranking helpers**

```python
def _candidate_matches_runtime_contract(inp: ThesisRuntimeInput, candidate: dict[str, Any]) -> bool:
    candidate_frame = candidate.get("semantic_frame")
    if candidate_frame and candidate_frame != inp.semantic_frame:
        return False
    candidate_direction = candidate.get("probability_direction") or inp.probability_direction
    if candidate_direction == inp.probability_direction:
        return True
    return (inp.probability_direction, candidate_direction) in SUPPORTED_DIRECTION_NORMALIZATIONS
```

- [x] **Step 2: Emit an explicit fallback target when contract alignment is good enough**

```python
if not inp.target_registry:
    fallback_candidate = _select_live_search_fallback(inp, market_candidates)
    if fallback_candidate is not None:
        return {
            "market_id": fallback_candidate.get("market_id"),
            "market_slug": fallback_candidate.get("market_slug"),
            "market_question": fallback_candidate.get("market_question"),
            "semantic_frame": fallback_candidate.get("semantic_frame") or inp.semantic_frame,
            "probability_direction": fallback_candidate.get("probability_direction") or inp.probability_direction,
            "resolution_mode": "live_search_fallback",
            "resolver_confidence": 0.75,
            "fallback_used": True,
        }, fallback_candidate
```

- [x] **Step 3: Preserve safety when candidates do not align**

```python
fallback_candidate = _select_live_search_fallback(inp, market_candidates)
if fallback_candidate is None:
    return None, market_candidates[0]
```

- [x] **Step 4: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_spine.py -q`
Expected: PASS

### Task 3: Document The New Compare Path

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`

- [x] **Step 1: Document when degraded fallback is expected**

```text
If a thesis run has no shipped or explicit registry match, but the discovered market candidate already matches the requested semantic frame and probability direction, the runtime may promote that candidate as `live_search_fallback`.
```

- [x] **Step 2: State the safety boundary**

```text
This fallback is still runtime-owned truth, not delivery inference. The runtime snapshot records `target_resolution_mode=live_search_fallback`, and compare remains `degraded_compare` until a curated registry entry exists.
```

- [x] **Step 3: Run full verification**

Run: `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-runtime-live-search-fallback.md lobster-intel/tests/test_runtime_spine.py lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md
git commit -m "feat: add runtime live search fallback"
```
