# Packaged Runtime Commands Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add package-level helper commands so the repo exposes cleaner setup and installed-workflow run commands for outside installs.

**Architecture:** Keep the existing shell and JS entrypoints, but make them discoverable through `package.json` scripts and `bin` mappings. Tighten the installed workflow CLI with a built-in `--help` path so the packaged command is self-describing instead of failing with a raw missing-argument error.

**Tech Stack:** Node.js ESM, `node:test`, `package.json`, existing `installed-workflow-cli.js`, `scripts/bootstrap_runtime.sh`, `scripts/run_installed_thesis_workflow.js`

**Status:** Implemented on 2026-04-20. This plan now serves as the execution record for packaged runtime commands.

---

## Execution Summary

This slice landed as:

- `installed-workflow-cli.js`
- `scripts/run_installed_thesis_workflow.js`
- `scripts/bootstrap_runtime.sh`
- `package.json`
- `tests/installed-workflow-cli.test.js`
- `tests/package-manifest.test.js`
- `tests/bootstrap-runtime-script.test.js`
- `README.md`
- `docs/INSTALL_OPENCLAW.md`

Verified with:

- `cd /Users/knowlet/ngi-lobster && node --test tests/*.test.js`
- `cd /Users/knowlet/ngi-lobster && .venv/bin/python -m pytest lobster-intel/tests -q`
- `cd /Users/knowlet/ngi-lobster && npm run bootstrap-runtime -- --help`
- `cd /Users/knowlet/ngi-lobster && npm run run-installed-workflow -- --help`

### Task 1: Lock Help And Manifest Contracts With Tests

**Files:**
- Modify: `tests/installed-workflow-cli.test.js`
- Create: `tests/package-manifest.test.js`
- Test: `tests/installed-workflow-cli.test.js`
- Test: `tests/package-manifest.test.js`

- [x] **Step 1: Add a failing test for CLI help output**

```js
const result = await runInstalledWorkflowCli({
  rootDir: "/repo",
  argv: ["--help"],
});

assert.equal(result.exitCode, 0);
assert.equal(result.payload, null);
assert.match(result.stdout, /Usage:/);
assert.match(result.stdout, /--thesis-id/);
```

- [x] **Step 2: Add a failing test for package helper commands**

```js
assert.equal(pkg.scripts["bootstrap-runtime"], "./scripts/bootstrap_runtime.sh");
assert.equal(pkg.scripts["run-installed-workflow"], "node ./scripts/run_installed_thesis_workflow.js");
assert.equal(pkg.bin["ngi-lobster-run-installed-workflow"], "./scripts/run_installed_thesis_workflow.js");
```

- [x] **Step 3: Run the focused JS test files and verify RED**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/installed-workflow-cli.test.js tests/package-manifest.test.js`
Expected: FAIL because the CLI has no help path and `package.json` does not expose helper commands yet

### Task 2: Implement Packaged Commands

**Files:**
- Modify: `installed-workflow-cli.js`
- Modify: `scripts/run_installed_thesis_workflow.js`
- Modify: `package.json`
- Test: `tests/installed-workflow-cli.test.js`
- Test: `tests/package-manifest.test.js`

- [x] **Step 1: Add a formatted help path to the installed workflow CLI**

```js
export function formatInstalledWorkflowCliHelp() {
  return [
    "Usage:",
    "  node scripts/run_installed_thesis_workflow.js --thesis-id <id> [options]",
  ].join("\\n");
}
```

- [x] **Step 2: Return help output before normal argument validation**

```js
if (argv.includes("--help") || argv.includes("-h")) {
  return {
    exitCode: 0,
    stdout: formatInstalledWorkflowCliHelp(),
    stderr: "",
    payload: null,
  };
}
```

- [x] **Step 3: Add package scripts and bin mappings**

```json
"bin": {
  "ngi-lobster-bootstrap-runtime": "./scripts/bootstrap_runtime.sh",
  "ngi-lobster-run-installed-workflow": "./scripts/run_installed_thesis_workflow.js"
},
"scripts": {
  "bootstrap-runtime": "./scripts/bootstrap_runtime.sh",
  "demo-gooaye": "./scripts/demo_run_gooaye.sh",
  "run-installed-workflow": "node ./scripts/run_installed_thesis_workflow.js"
}
```

- [x] **Step 4: Run the focused JS test files and syntax checks**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/installed-workflow-cli.test.js tests/package-manifest.test.js && node --check installed-workflow-cli.js && node --check scripts/run_installed_thesis_workflow.js`
Expected: PASS

### Task 3: Document The Cleaner Commands

**Files:**
- Modify: `README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] **Step 1: Document `npm run bootstrap-runtime` and `npm run run-installed-workflow -- --thesis-id <id>`**

```md
Cleaner local commands now exist:

- `npm run bootstrap-runtime`
- `npm run run-installed-workflow -- --thesis-id regional-escalation`
```

- [x] **Step 2: Run the full verification set**

Run: `cd /Users/knowlet/ngi-lobster && node --test tests/*.test.js && .venv/bin/python -m pytest lobster-intel/tests -q`
Expected: PASS

- [x] **Step 3: Commit**

```bash
git add docs/superpowers/plans/2026-04-20-packaged-runtime-commands.md tests/installed-workflow-cli.test.js tests/package-manifest.test.js installed-workflow-cli.js scripts/run_installed_thesis_workflow.js package.json README.md docs/INSTALL_OPENCLAW.md
git commit -m "feat: add packaged runtime commands"
```
