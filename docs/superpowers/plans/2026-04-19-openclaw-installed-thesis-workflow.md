# OpenClaw Installed Thesis Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose an OpenClaw-native tool that runs the installed source trackers and then the thesis runtime so `openclaw plugins install` becomes a real operator workflow surface instead of only a thin runtime wrapper.

**Architecture:** Add a small JS orchestration module beside the plugin entry. It should resolve default source-pack files from `lobster-intel/examples/source-packs`, run `official-statements-tracker`, `watchlist-tracker`, and `polymarket-tracker` through the existing Python source-runner CLI, then invoke the existing thesis runtime CLI with the refreshed artifacts. Keep the runtime spine and tracker internals unchanged; the new work stays at the OpenClaw wrapper boundary.

**Tech Stack:** Node.js ESM, `node:test`, existing `index.js` OpenClaw entry, `lobster-intel/scripts/run_source_plugin.py`, `lobster-intel/scripts/run_thesis_runtime.py`

### Task 1: Lock The Installed Workflow Contract With Tests

**Files:**
- Create: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Write the failing orchestrator tests**
- [ ] **Step 2: Run the new tests and verify RED**

Run: `node --test tests/thesis-workflow-tool.test.js`
Expected: FAIL because `thesis-workflow-tool.js` and its exported workflow helpers do not exist yet

### Task 2: Implement The OpenClaw Installed Workflow Tool

**Files:**
- Create: `thesis-workflow-tool.js`
- Modify: `index.js`
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add the JS orchestrator module**
- [ ] **Step 2: Wire a new OpenClaw tool in `index.js`**
- [ ] **Step 3: Document the new tool as part of the install surface**
- [ ] **Step 4: Run the focused JS tests and verify GREEN**

Run: `node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
Expected: PASS
