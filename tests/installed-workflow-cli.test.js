import test from "node:test";
import assert from "node:assert/strict";

import {
  formatInstalledWorkflowCliHelp,
  parseInstalledWorkflowCliArgs,
  runInstalledWorkflowCli,
} from "../installed-workflow-cli.js";

test("formatInstalledWorkflowCliHelp describes the packaged command", () => {
  const help = formatInstalledWorkflowCliHelp();

  assert.match(help, /Usage:/);
  assert.match(help, /run_installed_thesis_workflow\.js/);
  assert.match(help, /--thesis-id/);
});

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
    "--watchlist-config",
    "packs/watchlist.json",
    "--watchlist-state",
    "state/watchlist.json",
    "--polymarket-config",
    "packs/polymarket.json",
    "--polymarket-state",
    "state/polymarket.json",
    "--registry-file",
    "registries/targets.json",
    "--semantic-frame",
    "military_operations_end_by_deadline",
    "--probability-direction",
    "yes_is_peace",
    "--state",
    "ACTIVE_TRUCE",
    "--now-utc",
    "2026-04-20T04:00:00Z",
  ]);

  assert.deepEqual(request, {
    thesisId: "regional-escalation",
    workspace: "/tmp/workspace",
    officialStatementsConfigPath: "packs/official.json",
    officialStatementsStatePath: "state/official.json",
    watchlistConfigPath: "packs/watchlist.json",
    watchlistStatePath: "state/watchlist.json",
    polymarketConfigPath: "packs/polymarket.json",
    polymarketStatePath: "state/polymarket.json",
    registryFilePath: "registries/targets.json",
    semanticFrame: "military_operations_end_by_deadline",
    probabilityDirection: "yes_is_peace",
    state: "ACTIVE_TRUCE",
    nowUtc: "2026-04-20T04:00:00Z",
  });
});

test("runInstalledWorkflowCli returns a structured success payload", async () => {
  const sourceRuns = [];
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--thesis-id", "regional-escalation", "--workspace", "/tmp/workspace"],
    existsSync: () => true,
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        semantic_frame: "military_operations_end_by_deadline",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
        registry_file_path:
          "lobster-intel/examples/target-registries/regional-escalation.json",
        source_config_paths: {
          "official-statements-tracker":
            "lobster-intel/examples/source-packs/official-statements.json",
          "watchlist-tracker":
            "lobster-intel/examples/source-packs/watchlist.json",
          "polymarket-tracker":
            "lobster-intel/examples/source-packs/polymarket.json",
        },
      }),
    runSourcePlugin: async (run) => {
      sourceRuns.push(run);
      return {
        plugin: run.pluginId,
        new_count: 0,
        state_path: run.statePath,
      };
    },
    runThesisRuntime: async (runtimeRequest) => ({
      thesis_id: runtimeRequest.thesisId,
      compare_mode: "full_compare",
      artifact_paths: {
        delivery_receipt: "/repo/out/receipt.json",
      },
    }),
  });

  assert.equal(result.exitCode, 0);
  assert.equal(result.stderr, "");
  assert.equal(result.payload.thesis_id, "regional-escalation");
  assert.equal(result.payload.workspace, "/tmp/workspace");
  assert.equal(result.payload.source_results.length, 3);
  assert.equal(result.payload.runtime_result.compare_mode, "full_compare");
  assert.match(result.payload.summary, /regional-escalation/);
  assert.deepEqual(
    sourceRuns.map((run) => run.statePath),
    [
      "/tmp/workspace/lobster-intel/data/runtime/sources/official-statements.json",
      "/tmp/workspace/lobster-intel/data/runtime/sources/watchlist.json",
      "/tmp/workspace/lobster-intel/data/runtime/sources/polymarket.json",
    ],
  );
});

test("runInstalledWorkflowCli returns help output for --help", async () => {
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--help"],
  });

  assert.equal(result.exitCode, 0);
  assert.equal(result.payload, null);
  assert.equal(result.stderr, "");
  assert.match(result.stdout, /Usage:/);
  assert.match(result.stdout, /--thesis-id/);
});

test("runInstalledWorkflowCli returns exit code 2 when required files are missing", async () => {
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--thesis-id", "regional-escalation"],
    existsSync: (value) => !value.endsWith("watchlist.json"),
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        semantic_frame: "military_operations_end_by_deadline",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
        registry_file_path:
          "lobster-intel/examples/target-registries/regional-escalation.json",
        source_config_paths: {
          "official-statements-tracker":
            "lobster-intel/examples/source-packs/official-statements.json",
          "watchlist-tracker":
            "lobster-intel/examples/source-packs/watchlist.json",
          "polymarket-tracker":
            "lobster-intel/examples/source-packs/polymarket.json",
        },
      }),
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.exitCode, 2);
  assert.equal(result.payload, null);
  assert.match(result.stderr, /missing workflow input files/i);
  assert.match(result.stderr, /watchlist\.json/);
});

test("runInstalledWorkflowCli fails closed when the thesis profile contract is incomplete", async () => {
  const result = await runInstalledWorkflowCli({
    rootDir: "/repo",
    argv: ["--thesis-id", "regional-escalation"],
    existsSync: () => true,
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
      }),
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.exitCode, 1);
  assert.equal(result.payload, null);
  assert.match(result.stderr, /invalid thesis profile/i);
  assert.match(result.stderr, /semanticFrame/);
});
