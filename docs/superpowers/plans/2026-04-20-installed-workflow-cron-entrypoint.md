# Installed Workflow Cron Entrypoint Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a stable installed-workflow CLI entrypoint that outside installs and cron jobs can run directly without going through the OpenClaw tool surface.

**Architecture:** Keep installed workflow orchestration in the existing JS wrapper layer by adding a dedicated CLI module plus a small `scripts/` entrypoint. The CLI should reuse `runInstalledThesisWorkflow`, invoke the same Python source/runtime scripts as the plugin wrapper, print structured JSON on success, and fail with a concrete missing-path error on invalid input. Document the script as the reusable cron recipe for outside installs.

**Tech Stack:** Node.js ESM, `node:test`, existing `thesis-workflow-tool.js`, `child_process.execFile`, Python helper CLIs under `lobster-intel/scripts/`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for the installed workflow cron entrypoint.

---

## Execution Summary

This slice landed as:

- `installed-workflow-cli.js`
- `scripts/run_installed_thesis_workflow.js`
- `tests/installed-workflow-cli.test.js`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `lobster-intel/docs/operations/cron.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/*.test.js`
- `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`
- `cd /Users/knowlet/ngi-lobster && node --check installed-workflow-cli.js && node --check scripts/run_installed_thesis_workflow.js`
- `cd /Users/knowlet/ngi-lobster && node scripts/run_installed_thesis_workflow.js` (expected exit `2` with `ERROR: --thesis-id is required`)

Re-verified in the active workspace on 2026-04-22 with:

- `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && node --test tests/*.test.js`
- `cd /Users/knowlet/.openclaw/workspace/projects/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_runtime_contract_bundle.py -q`

### Task 1: Lock The CLI Contract With Tests

**Files:**
- Create: `tests/installed-workflow-cli.test.js`
- Test: `tests/installed-workflow-cli.test.js`

- [x] **Step 1: Write a failing test for CLI argument parsing**

```js
test("parseInstalledWorkflowCliArgs maps CLI flags into workflow request fields", () => {
  const request = parseInstalledWorkflowCliArgs([
    "--thesis-id",
    "regional-escalation",
    "--workspace",
    "/tmp/workspace",
    "--official-statements-config",
    "packs/official.json",
    "--official-statements-state",
    "state/official.json",
    "--now-utc",
    "2026-04-20T04:00:00Z",
  ]);

  assert.deepEqual(request, {
    thesisId: "regional-escalation",
    workspace: "/tmp/workspace",
    officialStatementsConfigPath: "packs/official.json",
    officialStatementsStatePath: "state/official.json",
    nowUtc: "2026-04-20T04:00:00Z",
  });
});
```

- [x] **Step 2: Write a failing test for structured success payload**

```js
test("runInstalledWorkflowCli returns a structured success payload", async () => {
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--thesis-id", "regional-escalation"],
    existsSync: () => true,
    readFileSync: () => JSON.stringify({ thesis_id: "regional-escalation" }),
    runSourcePlugin: async (run) => ({ plugin: run.pluginId, new_count: 0 }),
    runThesisRuntime: async () => ({
      thesis_id: "regional-escalation",
      compare_mode: "full_compare",
      artifact_paths: { delivery_receipt: "/repo/out/receipt.json" },
    }),
  });

  assert.equal(result.exitCode, 0);
  assert.equal(result.payload.thesis_id, "regional-escalation");
  assert.equal(result.payload.source_results.length, 3);
});
```

- [x] **Step 3: Write a failing test for missing-path failures**

```js
test("runInstalledWorkflowCli returns exit code 2 when required files are missing", async () => {
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--thesis-id", "regional-escalation"],
    existsSync: (value) => !value.endsWith("watchlist.json"),
    readFileSync: () => JSON.stringify({ thesis_id: "regional-escalation" }),
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.exitCode, 2);
  assert.match(result.stderr, /watchlist\.json/);
});
```

- [x] **Step 4: Run the new JS test file and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/installed-workflow-cli.test.js`
Expected: FAIL because the CLI module does not exist yet

### Task 2: Implement The Installed Workflow CLI

**Files:**
- Create: `installed-workflow-cli.js`
- Create: `scripts/run_installed_thesis_workflow.js`
- Test: `tests/installed-workflow-cli.test.js`

- [x] **Step 1: Add CLI parsing for thesis, source-pack, state, and runtime override flags**

```js
export function parseInstalledWorkflowCliArgs(argv = []) {
  const request = {};
  for (let index = 0; index < argv.length; index += 2) {
    const flag = argv[index];
    const value = argv[index + 1];
    if (flag === "--thesis-id") request.thesisId = value;
    if (flag === "--workspace") request.workspace = value;
    if (flag === "--official-statements-config") request.officialStatementsConfigPath = value;
    if (flag === "--official-statements-state") request.officialStatementsStatePath = value;
  }
  return request;
}
```

- [x] **Step 2: Wrap `runInstalledThesisWorkflow` into a CLI-friendly result**

```js
export async function runInstalledWorkflowCli(deps) {
  const request = parseInstalledWorkflowCliArgs(deps.argv);
  const workflowResult = await runInstalledThesisWorkflow({
    rootDir: deps.rootDir,
    request,
    existsSync: deps.existsSync,
    readFileSync: deps.readFileSync,
    runSourcePlugin: deps.runSourcePlugin,
    runThesisRuntime: deps.runThesisRuntime,
  });
  if (workflowResult.kind === "missing_paths") {
    return {
      exitCode: 2,
      stderr: `ERROR: missing workflow input files:\n${workflowResult.missingPaths.join("\n")}`,
    };
  }
  return {
    exitCode: 0,
    payload: {
      thesis_id: workflowResult.workflow.runtimeRequest.thesisId,
      summary: workflowResult.summary,
      source_results: workflowResult.sourceResults,
      runtime_result: workflowResult.runtimeResult,
    },
  };
}
```

- [x] **Step 3: Add the executable script entrypoint**

```js
const result = await runInstalledWorkflowCli({
  rootDir,
  argv: process.argv.slice(2),
  existsSync: fs.existsSync,
  readFileSync: fs.readFileSync,
  runSourcePlugin: runSourcePluginScript,
  runThesisRuntime: runThesisRuntimeScript,
});
```

- [x] **Step 4: Run the focused JS test file and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/installed-workflow-cli.test.js && node --check installed-workflow-cli.js && node --check scripts/run_installed_thesis_workflow.js`
Expected: PASS

### Task 3: Document The Reusable Cron Recipe

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `lobster-intel/docs/operations/cron.md`

- [x] **Step 1: Document the stable installed-workflow cron entrypoint**

```md
For outside installs and cron jobs, use:

```bash
node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation
```
```

- [x] **Step 2: Add a concrete cron example using the new CLI**

```md
*/15 * * * * cd /path/to/ngi-lobster && /usr/bin/env node scripts/run_installed_thesis_workflow.js --thesis-id regional-escalation >> lobster-intel/data/runtime/cron/regional-escalation.log 2>&1
```

- [x] **Step 3: Run the full verification set**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/*.test.js && .venv/bin/python -m pytest lobster-intel/tests -q`
Expected: PASS

- [x] **Step 4: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-installed-workflow-cron-entrypoint.md installed-workflow-cli.js scripts/run_installed_thesis_workflow.js tests/installed-workflow-cli.test.js README.md docs/INSTALL_OPENCLAW.md lobster-intel/docs/operations/cron.md
git commit -m "feat: add installed workflow cron entrypoint"
```
