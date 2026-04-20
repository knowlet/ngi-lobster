# Installed Thesis Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an operator-facing catalog surface so an installed OpenClaw user can discover bundled thesis profiles and inspect their runtime defaults before running a thesis workflow.

**Architecture:** Extend the existing JS workflow helper module with catalog/describe helpers that scan `lobster-intel/examples/thesis-profiles`, load bundled thesis metadata, and summarize linked target registries. Wire those helpers into a new OpenClaw-native listing tool while keeping all runtime decision logic in the Python runtime and existing thesis workflow path unchanged.

**Tech Stack:** Node.js ESM, `node:test`, existing `index.js` OpenClaw entry, `thesis-workflow-tool.js`, JSON fixtures under `lobster-intel/examples/`

### Task 1: Lock The Bundled Thesis Catalog Contract With Tests

**Files:**
- Modify: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add failing tests for bundled thesis discovery and description**
- [ ] **Step 2: Run the focused JS test file and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: FAIL because the catalog helpers do not exist yet

### Task 2: Implement The Installed Thesis Catalog Helpers And Tool

**Files:**
- Modify: `thesis-workflow-tool.js`
- Modify: `index.js`
- Modify: `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add metadata-aware catalog helpers in `thesis-workflow-tool.js`**
- [ ] **Step 2: Add a describe helper that loads the linked target registry**
- [ ] **Step 3: Register a new OpenClaw-native catalog tool**
- [ ] **Step 4: Add human-readable metadata to the bundled thesis example**
- [ ] **Step 5: Run the focused JS tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: PASS

### Task 3: Document The Installed Thesis Discovery Path

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`
- Test: `tests/workflow-default-tool.test.js`

- [ ] **Step 1: Document the catalog tool and bundled thesis metadata**
- [ ] **Step 2: Run the focused JS suite and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check index.js && node --check thesis-workflow-tool.js`
Expected: PASS
