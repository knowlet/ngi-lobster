# Installed Thesis Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an operator-facing catalog surface so an installed OpenClaw user can discover bundled thesis profiles and inspect their runtime defaults before running a thesis workflow.

**Architecture:** Extend the existing JS installed-workflow helper with catalog and describe helpers that scan bundled thesis profiles, normalize human-readable metadata, and summarize linked registry entries. Expose that data through a new OpenClaw-native tool while leaving runtime decision logic in the Python runtime and existing installed workflow orchestration unchanged.

**Tech Stack:** Node.js ESM, `node:test`, existing `index.js` OpenClaw entry, `thesis-workflow-tool.js`, bundled JSON fixtures under `lobster-intel/examples/`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for the installed thesis catalog slice.

---

## Execution Summary

This slice landed as:

- `tests/thesis-workflow-tool.test.js`
- `thesis-workflow-tool.js`
- `index.js`
- `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `lobster-intel/README.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js && node --check thesis-workflow-tool.js && node --check index.js`
- `cd /Users/knowlet/ngi-lobster && node --test tests/*.test.js && node --check thesis-workflow-tool.js && node --check index.js && node --check installed-workflow-cli.js && node --check scripts/run_installed_thesis_workflow.js`

### Task 1: Lock The Catalog Contract With Tests

**Files:**
- Modify: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [x] **Step 1: Add failing tests for bundled thesis discovery and description**

```js
test("listBundledThesisProfiles returns bundled thesis metadata sorted by thesis id", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    readdirSync: () => [
      { name: "regional-escalation.json", isFile: () => true },
      { name: "ignore-me.txt", isFile: () => true },
      { name: "oil-shipping.json", isFile: () => true },
    ],
    readFileSync: (value) => {
      if (value.endsWith("regional-escalation.json")) {
        return JSON.stringify({
          thesis_id: "regional-escalation",
          title: "Regional escalation monitor",
          summary: "Tracks military operations end-state risk.",
          semantic_frame: "military_operations_end_by_deadline",
          probability_direction: "yes_is_peace",
          state: "ACTIVE_TRUCE",
          registry_file_path:
            "lobster-intel/examples/target-registries/regional-escalation.json",
        });
      }
      return JSON.stringify({
        thesis_id: "oil-shipping",
        title: "Oil shipping disruption",
        summary: "Tracks chokepoint disruption risk.",
        semantic_frame: "shipping_disruption",
        probability_direction: "yes_is_escalation",
        state: "ELEVATED_RISK",
      });
    },
  });

  assert.deepEqual(catalog.map((entry) => entry.thesisId), [
    "oil-shipping",
    "regional-escalation",
  ]);
  assert.equal(catalog[1].title, "Regional escalation monitor");
});
```

- [x] **Step 2: Run the focused JS test file and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js`
Expected: FAIL because the catalog helpers do not exist yet

### Task 2: Implement Catalog Helpers And OpenClaw Tool

**Files:**
- Modify: `thesis-workflow-tool.js`
- Modify: `index.js`
- Modify: `lobster-intel/examples/thesis-profiles/regional-escalation.json`
- Test: `tests/thesis-workflow-tool.test.js`

- [x] **Step 1: Add metadata-aware thesis catalog helpers**

```js
export function listBundledThesisProfiles(rootDir, io = {}) {
  const profileDir = defaultThesisProfileDir(rootDir);
  return readdirSync(profileDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => profileSummary(rootDir, loadProfile(...)))
    .sort((left, right) => left.thesisId.localeCompare(right.thesisId));
}
```

- [x] **Step 2: Add a detailed describe helper that summarizes linked registry entries**

```js
export function describeBundledThesisProfile(rootDir, thesisId, io = {}) {
  return {
    ...profileSummary(rootDir, profile),
    registry: {
      path: registryPath || null,
      entryCount: registryEntries.length,
      markets: registryEntries.map((entry) => ({
        marketId: entry.market_id || null,
        marketQuestion: entry.market_question || null,
      })),
    },
  };
}
```

- [x] **Step 3: Register `ngi_lobster_list_installed_theses` in `index.js`**

```js
api.registerTool(
  {
    name: "ngi_lobster_list_installed_theses",
    async execute(input) {
      const request = input || {};
      const details = request.thesisId
        ? describeBundledThesisProfile(rootDir, request.thesisId)
        : { theses: listBundledThesisProfiles(rootDir) };
      return {
        content: [{ type: "text", text: JSON.stringify(details) }],
        details,
      };
    },
  },
  { name: "ngi_lobster_list_installed_theses" },
);
```

- [x] **Step 4: Add human-readable metadata to the bundled regional escalation profile**

```json
{
  "title": "Regional escalation monitor",
  "summary": "Tracks the active military-operations end-state thesis and bundled market target defaults."
}
```

- [x] **Step 5: Run the focused JS tests and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/thesis-workflow-tool.test.js && node --check thesis-workflow-tool.js && node --check index.js`
Expected: PASS

### Task 3: Document The Installed Thesis Discovery Path

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/README.md`

- [x] **Step 1: Document the catalog tool and bundled thesis metadata surface**

```md
- `ngi_lobster_list_installed_theses`
  - lists bundled thesis ids, titles, runtime defaults, and linked registry paths
  - accepts an optional `thesisId` for a detailed single-thesis view
```

- [x] **Step 2: Run the focused JS suite and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check thesis-workflow-tool.js && node --check index.js`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-installed-thesis-catalog.md tests/thesis-workflow-tool.test.js thesis-workflow-tool.js index.js lobster-intel/examples/thesis-profiles/regional-escalation.json README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md
git commit -m "feat: add installed thesis catalog"
```
