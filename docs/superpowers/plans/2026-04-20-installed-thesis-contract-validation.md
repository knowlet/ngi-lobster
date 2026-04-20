# Installed Thesis Contract Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the installed thesis workflow fail closed when a bundled thesis profile is missing or incomplete, and expose operator-facing contract health through the installed thesis catalog.

**Architecture:** Extend the existing JS thesis workflow helper so bundled thesis profiles are treated as an install-surface contract, not just loose metadata. The helper should validate runtime defaults and referenced files before launching source plugins, and the catalog should surface the same validation result through `contractStatus` and `validationErrors`. Keep runtime truth in the Python spine; the JS layer only validates install-time/default wiring.

**Tech Stack:** Node.js ESM, `node:test`, OpenClaw plugin entry in `index.js`, thesis workflow helper in `thesis-workflow-tool.js`, bundled JSON fixtures under `lobster-intel/examples/`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for the profile-contract validation slice.

---

## Execution Summary

This slice landed as:

- `thesis-workflow-tool.js`
- `tests/thesis-workflow-tool.test.js`
- `index.js`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `docs/THESIS_PROFILES.md`
- `lobster-intel/README.md`
- `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- `lobster-intel/examples/target-registries/regional-escalation.json`

Verified with:

- `node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
- `node --check index.js`
- `node --check thesis-workflow-tool.js`

### Task 1: Lock The Profile Contract In Tests

**Files:**
- Create: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add tests for bundled thesis discovery and validation**

```js
test("describeBundledThesisProfile flags incomplete runtime contracts", () => {
  const description = describeBundledThesisProfile("/repo", "regional-escalation", {
    existsSync: () => true,
    readFileSync: () => JSON.stringify({
      thesis_id: "regional-escalation",
      probability_direction: "yes_is_peace",
      state: "ACTIVE_TRUCE",
    }),
  });

  assert.equal(description.contractStatus, "incomplete");
  assert.match(description.validationErrors[0], /semanticFrame/);
});

test("runInstalledThesisWorkflow stops when thesis profile defaults are unavailable", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: { thesisId: "unknown-thesis" },
    existsSync: () => false,
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.kind, "invalid_profile");
});
```

- [ ] **Step 2: Run the focused JS suite and verify RED**

Run: `cd /Users/knowlet/.codex/worktrees/8b78/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: FAIL because the helper does not expose validation state yet

### Task 2: Implement Contract Validation And Surface It In The Catalog

**Files:**
- Create: `thesis-workflow-tool.js`
- Modify: `index.js`
- Modify: `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add contract validation to the workflow helper**

```js
function validateInstalledWorkflowContract(request, thesisProfile, workflow) {
  const errors = [];
  if (!thesisProfile) {
    errors.push(`No bundled thesis profile found for "${request.thesisId}".`);
    return errors;
  }
  if (!workflow.runtimeRequest.semanticFrame) {
    errors.push(`Thesis profile "${request.thesisId}" does not resolve semanticFrame.`);
  }
  if (!workflow.runtimeRequest.registryFilePath) {
    errors.push(`Thesis profile "${request.thesisId}" does not resolve registryFilePath.`);
  }
  return errors;
}
```

- [ ] **Step 2: Expose validation state in list/describe helpers**

```js
return profileSummary(rootDir, thesisProfile, {
  contractStatus: validationErrors.length === 0 ? "ready" : "incomplete",
  validationErrors,
});
```

- [ ] **Step 3: Stop the installed workflow before execution when the contract is incomplete**

```js
if (validationErrors.length > 0) {
  return {
    kind: "invalid_profile",
    validationErrors,
    workflow,
    thesisProfile,
  };
}
```

- [ ] **Step 4: Make the bundled profile self-describing**

```json
"source_config_paths": {
  "official-statements-tracker": "lobster-intel/examples/source-packs/official-statements.json",
  "watchlist-tracker": "lobster-intel/examples/source-packs/watchlist.json",
  "polymarket-tracker": "lobster-intel/examples/source-packs/polymarket.json"
}
```

- [ ] **Step 5: Run the focused suite and verify GREEN**

Run: `cd /Users/knowlet/.codex/worktrees/8b78/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: PASS

### Task 3: Document The Thesis Profile Contract

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Create: `docs/THESIS_PROFILES.md`
- Modify: `lobster-intel/README.md`

- [ ] **Step 1: Document the new validation behavior and profile contract**

```md
- `ngi_lobster_list_installed_theses`
  - exposes `contractStatus` and `validationErrors`
- `ngi_lobster_run_installed_thesis_workflow`
  - fails closed when thesis defaults are missing or incomplete
```

- [ ] **Step 2: Run final verification**

Run: `cd /Users/knowlet/.codex/worktrees/8b78/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check index.js && node --check thesis-workflow-tool.js`
Expected: PASS
