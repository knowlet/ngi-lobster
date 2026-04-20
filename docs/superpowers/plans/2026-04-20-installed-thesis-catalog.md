# Installed Thesis Catalog Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an operator-facing catalog surface so an installed OpenClaw user can discover bundled thesis profiles and inspect their runtime defaults before running a thesis workflow.

**Architecture:** Extend the existing JS workflow helper module with catalog/describe helpers that scan `lobster-intel/examples/thesis-profiles`, load bundled thesis metadata, and summarize linked target registries. Wire those helpers into a new OpenClaw-native listing tool while keeping all runtime decision logic in the Python runtime and existing thesis workflow path unchanged.

**Tech Stack:** Node.js ESM, `node:test`, existing `index.js` OpenClaw entry, `thesis-workflow-tool.js`, JSON fixtures under `lobster-intel/examples/`

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

- `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check index.js && node --check thesis-workflow-tool.js`

### Task 1: Lock The Bundled Thesis Catalog Contract With Tests

**Files:**
- Modify: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Add failing tests for bundled thesis discovery and description**

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
  assert.equal(catalog[1].registryFilePath, "/repo/lobster-intel/examples/target-registries/regional-escalation.json");
});

test("describeBundledThesisProfile summarizes registry entries for a thesis", () => {
  const description = describeBundledThesisProfile("/repo", "regional-escalation", {
    existsSync: () => true,
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
      return JSON.stringify([
        {
          market_id: "1517836",
          market_question: "Military operations end by June 30?",
        },
      ]);
    },
  });

  assert.equal(description.thesisId, "regional-escalation");
  assert.equal(description.registry.entryCount, 1);
  assert.equal(description.registry.markets[0].marketId, "1517836");
});
```

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

```js
export function listBundledThesisProfiles(rootDir, io = {}) {
  const readdirSync = io.readdirSync || fs.readdirSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profileDir = path.join(rootDir, "lobster-intel", "examples", "thesis-profiles");

  return readdirSync(profileDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => {
      const profilePath = path.join(profileDir, entry.name);
      const profile = JSON.parse(readFileSync(profilePath, "utf8"));
      return {
        thesisId: profile.thesis_id,
        title: profile.title || profile.thesis_id,
        summary: profile.summary || "",
        semanticFrame: profile.semantic_frame,
        probabilityDirection: profile.probability_direction,
        state: profile.state,
        profilePath,
        registryFilePath: resolveRepoPath(rootDir, profile.registry_file_path),
      };
    })
    .sort((left, right) => left.thesisId.localeCompare(right.thesisId));
}
```

- [ ] **Step 2: Add a describe helper that loads the linked target registry**

```js
export function describeBundledThesisProfile(rootDir, thesisId, io = {}) {
  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profile = loadBundledThesisProfile(rootDir, { thesisId }, { existsSync, readFileSync });
  if (!profile) {
    return null;
  }

  const registryPath = resolveRepoPath(rootDir, profile.registry_file_path);
  const registryEntries =
    registryPath && existsSync(registryPath)
      ? JSON.parse(readFileSync(registryPath, "utf8"))
      : [];

  return {
    thesisId: profile.thesis_id,
    title: profile.title || profile.thesis_id,
    summary: profile.summary || "",
    semanticFrame: profile.semantic_frame,
    probabilityDirection: profile.probability_direction,
    state: profile.state,
    profilePath: profile.profile_path,
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

- [ ] **Step 3: Register a new OpenClaw-native catalog tool**

```js
api.registerTool(
  {
    name: "ngi_lobster_list_installed_theses",
    label: "NGI Lobster List Installed Theses",
    description:
      "List bundled thesis profiles and their runtime defaults for the installed thesis workflow.",
    parameters: {
      type: "object",
      additionalProperties: false,
      properties: {
        thesisId: {
          type: "string",
          description: "Optional thesis id to return a single detailed profile view.",
        },
      },
    },
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

- [ ] **Step 4: Add human-readable metadata to the bundled thesis example**

```json
{
  "thesis_id": "regional-escalation",
  "title": "Regional escalation monitor",
  "summary": "Tracks the active military-operations end-state thesis and bundled market target defaults.",
  "semantic_frame": "military_operations_end_by_deadline",
  "probability_direction": "yes_is_peace",
  "state": "ACTIVE_TRUCE",
  "registry_file_path": "lobster-intel/examples/target-registries/regional-escalation.json"
}
```

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

```md
- `ngi_lobster_list_installed_theses`
  - lists bundled thesis ids, titles, runtime defaults, and linked registry paths
  - accepts an optional `thesisId` to return a detailed single-thesis view
```

- [ ] **Step 2: Run the focused JS suite and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js && node --check index.js && node --check thesis-workflow-tool.js`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add tests/thesis-workflow-tool.test.js thesis-workflow-tool.js index.js README.md docs/INSTALL_OPENCLAW.md lobster-intel/README.md lobster-intel/examples/thesis-profiles/regional-escalation.json docs/superpowers/plans/2026-04-20-installed-thesis-catalog.md
git commit -m "feat: add installed thesis catalog"
```
