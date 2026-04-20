# Installed Workflow Source State Defaults Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed thesis workflow persist source cursors into default runtime storage without manual environment-variable wiring.

**Architecture:** Keep source plugin execution inside the existing JS installed-workflow wrapper, but assign each bundled source plugin a default `statePath` under `lobster-intel/data/runtime/sources/`. Pass that path through the source-plugin CLI so tracker plugins continue to own cursor load/save behavior while the installed workflow defines the default storage contract.

**Tech Stack:** Node.js ESM, `node:test`, Python 3.11, `unittest`, existing `thesis-workflow-tool.js`, `index.js`, `lobster-intel/scripts/run_source_plugin.py`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for installed workflow source state defaults.

---

## Execution Summary

This slice landed as:

- `thesis-workflow-tool.js`
- `index.js`
- `lobster-intel/scripts/run_source_plugin.py`
- `tests/thesis-workflow-tool.test.js`
- `lobster-intel/tests/test_source_runner_e2e.py`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `lobster-intel/README.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
- `cd /Users/knowlet/ngi-lobster && node --check index.js && node --check thesis-workflow-tool.js`
- `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_source_runner_e2e.py lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_default_workflow.py -q`

### Task 1: Lock Installed Workflow State Paths With Tests

**Files:**
- Modify: `tests/thesis-workflow-tool.test.js`
- Modify: `lobster-intel/tests/test_source_runner_e2e.py`
- Test: `tests/thesis-workflow-tool.test.js`
- Test: `lobster-intel/tests/test_source_runner_e2e.py`

- [ ] **Step 1: Add a failing JS test for default source state paths**

```js
assert.deepEqual(
  workflow.sourceRuns.map((run) => [run.pluginId, run.statePath]),
  [
    [
      "official-statements-tracker",
      "/repo/lobster-intel/data/runtime/sources/official-statements.json",
    ],
    [
      "watchlist-tracker",
      "/repo/lobster-intel/data/runtime/sources/watchlist.json",
    ],
    [
      "polymarket-tracker",
      "/repo/lobster-intel/data/runtime/sources/polymarket.json",
    ],
  ],
);
```

- [ ] **Step 2: Add a failing JS test for explicit state-path overrides**

```js
assert.equal(
  workflow.sourceRuns[0].statePath,
  "/repo/custom/official-state.json",
);
```

- [ ] **Step 3: Add a failing Python E2E test for `--state-path`**

```python
self.assertEqual(payload["state_path"], str(state_path))
self.assertTrue(state_path.exists())
saved_state = json.loads(state_path.read_text(encoding="utf-8"))
self.assertIn("watch-test", saved_state["cursors"])
```

- [ ] **Step 4: Run focused tests and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js && .venv/bin/python -m pytest lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: FAIL because installed workflow source runs do not expose `statePath` and the source-plugin CLI does not accept `--state-path`

### Task 2: Implement Default Source State Wiring

**Files:**
- Modify: `thesis-workflow-tool.js`
- Modify: `index.js`
- Modify: `lobster-intel/scripts/run_source_plugin.py`
- Test: `tests/thesis-workflow-tool.test.js`
- Test: `lobster-intel/tests/test_source_runner_e2e.py`

- [ ] **Step 1: Add bundled default state-path metadata per source plugin**

```js
{
  pluginId: "official-statements-tracker",
  requestField: "officialStatementsConfigPath",
  stateRequestField: "officialStatementsStatePath",
  defaultConfig: "official-statements.json",
  defaultState: "official-statements.json",
}
```

- [ ] **Step 2: Resolve `statePath` for each installed source run**

```js
statePath:
  resolveRepoPath(rootDir, request[spec.stateRequestField]) ||
  resolveRepoPath(rootDir, thesisProfile?.source_state_paths?.[spec.pluginId]) ||
  path.join(rootDir, "lobster-intel", "data", "runtime", "sources", spec.defaultState),
```

- [ ] **Step 3: Pass the state path through the source-plugin CLI**

```js
if (statePath) {
  cliArgs.push("--state-path", statePath);
}
```

- [ ] **Step 4: Inject the explicit state path into normalized Python source-plugin config**

```python
normalized_config = normalize_source_plugin_config(args.plugin_dir, config) or {}
if args.state_path:
    normalized_config["state_path"] = args.state_path
result = run_source_plugin(args.plugin_dir, args.workspace, config=normalized_config)
```

- [ ] **Step 5: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js && .venv/bin/python -m pytest lobster-intel/tests/test_source_runner_e2e.py -q`
Expected: PASS

### Task 3: Document Installed Source Cursor Defaults

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`

- [ ] **Step 1: Document the default source state paths**

```md
Installed source trackers now persist cursor state by default under:

- `lobster-intel/data/runtime/sources/official-statements.json`
- `lobster-intel/data/runtime/sources/watchlist.json`
- `lobster-intel/data/runtime/sources/polymarket.json`
```

- [ ] **Step 2: Explain that the installed workflow sets these paths automatically**

```md
The native installed workflow passes these state paths into the source plugin runtime automatically, so repeated runs reuse cursors without extra environment-variable wiring.
```

- [ ] **Step 3: Run end-to-end verification**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && .venv/bin/python -m pytest lobster-intel/tests/test_source_runner_e2e.py lobster-intel/tests/test_runtime_spine.py lobster-intel/tests/test_default_workflow.py -q`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-installed-workflow-source-state-defaults.md tests/thesis-workflow-tool.test.js thesis-workflow-tool.js index.js lobster-intel/scripts/run_source_plugin.py lobster-intel/tests/test_source_runner_e2e.py README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md
git commit -m "feat: wire installed workflow source state defaults"
```
