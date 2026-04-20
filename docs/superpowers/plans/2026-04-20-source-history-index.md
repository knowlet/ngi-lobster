# Source History And Index Rebuild Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add replayable source-run history and a rebuildable per-plugin SQLite index on top of existing source runtime artifacts.

**Architecture:** Introduce a small `lobster_runtime.source_history` module that reads `runs/*.json` as runtime truth, exposes a replay helper, and rebuilds `index.sqlite` for one source plugin. Keep the source runner unchanged except for sharing the artifact contract through the new helpers and a thin CLI.

**Tech Stack:** Python 3.11+, stdlib `json`/`sqlite3`/`argparse`, existing `lobster_runtime`, `unittest`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for source history replay tooling.

---

## Execution Summary

This slice landed as:

- `docs/superpowers/specs/2026-04-20-source-history-design.md`
- `docs/superpowers/plans/2026-04-20-source-history-index.md`
- `lobster-intel/tests/test_source_history.py`
- `lobster-intel/packages/lobster-runtime/lobster_runtime/source_history.py`
- `lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py`
- `lobster-intel/scripts/source_history.py`
- `lobster-intel/README.md`
- `docs/INSTALL_OPENCLAW.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m unittest discover -s lobster-intel/tests -p 'test_source_history.py' -v`
- `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`

### Task 1: Lock The Source History Contract With Tests

**Files:**
- Create: `lobster-intel/tests/test_source_history.py`

- [ ] **Step 1: Write the failing replay and rebuild tests**

```python
def test_replay_source_run_returns_historical_payload(tmp_path: Path):
    plugin_id, run_id = install_source_run_fixture(tmp_path)
    replay = replay_source_run(tmp_path, plugin_id, run_id)
    self.assertEqual(replay["run_id"], run_id)
    self.assertEqual(replay["evidence_item_count"], 2)
    self.assertEqual(replay["items"][0]["external_id"], "stmt-1")


def test_rebuild_source_index_recreates_sqlite_rows(tmp_path: Path):
    plugin_id, _ = install_source_run_fixture(tmp_path)
    result = rebuild_source_index(tmp_path, plugin_id)
    self.assertEqual(result["run_count"], 2)
    self.assertEqual(result["item_count"], 3)
```

- [ ] **Step 2: Run the focused test file and verify RED**

Run: `python3 -m unittest discover -s lobster-intel/tests -p 'test_source_history.py' -v`
Expected: FAIL with missing `replay_source_run` / `rebuild_source_index` imports

- [ ] **Step 3: Add CLI coverage in the same test file**

```python
payload = json.loads(
    subprocess.check_output(
        [
            sys.executable,
            "lobster-intel/scripts/source_history.py",
            "replay",
            "--workspace",
            str(tmp_path),
            "--plugin-id",
            plugin_id,
            "--run-id",
            run_id,
        ],
        text=True,
    )
)
self.assertEqual(payload["run_id"], run_id)
```

- [ ] **Step 4: Run the focused test file again and verify RED**

Run: `python3 -m unittest discover -s lobster-intel/tests -p 'test_source_history.py' -v`
Expected: FAIL because the CLI script does not exist yet

### Task 2: Implement Source History Helpers And CLI

**Files:**
- Create: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_history.py`
- Create: `lobster-intel/scripts/source_history.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py`

- [ ] **Step 1: Implement artifact loading and replay helpers**

```python
def replay_source_run(workspace_dir: str | Path, plugin_id: str, run_id: str) -> dict[str, Any]:
    artifact_path = _source_run_path(workspace_dir, plugin_id, run_id)
    payload = _load_json(artifact_path)
    return {
        "plugin": payload["plugin"],
        "run_id": payload["run_id"],
        "artifact_path": str(artifact_path),
        "state_path": (payload.get("evidence") or {}).get("state_path"),
        "evidence_item_count": len((payload.get("evidence") or {}).get("items") or []),
        "items": [...],
    }
```

- [ ] **Step 2: Implement the SQLite rebuild path**

```python
with sqlite3.connect(index_path) as conn:
    conn.execute(
        "create table source_runs (run_id text primary key, plugin text, ran_at_utc text, artifact_path text, evidence_item_count integer, new_count integer, state_path text)"
    )
    conn.execute(
        "create table source_items (item_id text primary key, run_id text, source_id text, external_id text, title text, url text, published_at_utc text, collected_at_utc text, source_type text, artifact_path text)"
    )
```

- [ ] **Step 3: Add a thin CLI with `replay` and `rebuild-index` subcommands**

```python
replay_ap = subparsers.add_parser("replay")
replay_ap.add_argument("--plugin-id", required=True)
replay_ap.add_argument("--run-id", required=True)

rebuild_ap = subparsers.add_parser("rebuild-index")
rebuild_ap.add_argument("--plugin-id", required=True)
```

- [ ] **Step 4: Run the focused tests and verify GREEN**

Run: `python3 -m unittest discover -s lobster-intel/tests -p 'test_source_history.py' -v`
Expected: PASS

### Task 3: Update Operator Docs

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [ ] **Step 1: Document source replay and index rebuild**

```text
python3 lobster-intel/scripts/source_history.py replay --workspace . --plugin-id watchlist-tracker --run-id 20260415T013020Z
python3 lobster-intel/scripts/source_history.py rebuild-index --workspace . --plugin-id watchlist-tracker
```

- [ ] **Step 2: Run the focused tests after doc-touching code stays green**

Run: `python3 -m unittest discover -s lobster-intel/tests -p 'test_source_history.py' -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add docs/superpowers/specs/2026-04-20-source-history-design.md docs/superpowers/plans/2026-04-20-source-history-index.md lobster-intel/tests/test_source_history.py lobster-intel/packages/lobster-runtime/lobster_runtime/source_history.py lobster-intel/packages/lobster-runtime/lobster_runtime/__init__.py lobster-intel/scripts/source_history.py lobster-intel/README.md docs/INSTALL_OPENCLAW.md
git commit -m "feat: add source history replay tooling"
```
