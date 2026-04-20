# OpenClaw Installed Thesis Workflow Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose an OpenClaw-native tool that runs the installed source trackers and then the thesis runtime so `openclaw plugins install` becomes a real operator workflow surface instead of only a thin runtime wrapper.

**Architecture:** Add a small JS orchestration module beside the plugin entry. It should resolve default source-pack files from `lobster-intel/examples/source-packs`, run `official-statements-tracker`, `watchlist-tracker`, and `polymarket-tracker` through the existing Python source-runner CLI, then invoke the existing thesis runtime CLI with the refreshed artifacts. Keep the runtime spine and tracker internals unchanged; the new work stays at the OpenClaw wrapper boundary.

**Tech Stack:** Node.js ESM, `node:test`, existing `index.js` OpenClaw entry, `lobster-intel/scripts/run_source_plugin.py`, `lobster-intel/scripts/run_thesis_runtime.py`

**Status:** Implemented on 2026-04-19. This plan now serves as the execution record for the installed workflow orchestration slice.

---

## Execution Summary

This slice landed as:

- `thesis-workflow-tool.js`
- `tests/thesis-workflow-tool.test.js`
- `index.js`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`

### Task 1: Lock The Installed Workflow Contract With Tests

**Files:**
- Create: `tests/thesis-workflow-tool.test.js`
- Test: `tests/thesis-workflow-tool.test.js`

- [ ] **Step 1: Write the failing orchestrator tests**

```js
test("buildInstalledThesisWorkflow uses bundled source-pack defaults", () => {
  const workflow = buildInstalledThesisWorkflow("/repo", { thesisId: "regional-escalation" });

  assert.deepEqual(
    workflow.sourceRuns.map((run) => [run.pluginId, run.configPath]),
    [
      ["official-statements-tracker", "/repo/lobster-intel/examples/source-packs/official-statements.json"],
      ["watchlist-tracker", "/repo/lobster-intel/examples/source-packs/watchlist.json"],
      ["polymarket-tracker", "/repo/lobster-intel/examples/source-packs/polymarket.json"],
    ],
  );
});

test("runInstalledThesisWorkflow stops before execution when required files are missing", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: { thesisId: "regional-escalation" },
    existsSync: (value) => !value.endsWith("watchlist.json"),
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.kind, "missing_paths");
  assert.match(result.missingPaths[0], /watchlist\.json$/);
});

test("runInstalledThesisWorkflow runs sources before the runtime and returns a workflow summary", async () => {
  const calls = [];
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: {
      thesisId: "regional-escalation",
      semanticFrame: "military_operations_end_by_deadline",
      probabilityDirection: "yes_is_peace",
      state: "ACTIVE_TRUCE",
      nowUtc: "2026-04-19T12:30:00+00:00",
    },
    existsSync: () => true,
    runSourcePlugin: async (run) => {
      calls.push(run.pluginId);
      return { plugin: run.pluginId, new_count: 1, latest_runtime_artifact_path: `/repo/${run.pluginId}/latest.json` };
    },
    runThesisRuntime: async (runtimeRequest) => {
      calls.push("runtime");
      assert.equal(runtimeRequest.workspace, "/repo");
      assert.equal(runtimeRequest.semanticFrame, "military_operations_end_by_deadline");
      return {
        thesis_id: runtimeRequest.thesisId,
        compare_mode: "full_compare",
        artifact_paths: { delivery_receipt: "/repo/lobster-intel/data/delivery/regional-escalation/receipts/run.json" },
      };
    },
  });

  assert.deepEqual(calls, [
    "official-statements-tracker",
    "watchlist-tracker",
    "polymarket-tracker",
    "runtime",
  ]);
  assert.equal(result.kind, "ok");
  assert.match(result.summary, /full_compare/);
});
```

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

```js
export function buildInstalledThesisWorkflow(rootDir, request = {}) {
  return {
    workspace: request.workspace || rootDir,
    sourceRuns: [
      {
        pluginId: "official-statements-tracker",
        pluginDir: path.join(rootDir, "lobster-intel", "plugins", "official-statements-tracker"),
        configPath: request.officialStatementsConfigPath || path.join(rootDir, "lobster-intel", "examples", "source-packs", "official-statements.json"),
      },
      // watchlist, polymarket
    ],
    runtimeRequest: {
      thesisId: request.thesisId,
      workspace: request.workspace || rootDir,
      registryFilePath: request.registryFilePath,
      semanticFrame: request.semanticFrame,
      probabilityDirection: request.probabilityDirection,
      state: request.state,
      nowUtc: request.nowUtc,
    },
  };
}
```

- [ ] **Step 2: Wire a new OpenClaw tool in `index.js`**

```js
api.registerTool(
  {
    name: "ngi_lobster_run_installed_thesis_workflow",
    label: "NGI Lobster Run Installed Thesis Workflow",
    description:
      "Run the installed source trackers from bundled or explicit source-pack configs, then invoke the thesis runtime spine.",
    parameters: {
      type: "object",
      additionalProperties: false,
      required: ["thesisId"],
      properties: {
        thesisId: { type: "string" },
        officialStatementsConfigPath: { type: "string" },
        watchlistConfigPath: { type: "string" },
        polymarketConfigPath: { type: "string" },
        registryFilePath: { type: "string" },
        semanticFrame: { type: "string" },
        probabilityDirection: { type: "string" },
        state: { type: "string" },
        nowUtc: { type: "string" },
      },
    },
  },
  { name: "ngi_lobster_run_installed_thesis_workflow" },
);
```

- [ ] **Step 3: Document the new tool as part of the install surface**

```md
- `ngi_lobster_run_installed_thesis_workflow`
  - runs the bundled source trackers using example source-pack defaults or explicit config overrides
  - then invokes the thesis runtime spine against the freshly written source artifacts
```

- [ ] **Step 4: Run the focused JS tests and verify GREEN**

Run: `node --test tests/workflow-default-tool.test.js tests/thesis-workflow-tool.test.js`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add tests/thesis-workflow-tool.test.js thesis-workflow-tool.js index.js README.md docs/INSTALL_OPENCLAW.md docs/superpowers/plans/2026-04-19-openclaw-installed-thesis-workflow.md
git commit -m "feat: add installed thesis workflow tool"
```
