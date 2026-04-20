# Tracker Capability Surface Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give source trackers a structured capability contract so plugin onboarding, replay expectations, and downstream follow-up queues stop depending on ad hoc manifest conventions.

**Architecture:** Keep third-party-style dependency flags in the existing flat `capabilities` list, but add a repo-owned `tracker` contract that describes source family, replay semantics, state mode, and follow-up queue outputs in a machine-readable way. Validation should live in `lobster-plugins` manifest loading so runtime and operator tooling can trust plugin metadata without re-implementing manifest rules.

**Tech Stack:** Python 3.11, dataclasses, existing `lobster_plugins` manifest loader, pytest, JSON plugin manifests under `lobster-intel/plugins/`

---

### Task 1: Lock The Tracker Contract In Tests

**Files:**
- Modify: `lobster-intel/tests/test_plugin_manifest.py`
- Test: `lobster-intel/tests/test_plugin_manifest.py`

- [ ] **Step 1: Add a failing test for structured tracker metadata**

```python
def test_gooaye_manifest_loads_tracker_contract():
    manifest_path = Path(__file__).resolve().parents[1] / "plugins" / "gooaye-tracker" / "plugin.json"
    manifest = read_manifest(manifest_path)

    assert manifest.tracker.source_family == "telegram_channel"
    assert manifest.tracker.state_mode == "cursor_json"
    assert manifest.tracker.replayable is True
    assert manifest.tracker.follow_up_queues == ["linked_content_queue", "image_analysis_queue"]
```

- [ ] **Step 2: Add a failing validation test for inconsistent queue declarations**

```python
def test_manifest_rejects_runtime_queue_output_without_tracker_contract(tmp_path: Path):
    manifest_path = tmp_path / "plugin.json"
    manifest_path.write_text(
        json.dumps(
            {
                "id": "broken-tracker",
                "name": "Broken Tracker",
                "version": "0.1.0",
                "type": "ingest",
                "entrypoints": {"ingest": "plugin.py:ingest"},
                "produces": ["runtime.linked_content_queue"],
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="tracker.follow_up_queues"):
        read_manifest(manifest_path)
```

- [ ] **Step 3: Run the focused manifest tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_plugin_manifest.py -q`
Expected: FAIL because `PluginManifest` does not parse or validate a structured tracker contract yet

### Task 2: Implement Structured Tracker Capability Parsing

**Files:**
- Modify: `lobster-intel/packages/lobster-plugins/lobster_plugins/manifest.py`
- Modify: `lobster-intel/packages/lobster-plugins/lobster_plugins/contracts.py`
- Modify: `lobster-intel/plugins/gooaye-tracker/plugin.json`
- Modify: `lobster-intel/plugins/official-statements-tracker/plugin.json`
- Modify: `lobster-intel/plugins/watchlist-tracker/plugin.json`
- Modify: `lobster-intel/plugins/polymarket-tracker/plugin.json`
- Test: `lobster-intel/tests/test_plugin_manifest.py`

- [ ] **Step 1: Add tracker contract dataclasses to the manifest layer**

```python
@dataclass(slots=True)
class TrackerContract:
    source_family: str
    default_source_type: str | None = None
    replayable: bool = True
    state_mode: str = "cursor_json"
    follow_up_queues: list[str] = field(default_factory=list)


@dataclass(slots=True)
class PluginManifest:
    ...
    tracker: TrackerContract | None = None
```

- [ ] **Step 2: Parse and validate tracker metadata while keeping flat capabilities**

```python
def _read_tracker_contract(raw: dict[str, Any], produces: list[str]) -> TrackerContract | None:
    tracker_raw = raw.get("tracker")
    if tracker_raw is None:
        if any(value.startswith("runtime.") and value.endswith("_queue") for value in produces):
            raise ValueError("runtime queue outputs require tracker.follow_up_queues")
        return None
    contract = TrackerContract(
        source_family=tracker_raw["source_family"],
        default_source_type=tracker_raw.get("default_source_type"),
        replayable=tracker_raw.get("replayable", True),
        state_mode=tracker_raw.get("state_mode", "cursor_json"),
        follow_up_queues=list(tracker_raw.get("follow_up_queues") or []),
    )
    expected_outputs = {f"runtime.{queue_name}" for queue_name in contract.follow_up_queues}
    missing_outputs = expected_outputs.difference(produces)
    if missing_outputs:
        raise ValueError(f"tracker.follow_up_queues missing produces entries: {sorted(missing_outputs)}")
    return contract
```

- [ ] **Step 3: Update reference tracker manifests to declare the new contract**

```json
"tracker": {
  "source_family": "telegram_channel",
  "default_source_type": "telegram_post",
  "replayable": true,
  "state_mode": "cursor_json",
  "follow_up_queues": ["linked_content_queue", "image_analysis_queue"]
}
```

- [ ] **Step 4: Run the focused manifest tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_plugin_manifest.py -q`
Expected: PASS

### Task 3: Expose The Tracker Contract In Loader Docs

**Files:**
- Modify: `lobster-intel/docs/protocols/PLUGIN_CONTRACT.md`
- Modify: `lobster-intel/docs/architecture/plugin-system.md`
- Modify: `lobster-intel/README.md`

- [ ] **Step 1: Document the split between external dependency capabilities and tracker contract**

```md
- `capabilities`: external or execution capabilities such as `web_fetch`, `ocr`, `image_understanding`
- `tracker`: repo-owned source contract describing replayability, source family, state mode, and follow-up queues
```

- [ ] **Step 2: Add the Gooaye tracker as the reference manifest example**

```md
The Gooaye tracker now declares `tracker.source_family=telegram_channel` and
`tracker.follow_up_queues=["linked_content_queue", "image_analysis_queue"]`,
which downstream tooling can trust without source-specific branching.
```

- [ ] **Step 3: Run final verification**

Run: `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_plugin_manifest.py lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-tracker-capability-surface.md lobster-intel/tests/test_plugin_manifest.py lobster-intel/packages/lobster-plugins/lobster_plugins/manifest.py lobster-intel/packages/lobster-plugins/lobster_plugins/contracts.py lobster-intel/plugins/gooaye-tracker/plugin.json lobster-intel/plugins/official-statements-tracker/plugin.json lobster-intel/plugins/watchlist-tracker/plugin.json lobster-intel/plugins/polymarket-tracker/plugin.json lobster-intel/docs/protocols/PLUGIN_CONTRACT.md lobster-intel/docs/architecture/plugin-system.md lobster-intel/README.md
git commit -m "feat: add tracker capability contract"
```
