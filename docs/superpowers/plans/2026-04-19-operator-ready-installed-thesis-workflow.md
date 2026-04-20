# Operator-Ready Installed Thesis Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed OpenClaw thesis workflow usable with bundled defaults by adding a thesis profile and target registry path that the OpenClaw-native tool can resolve automatically.

**Architecture:** Keep the new installed workflow orchestration at the JS wrapper boundary, but add a bundled `thesis-profiles/` example layer that defines runtime defaults such as `semantic_frame`, `probability_direction`, `state`, and a target registry file. The orchestrator should load that profile from `thesisId`, merge explicit request overrides on top, then run the existing source plugins and thesis runtime without changing the Python runtime contracts.

**Tech Stack:** Node.js ESM, `node:test`, JSON example fixtures under `lobster-intel/examples/`, existing `thesis-workflow-tool.js`, `index.js`

**Status:** Implemented on 2026-04-19. This plan now serves as the execution record for bundled thesis profile defaults.

---

## Execution Summary

This slice landed as:

- `thesis-workflow-tool.js`
- `tests/thesis-workflow-tool.test.js`
- `index.js`
- `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- `lobster-intel/examples/target-registries/regional-escalation.json`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `lobster-intel/README.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
- `cd /Users/knowlet/ngi-lobster && node --check index.js && node --check thesis-workflow-tool.js`

### Task 1: Lock Thesis Profile Resolution With Tests

**Files:**
- Modify: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add failing tests for bundled thesis profile loading**

```js
test("loadBundledThesisProfile resolves the thesisId profile path by default", () => {
  const profile = loadBundledThesisProfile("/repo", { thesisId: "regional-escalation" }, {
    existsSync: (value) => value.endsWith("regional-escalation.json"),
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        semantic_frame: "military_operations_end_by_deadline",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
        registry_file_path: "lobster-intel/examples/target-registries/regional-escalation.json",
      }),
  });

  assert.equal(profile.semantic_frame, "military_operations_end_by_deadline");
});

test("buildInstalledThesisWorkflow applies thesis profile defaults before explicit overrides", () => {
  const workflow = buildInstalledThesisWorkflow(
    "/repo",
    {
      thesisId: "regional-escalation",
      state: "ESCALATING",
    },
    {
      thesis_id: "regional-escalation",
      semantic_frame: "military_operations_end_by_deadline",
      probability_direction: "yes_is_peace",
      state: "ACTIVE_TRUCE",
      registry_file_path: "lobster-intel/examples/target-registries/regional-escalation.json",
    },
  );

  assert.equal(workflow.runtimeRequest.semanticFrame, "military_operations_end_by_deadline");
  assert.equal(workflow.runtimeRequest.state, "ESCALATING");
  assert.equal(
    workflow.runtimeRequest.registryFilePath,
    "/repo/lobster-intel/examples/target-registries/regional-escalation.json",
  );
});
```

- [ ] **Step 2: Run the focused test file and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: FAIL because thesis profile loading helpers do not exist yet

### Task 2: Implement Bundled Thesis Profile Support

**Files:**
- Modify: `thesis-workflow-tool.js`
- Modify: `index.js`
- Create: `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- Create: `lobster-intel/examples/target-registries/regional-escalation.json`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add thesis profile loading and path resolution**

```js
export function loadBundledThesisProfile(rootDir, request = {}, io = {}) {
  const profilePath =
    request.thesisProfilePath ||
    path.join(rootDir, "lobster-intel", "examples", "thesis-profiles", `${request.thesisId}.json`);
  if (!request.thesisId || !io.existsSync(profilePath)) {
    return null;
  }
  return JSON.parse(io.readFileSync(profilePath, "utf8"));
}
```

- [ ] **Step 2: Merge profile defaults into the installed workflow request**

```js
const registryFilePath =
  request.registryFilePath ||
  resolveProfileRelativePath(rootDir, profile?.registry_file_path);

const semanticFrame = request.semanticFrame || profile?.semantic_frame;
const probabilityDirection =
  request.probabilityDirection || profile?.probability_direction;
const state = request.state || profile?.state;
```

- [ ] **Step 3: Add bundled example fixtures**

```json
{
  "thesis_id": "regional-escalation",
  "semantic_frame": "military_operations_end_by_deadline",
  "probability_direction": "yes_is_peace",
  "state": "ACTIVE_TRUCE",
  "registry_file_path": "lobster-intel/examples/target-registries/regional-escalation.json"
}
```

- [ ] **Step 4: Run focused tests and verify GREEN**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: PASS

### Task 3: Document The Bundled Default Thesis Path

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`
- Test: `tests/workflow-default-tool.test.js`

- [ ] **Step 1: Document thesis profile defaults in the install surface**

```md
The installed workflow tool now resolves bundled thesis defaults from:

- `lobster-intel/examples/thesis-profiles/<thesis-id>.json`
- `lobster-intel/examples/target-registries/<thesis-id>.json`
```

- [ ] **Step 2: Run the focused JS suite and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check index.js && node --check thesis-workflow-tool.js`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/thesis-workflow-tool.test.js thesis-workflow-tool.js index.js README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md lobster-intel/examples/thesis-profiles/regional-escalation.json lobster-intel/examples/target-registries/regional-escalation.json docs/superpowers/plans/2026-04-19-operator-ready-installed-thesis-workflow.md
git commit -m "feat: add bundled thesis profile defaults"
```
