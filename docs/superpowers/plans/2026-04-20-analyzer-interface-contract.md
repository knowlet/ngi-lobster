# Analyzer Interface Contract Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a first-class analyzer contract so source-specific observation shaping becomes explicit, testable, and replaceable instead of being hardcoded inside the thesis runtime spine.

**Architecture:** Extract source-to-observation logic from `runtime_spine.py` into a small analyzer registry that accepts evidence artifacts and returns normalized observation drafts. Keep runtime truth and compare logic in the runtime spine; analyzers only shape observations and metadata, with a legacy fallback analyzer preserved for unknown source types.

**Tech Stack:** Python 3.11, dataclasses or protocols, existing `lobster_runtime` package, pytest

---

### Task 1: Lock The Analyzer Boundary In Tests

**Files:**
- Create: `lobster-intel/tests/test_runtime_analyzers.py`
- Modify: `lobster-intel/tests/test_runtime_spine.py`
- Test: `lobster-intel/tests/test_runtime_analyzers.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Add a failing unit test for market analyzer output**

```python
def test_prediction_market_analyzer_emits_market_candidate_draft():
    evidence_artifact = {
        "artifact_id": "evidence:gooaye:polymarket-tracker:1517836",
        "external_id": "1517836",
        "source_type": "prediction_market",
        "content_refs": [
            {"kind": "title", "value": "Military operations end by June 30?"},
            {"kind": "url", "value": "military-operations-end-by-june-30"},
        ],
        "metadata": {
            "market_id": "1517836",
            "semantic_frame": "military_operations_end_by_deadline",
            "probability_direction": "yes_is_peace",
        },
        "provenance": {"source_ids": ["polymarket"]},
        "checksum": "abc123",
    }

    draft = analyze_evidence_artifact(evidence_artifact)

    assert draft.event_type == "market_candidate"
    assert draft.stance == "market_snapshot"
    assert "market_candidate" in draft.semantic_tags
```

- [ ] **Step 2: Add a failing runtime-spine integration test for fallback analyzer behavior**

```python
def test_build_observations_preserves_generic_fallback_for_unknown_source_types(tmp_path: Path):
    evidence_artifacts = [
        {
            "artifact_id": "evidence:gooaye:custom-source:item-1",
            "external_id": "item-1",
            "source_type": "custom_source",
            "content_refs": [{"kind": "title", "value": "Custom item"}],
            "metadata": {},
            "provenance": {"source_ids": ["custom-source"], "source_paths": [], "source_urls": []},
            "checksum": "abc123",
        }
    ]

    observations = runtime_spine._build_observations(
        ThesisRuntimeInput(thesis_id="gooaye", workspace_dir=tmp_path),
        "20260420T000000Z",
        "2026-04-20T00:00:00+00:00",
        evidence_artifacts,
    )

    assert observations[0]["event_type"] == "custom_source"
    assert observations[0]["stance"] == "escalatory_signal"
```

- [ ] **Step 3: Run focused analyzer tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_analyzers.py lobster-intel/tests/test_runtime_spine.py -k analyzer -q`
Expected: FAIL because no analyzer registry exists and observation shaping still lives entirely inside `runtime_spine.py`

### Task 2: Extract The Analyzer Registry And Runtime Adapter

**Files:**
- Create: `lobster-intel/packages/lobster-runtime/lobster_runtime/analyzers.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py`
- Test: `lobster-intel/tests/test_runtime_analyzers.py`
- Test: `lobster-intel/tests/test_runtime_spine.py`

- [ ] **Step 1: Define the analyzer draft contract and registry**

```python
@dataclass(slots=True)
class ObservationDraft:
    event_type: str
    stance: str
    entity_refs: list[str] = field(default_factory=list)
    semantic_tags: list[str] = field(default_factory=list)
    extractive_rationale: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


def analyze_evidence_artifact(evidence_artifact: dict[str, Any]) -> ObservationDraft:
    source_type = evidence_artifact["source_type"]
    analyzer = ANALYZERS_BY_SOURCE_TYPE.get(source_type, _default_analyzer)
    return analyzer(evidence_artifact)
```

- [ ] **Step 2: Move source-specific shaping out of `runtime_spine.py`**

```python
draft = analyze_evidence_artifact(evidence_artifact)
observation.update(
    {
        "entity_refs": draft.entity_refs or [evidence_artifact["external_id"]],
        "event_type": draft.event_type,
        "stance": draft.stance,
        "semantic_tags": draft.semantic_tags,
        "extractive_rationale": draft.extractive_rationale,
        "metadata": draft.metadata,
    }
)
```

- [ ] **Step 3: Preserve the current semantics through dedicated analyzers**

```python
def _prediction_market_analyzer(evidence_artifact: dict[str, Any]) -> ObservationDraft:
    metadata = _observation_metadata(evidence_artifact)
    return ObservationDraft(
        event_type="market_candidate",
        stance="market_snapshot",
        entity_refs=[metadata.get("market_id")] if metadata.get("market_id") else [],
        semantic_tags=["market_candidate", metadata.get("semantic_frame") or "unknown_semantic_frame"],
        extractive_rationale=_content_ref_value(evidence_artifact.get("content_refs") or [], "title"),
        metadata=metadata,
    )
```

- [ ] **Step 4: Run focused analyzer tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_analyzers.py lobster-intel/tests/test_runtime_spine.py -k 'analyzer or observations' -q`
Expected: PASS

### Task 3: Document The Analyzer Protocol

**Files:**
- Create: `lobster-intel/docs/protocols/ANALYZER_CONTRACT.md`
- Modify: `lobster-intel/docs/architecture/overview.md`
- Modify: `lobster-intel/README.md`

- [ ] **Step 1: Document analyzer ownership and safety boundaries**

```md
Analyzers transform evidence artifacts into normalized observation drafts.
They do not select active targets, compute compare mode, or send delivery.
Those decisions remain runtime-owned.
```

- [ ] **Step 2: Document the fallback rule for new source families**

```md
If no source-specific analyzer is registered, runtime uses the default analyzer
that preserves generic `event_type=source_type` and `stance=escalatory_signal`.
```

- [ ] **Step 3: Run final verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_runtime_analyzers.py lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_source_history.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-analyzer-interface-contract.md lobster-intel/tests/test_runtime_analyzers.py lobster-intel/tests/test_runtime_spine.py lobster-intel/packages/lobster-runtime/lobster_runtime/analyzers.py lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py lobster-intel/docs/protocols/ANALYZER_CONTRACT.md lobster-intel/docs/architecture/overview.md lobster-intel/README.md
git commit -m "feat: add analyzer interface contract"
```
