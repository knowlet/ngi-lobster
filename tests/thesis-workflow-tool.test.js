import test from "node:test";
import assert from "node:assert/strict";

import {
  buildInstalledThesisWorkflow,
  describeBundledThesisProfile,
  listBundledThesisProfiles,
  loadBundledThesisProfile,
  runInstalledThesisWorkflow,
} from "../thesis-workflow-tool.js";

test("buildInstalledThesisWorkflow uses bundled source-pack defaults", () => {
  const workflow = buildInstalledThesisWorkflow("/repo", {
    thesisId: "regional-escalation",
  });

  assert.deepEqual(
    workflow.sourceRuns.map((run) => [run.pluginId, run.configPath]),
    [
      [
        "official-statements-tracker",
        "/repo/lobster-intel/examples/source-packs/official-statements.json",
      ],
      [
        "watchlist-tracker",
        "/repo/lobster-intel/examples/source-packs/watchlist.json",
      ],
      [
        "polymarket-tracker",
        "/repo/lobster-intel/examples/source-packs/polymarket.json",
      ],
    ],
  );
  assert.equal(workflow.runtimeRequest.workspace, "/repo");
});

test("loadBundledThesisProfile resolves the thesisId profile path by default", () => {
  const profile = loadBundledThesisProfile(
    "/repo",
    { thesisId: "regional-escalation" },
    {
      existsSync: (value) => value.endsWith("regional-escalation.json"),
      readFileSync: () =>
        JSON.stringify({
          thesis_id: "regional-escalation",
          semantic_frame: "military_operations_end_by_deadline",
          probability_direction: "yes_is_peace",
          state: "ACTIVE_TRUCE",
          registry_file_path:
            "lobster-intel/examples/target-registries/regional-escalation.json",
        }),
    },
  );

  assert.equal(profile.semantic_frame, "military_operations_end_by_deadline");
  assert.equal(profile.probability_direction, "yes_is_peace");
});

test("loadBundledThesisProfile resolves a relative thesisProfilePath from the repo root", () => {
  let seenPath;
  const profile = loadBundledThesisProfile(
    "/repo",
    {
      thesisId: "regional-escalation",
      thesisProfilePath: "profiles/custom.json",
    },
    {
      existsSync: (value) => {
        seenPath = value;
        return value === "/repo/profiles/custom.json";
      },
      readFileSync: () =>
        JSON.stringify({
          thesis_id: "regional-escalation",
          semantic_frame: "military_operations_end_by_deadline",
          probability_direction: "yes_is_peace",
          state: "ACTIVE_TRUCE",
        }),
    },
  );

  assert.equal(seenPath, "/repo/profiles/custom.json");
  assert.equal(profile.profile_path, "/repo/profiles/custom.json");
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
      registry_file_path:
        "lobster-intel/examples/target-registries/regional-escalation.json",
    },
  );

  assert.equal(
    workflow.runtimeRequest.semanticFrame,
    "military_operations_end_by_deadline",
  );
  assert.equal(workflow.runtimeRequest.probabilityDirection, "yes_is_peace");
  assert.equal(workflow.runtimeRequest.state, "ESCALATING");
  assert.equal(
    workflow.runtimeRequest.registryFilePath,
    "/repo/lobster-intel/examples/target-registries/regional-escalation.json",
  );
});

test("buildInstalledThesisWorkflow resolves relative request paths from the repo root", () => {
  const workflow = buildInstalledThesisWorkflow("/repo", {
    thesisId: "regional-escalation",
    workspace: "workspaces/live",
    sourcePackDir: "custom/source-packs",
    officialStatementsConfigPath: "configs/official.json",
    watchlistConfigPath: "configs/watchlist.json",
    polymarketConfigPath: "configs/polymarket.json",
    registryFilePath: "registries/regional-escalation.json",
    thesisProfilePath: "profiles/regional-escalation.json",
  });

  assert.equal(workflow.runtimeRequest.workspace, "/repo/workspaces/live");
  assert.equal(workflow.sourcePackDir, "/repo/custom/source-packs");
  assert.equal(
    workflow.sourceRuns[0].configPath,
    "/repo/configs/official.json",
  );
  assert.equal(
    workflow.sourceRuns[1].configPath,
    "/repo/configs/watchlist.json",
  );
  assert.equal(
    workflow.sourceRuns[2].configPath,
    "/repo/configs/polymarket.json",
  );
  assert.equal(
    workflow.runtimeRequest.registryFilePath,
    "/repo/registries/regional-escalation.json",
  );
  assert.equal(
    workflow.thesisProfileRequestPath,
    "/repo/profiles/regional-escalation.json",
  );
});

test("listBundledThesisProfiles returns bundled thesis metadata sorted by thesis id", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    existsSync: () => true,
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

  assert.deepEqual(
    catalog.map((entry) => entry.thesisId),
    ["oil-shipping", "regional-escalation"],
  );
  assert.equal(catalog[1].title, "Regional escalation monitor");
  assert.equal(
    catalog[1].registryFilePath,
    "/repo/lobster-intel/examples/target-registries/regional-escalation.json",
  );
});

test("listBundledThesisProfiles returns an empty array when the profile directory is missing", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    existsSync: () => false,
  });

  assert.deepEqual(catalog, []);
});

test("listBundledThesisProfiles skips invalid JSON profile files", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    existsSync: () => true,
    readdirSync: () => [
      { name: "broken.json", isFile: () => true },
      { name: "regional-escalation.json", isFile: () => true },
    ],
    readFileSync: (value) => {
      if (value.endsWith("broken.json")) {
        return "{";
      }

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
    },
  });

  assert.deepEqual(catalog.map((entry) => entry.thesisId), [
    "regional-escalation",
  ]);
});

test("describeBundledThesisProfile summarizes registry entries for a thesis", () => {
  const description = describeBundledThesisProfile(
    "/repo",
    "regional-escalation",
    {
      existsSync: () => true,
      readFileSync: (value) => {
        if (value.includes("thesis-profiles")) {
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
    },
  );

  assert.equal(description.thesisId, "regional-escalation");
  assert.equal(description.registry.entryCount, 1);
  assert.equal(description.registry.markets[0].marketId, "1517836");
});

test("runInstalledThesisWorkflow stops before execution when required files are missing", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: { thesisId: "regional-escalation" },
    existsSync: (value) => !value.endsWith("watchlist.json"),
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        semantic_frame: "military_operations_end_by_deadline",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
        registry_file_path:
          "lobster-intel/examples/target-registries/regional-escalation.json",
      }),
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

test("runInstalledThesisWorkflow stops when the requested thesis profile is missing", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: { thesisId: "regional-escalation" },
    existsSync: (value) => !value.endsWith("regional-escalation.json"),
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.kind, "missing_paths");
  assert.deepEqual(result.missingPaths, [
    "/repo/lobster-intel/examples/thesis-profiles/regional-escalation.json",
  ]);
});

test("runInstalledThesisWorkflow stops when an explicit thesisProfilePath is missing", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: {
      thesisId: "regional-escalation",
      thesisProfilePath: "profiles/custom.json",
    },
    existsSync: (value) => value !== "/repo/profiles/custom.json",
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.kind, "missing_paths");
  assert.deepEqual(result.missingPaths, ["/repo/profiles/custom.json"]);
});

test("runInstalledThesisWorkflow runs sources before the runtime and returns a workflow summary", async () => {
  const calls = [];
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: {
      thesisId: "regional-escalation",
      nowUtc: "2026-04-19T12:30:00+00:00",
    },
    existsSync: () => true,
    readFileSync: () =>
      JSON.stringify({
        thesis_id: "regional-escalation",
        semantic_frame: "military_operations_end_by_deadline",
        probability_direction: "yes_is_peace",
        state: "ACTIVE_TRUCE",
        registry_file_path:
          "lobster-intel/examples/target-registries/regional-escalation.json",
      }),
    runSourcePlugin: async (run) => {
      calls.push(run.pluginId);
      return {
        plugin: run.pluginId,
        new_count: 1,
        latest_runtime_artifact_path: `/repo/${run.pluginId}/latest.json`,
      };
    },
    runThesisRuntime: async (runtimeRequest) => {
      calls.push("runtime");
      assert.equal(runtimeRequest.workspace, "/repo");
      assert.equal(
        runtimeRequest.semanticFrame,
        "military_operations_end_by_deadline",
      );
      assert.equal(
        runtimeRequest.registryFilePath,
        "/repo/lobster-intel/examples/target-registries/regional-escalation.json",
      );
      assert.equal(runtimeRequest.state, "ACTIVE_TRUCE");
      return {
        thesis_id: runtimeRequest.thesisId,
        compare_mode: "full_compare",
        artifact_paths: {
          delivery_receipt:
            "/repo/lobster-intel/data/delivery/regional-escalation/receipts/run.json",
        },
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
  assert.equal(result.sourceResults.length, 3);
  assert.equal(result.runtimeResult.compare_mode, "full_compare");
  assert.match(result.summary, /full_compare/);
  assert.match(result.summary, /official-statements-tracker: 1/);
});
