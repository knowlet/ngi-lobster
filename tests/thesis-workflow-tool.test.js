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
        }),
    },
  );

  assert.equal(seenPath, "/repo/profiles/custom.json");
  assert.equal(profile.profile_path, "/repo/profiles/custom.json");
});

test("loadBundledThesisProfile returns null when profile JSON is malformed", () => {
  const profile = loadBundledThesisProfile(
    "/repo",
    { thesisId: "regional-escalation" },
    {
      existsSync: () => true,
      readFileSync: () => "{",
    },
  );

  assert.equal(profile, null);
});

test("buildInstalledThesisWorkflow resolves relative override paths from the repo root", () => {
  const workflow = buildInstalledThesisWorkflow(
    "/repo",
    {
      thesisId: "regional-escalation",
      workspace: "workspace/custom",
      sourcePackDir: "packs",
      officialStatementsConfigPath: "configs/official.json",
      registryFilePath: "registries/custom.json",
    },
  );

  assert.equal(workflow.runtimeRequest.workspace, "/repo/workspace/custom");
  assert.equal(workflow.sourcePackDir, "/repo/packs");
  assert.equal(workflow.sourceRuns[0].configPath, "/repo/configs/official.json");
  assert.equal(workflow.runtimeRequest.registryFilePath, "/repo/registries/custom.json");
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
      source_config_paths: {
        "official-statements-tracker":
          "lobster-intel/examples/source-packs/official-statements.json",
      },
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
  assert.equal(
    workflow.sourceRuns[0].configPath,
    "/repo/lobster-intel/examples/source-packs/official-statements.json",
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
        registry_file_path: "lobster-intel/examples/target-registries/oil-shipping.json",
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
  assert.equal(catalog[1].contractStatus, "ready");
});

test("listBundledThesisProfiles returns an empty list when the profile directory is missing", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    existsSync: () => false,
    readdirSync: () => {
      throw new Error("should not read missing directory");
    },
  });

  assert.deepEqual(catalog, []);
});

test("listBundledThesisProfiles reports malformed profile JSON as incomplete", () => {
  const catalog = listBundledThesisProfiles("/repo", {
    existsSync: () => true,
    readdirSync: () => [
      { name: "regional-escalation.json", isFile: () => true },
    ],
    readFileSync: () => "{",
  });

  assert.equal(catalog[0].thesisId, "regional-escalation");
  assert.equal(catalog[0].contractStatus, "incomplete");
  assert.match(catalog[0].validationErrors[0], /Failed to parse profile JSON/);
});

test("describeBundledThesisProfile summarizes registry entries and contract status", () => {
  const description = describeBundledThesisProfile("/repo", "regional-escalation", {
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
          source_config_paths: {
            "official-statements-tracker":
              "lobster-intel/examples/source-packs/official-statements.json",
            "watchlist-tracker":
              "lobster-intel/examples/source-packs/watchlist.json",
            "polymarket-tracker":
              "lobster-intel/examples/source-packs/polymarket.json",
          },
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
  assert.equal(description.contractStatus, "ready");
  assert.equal(description.sourceConfigs.length, 3);
});

test("describeBundledThesisProfile flags incomplete runtime contracts", () => {
  const description = describeBundledThesisProfile("/repo", "regional-escalation", {
    existsSync: () => true,
    readFileSync: (value) => {
      if (value.includes("thesis-profiles")) {
        return JSON.stringify({
          thesis_id: "regional-escalation",
          title: "Regional escalation monitor",
          summary: "Tracks military operations end-state risk.",
          probability_direction: "yes_is_peace",
          state: "ACTIVE_TRUCE",
        });
      }
      return JSON.stringify([]);
    },
  });

  assert.equal(description.contractStatus, "incomplete");
  assert.match(
    description.validationErrors[0],
    /does not resolve semanticFrame/,
  );
});

test("describeBundledThesisProfile reports malformed registry JSON as incomplete", () => {
  const description = describeBundledThesisProfile("/repo", "regional-escalation", {
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

      return "{";
    },
  });

  assert.equal(description.contractStatus, "incomplete");
  assert.match(description.validationErrors[0], /Failed to parse registry JSON/);
  assert.equal(description.registry.entryCount, 0);
});

test("runInstalledThesisWorkflow reports malformed bundled profile JSON as invalid_profile", async () => {
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: { thesisId: "regional-escalation" },
    existsSync: () => true,
    readFileSync: () => "{",
    runSourcePlugin: async () => {
      throw new Error("should not run");
    },
    runThesisRuntime: async () => {
      throw new Error("should not run");
    },
  });

  assert.equal(result.kind, "invalid_profile");
  assert.match(result.validationErrors[0], /Failed to parse profile JSON/);
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
  assert.match(result.validationErrors[0], /No bundled thesis profile found/);
});

test("runInstalledThesisWorkflow runs with explicit overrides when no bundled profile exists", async () => {
  const calls = [];
  const result = await runInstalledThesisWorkflow({
    rootDir: "/repo",
    request: {
      thesisId: "custom-thesis",
      semanticFrame: "military_operations_end_by_deadline",
      probabilityDirection: "yes_is_peace",
      state: "ACTIVE_TRUCE",
      registryFilePath: "/repo/custom-registry.json",
      officialStatementsConfigPath: "/repo/official.json",
      watchlistConfigPath: "/repo/watchlist.json",
      polymarketConfigPath: "/repo/polymarket.json",
    },
    existsSync: (value) => !value.includes("thesis-profiles/custom-thesis.json"),
    runSourcePlugin: async (run) => {
      calls.push(run.pluginId);
      return { plugin: run.pluginId, new_count: 0 };
    },
    runThesisRuntime: async (runtimeRequest) => {
      calls.push("runtime");
      return {
        thesis_id: runtimeRequest.thesisId,
        compare_mode: "degraded_compare",
        artifact_paths: {
          delivery_receipt: "/repo/lobster-intel/data/delivery/custom-thesis/receipts/run.json",
        },
      };
    },
  });

  assert.equal(result.kind, "ok");
  assert.deepEqual(calls, [
    "official-statements-tracker",
    "watchlist-tracker",
    "polymarket-tracker",
    "runtime",
  ]);
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
