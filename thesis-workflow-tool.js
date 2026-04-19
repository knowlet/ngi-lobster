import fs from "node:fs";
import path from "node:path";

const INSTALLED_SOURCE_SPECS = [
  {
    pluginId: "official-statements-tracker",
    requestField: "officialStatementsConfigPath",
    defaultConfig: "official-statements.json",
  },
  {
    pluginId: "watchlist-tracker",
    requestField: "watchlistConfigPath",
    defaultConfig: "watchlist.json",
  },
  {
    pluginId: "polymarket-tracker",
    requestField: "polymarketConfigPath",
    defaultConfig: "polymarket.json",
  },
];

function defaultSourcePackDir(rootDir) {
  return path.join(rootDir, "lobster-intel", "examples", "source-packs");
}

function defaultThesisProfilePath(rootDir, thesisId) {
  return path.join(
    rootDir,
    "lobster-intel",
    "examples",
    "thesis-profiles",
    `${thesisId}.json`,
  );
}

function resolveRepoPath(rootDir, value) {
  if (!value) {
    return undefined;
  }
  if (path.isAbsolute(value)) {
    return value;
  }
  return path.join(rootDir, value);
}

export function loadBundledThesisProfile(rootDir, request = {}, io = {}) {
  const thesisId = request.thesisId;
  if (!thesisId) {
    return null;
  }

  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profilePath =
    resolveRepoPath(rootDir, request.thesisProfilePath) ||
    defaultThesisProfilePath(rootDir, thesisId);
    resolveRepoPath(rootDir, request.thesisProfilePath) ||
    defaultThesisProfilePath(rootDir, thesisId);

  if (!existsSync(profilePath)) {
    return null;
  }

  const profile = JSON.parse(readFileSync(profilePath, "utf8"));
  return {
    ...profile,
    profile_path: profilePath,
  };
}

export function buildInstalledThesisWorkflow(
  rootDir,
  request = {},
  thesisProfile = null,
) {
  const workspace = resolveRepoPath(rootDir, request.workspace) || rootDir;
  const sourcePackDir =
    resolveRepoPath(rootDir, request.sourcePackDir) ||
    resolveRepoPath(rootDir, thesisProfile?.source_pack_dir) ||
    defaultSourcePackDir(rootDir);

  return {
    rootDir,
    sourcePackDir,
    thesisProfile,
    sourceRuns: INSTALLED_SOURCE_SPECS.map((spec) => ({
      pluginId: spec.pluginId,
      pluginDir: path.join(rootDir, "lobster-intel", "plugins", spec.pluginId),
      configPath:
        resolveRepoPath(rootDir, request[spec.requestField]) ||
        resolveRepoPath(
          rootDir,
          thesisProfile?.source_config_paths?.[spec.pluginId],
        ) ||
        path.join(sourcePackDir, spec.defaultConfig),
      workspace,
    })),
    runtimeRequest: {
      thesisId: request.thesisId,
      workspace,
      registryFilePath:
        resolveRepoPath(rootDir, request.registryFilePath) ||
        resolveRepoPath(rootDir, thesisProfile?.registry_file_path),
      semanticFrame: request.semanticFrame || thesisProfile?.semantic_frame,
      probabilityDirection:
        request.probabilityDirection ||
        thesisProfile?.probability_direction,
      state: request.state || thesisProfile?.state,
      nowUtc: request.nowUtc,
    },
  };
}

export function collectInstalledWorkflowMissingPaths(
  workflow,
  existsSync = () => true,
) {
  const missingPaths = [];

  for (const sourceRun of workflow.sourceRuns) {
    if (!existsSync(sourceRun.pluginDir)) {
      missingPaths.push(sourceRun.pluginDir);
    }
    if (!existsSync(sourceRun.configPath)) {
      missingPaths.push(sourceRun.configPath);
    }
  }

  if (
    workflow.runtimeRequest.registryFilePath &&
    !existsSync(workflow.runtimeRequest.registryFilePath)
  ) {
    missingPaths.push(workflow.runtimeRequest.registryFilePath);
  }

  return missingPaths;
}

export function formatInstalledThesisWorkflowText({
  thesisId,
  sourceResults,
  runtimeResult,
}) {
  const sourceSummary = sourceResults
    .map((result) => `${result.plugin}: ${result.new_count ?? 0}`)
    .join(", ");
  const compareMode = runtimeResult.compare_mode || "unknown";
  const receiptPath =
    runtimeResult.artifact_paths?.delivery_receipt || "not available";

  return `Ran installed thesis workflow for ${thesisId}. Sources: ${sourceSummary}. Compare: ${compareMode}. Receipt: ${receiptPath}`;
}

export async function runInstalledThesisWorkflow({
  rootDir,
  request = {},
  existsSync = () => true,
  readFileSync = fs.readFileSync,
  runSourcePlugin,
  runThesisRuntime,
}) {
  const thesisProfile = loadBundledThesisProfile(rootDir, request, {
    existsSync,
    readFileSync,
  });
  const workflow = buildInstalledThesisWorkflow(
    rootDir,
    request,
    thesisProfile,
  );
  const missingPaths = collectInstalledWorkflowMissingPaths(workflow, existsSync);
  if (missingPaths.length > 0) {
    return {
      kind: "missing_paths",
      missingPaths,
      workflow,
    };
  }

  const sourceResults = [];
  for (const sourceRun of workflow.sourceRuns) {
    sourceResults.push(await runSourcePlugin(sourceRun));
  }

  const runtimeResult = await runThesisRuntime(workflow.runtimeRequest);
  return {
    kind: "ok",
    workflow,
    sourceResults,
    runtimeResult,
    summary: formatInstalledThesisWorkflowText({
      thesisId: workflow.runtimeRequest.thesisId,
      sourceResults,
      runtimeResult,
    }),
  };
}
