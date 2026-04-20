import fs from "node:fs";
import path from "node:path";

const INSTALLED_SOURCE_SPECS = [
  {
    pluginId: "official-statements-tracker",
    requestField: "officialStatementsConfigPath",
    stateRequestField: "officialStatementsStatePath",
    defaultConfig: "official-statements.json",
    defaultState: "official-statements.json",
  },
  {
    pluginId: "watchlist-tracker",
    requestField: "watchlistConfigPath",
    stateRequestField: "watchlistStatePath",
    defaultConfig: "watchlist.json",
    defaultState: "watchlist.json",
  },
  {
    pluginId: "polymarket-tracker",
    requestField: "polymarketConfigPath",
    stateRequestField: "polymarketStatePath",
    defaultConfig: "polymarket.json",
    defaultState: "polymarket.json",
  },
];

function defaultSourcePackDir(rootDir) {
  return path.join(rootDir, "lobster-intel", "examples", "source-packs");
}

function defaultThesisProfileDir(rootDir) {
  return path.join(rootDir, "lobster-intel", "examples", "thesis-profiles");
}

function defaultThesisProfilePath(rootDir, thesisId) {
  return path.join(defaultThesisProfileDir(rootDir), `${thesisId}.json`);
}

function resolveThesisProfilePath(rootDir, request = {}) {
  if (!request.thesisId) {
    return null;
  }
  return (
    resolveRepoPath(rootDir, request.thesisProfilePath) ||
    defaultThesisProfilePath(rootDir, request.thesisId)
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

function resolveWorkspacePath(workspace, value) {
  if (!value) {
    return undefined;
  }
  if (path.isAbsolute(value)) {
    return value;
  }
  return path.join(workspace, value);
}

function parseJsonFile(readFileSync, filePath, label) {
  try {
    return JSON.parse(readFileSync(filePath, "utf8"));
  } catch (err) {
    throw new Error(
      `Failed to parse ${label} at ${filePath}: ${err?.message || "invalid JSON"}`,
    );
  }
}

export function loadBundledThesisProfile(rootDir, request = {}, io = {}) {
  const thesisId = request.thesisId;
  if (!thesisId) {
    return null;
  }

  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profilePath = resolveThesisProfilePath(rootDir, request);

  if (!existsSync(profilePath)) {
    return null;
  }

  const profile = parseJsonFile(readFileSync, profilePath, "thesis profile");
  return {
    ...profile,
    profile_path: profilePath,
  };
}

function profileSummary(rootDir, profile, extra = {}) {
  return {
    thesisId: profile.thesis_id,
    title: profile.title || profile.thesis_id,
    summary: profile.summary || "",
    semanticFrame: profile.semantic_frame,
    probabilityDirection: profile.probability_direction,
    state: profile.state,
    profilePath: profile.profile_path,
    registryFilePath: resolveRepoPath(rootDir, profile.registry_file_path),
    ...extra,
  };
}

function inspectInstalledWorkflowContract({
  rootDir,
  request = {},
  thesisProfile = null,
  workflow = null,
  existsSync = fs.existsSync,
}) {
  const thesisId = request.thesisId || thesisProfile?.thesis_id || "unknown-thesis";
  const profileErrors = [];

  if (!thesisProfile) {
    const profilePath = resolveThesisProfilePath(rootDir, request);
    profileErrors.push(
      `No bundled thesis profile found for "${thesisId}" at ${profilePath}.`,
    );
  } else {
    if (request.thesisId && thesisProfile.thesis_id !== request.thesisId) {
      profileErrors.push(
        `Thesis profile "${thesisProfile.profile_path}" declares thesis_id "${thesisProfile.thesis_id}" but the request asked for "${request.thesisId}".`,
      );
    }

    if (!workflow?.runtimeRequest.semanticFrame) {
      profileErrors.push(
        `Thesis profile "${thesisId}" does not resolve semanticFrame.`,
      );
    }
    if (!workflow?.runtimeRequest.probabilityDirection) {
      profileErrors.push(
        `Thesis profile "${thesisId}" does not resolve probabilityDirection.`,
      );
    }
    if (!workflow?.runtimeRequest.state) {
      profileErrors.push(`Thesis profile "${thesisId}" does not resolve state.`);
    }
    if (!workflow?.runtimeRequest.registryFilePath) {
      profileErrors.push(
        `Thesis profile "${thesisId}" does not resolve registryFilePath.`,
      );
    }

    for (const spec of INSTALLED_SOURCE_SPECS) {
      const hasExplicitOverride = Boolean(request[spec.requestField]);
      const declaredSourcePath =
        thesisProfile.source_config_paths?.[spec.pluginId] || null;
      if (!hasExplicitOverride && !declaredSourcePath) {
        profileErrors.push(
          `Thesis profile "${thesisId}" does not declare source_config_paths.${spec.pluginId}.`,
        );
      }
    }
  }

  const missingPaths =
    profileErrors.length > 0 || !workflow
      ? []
      : collectInstalledWorkflowMissingPaths(workflow, existsSync);
  const validationErrors = [
    ...profileErrors,
    ...missingPaths.map((item) => `Workflow input file not found: ${item}`),
  ];

  return {
    contractStatus: validationErrors.length === 0 ? "ready" : "incomplete",
    profileErrors,
    missingPaths,
    validationErrors,
  };
}

export function listBundledThesisProfiles(rootDir, io = {}) {
  const existsSync = io.existsSync || fs.existsSync;
  const readdirSync = io.readdirSync || fs.readdirSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profileDir = defaultThesisProfileDir(rootDir);

  return readdirSync(profileDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => {
      const profilePath = path.join(profileDir, entry.name);
      const profile = parseJsonFile(readFileSync, profilePath, "thesis profile");
      const thesisProfile = {
        ...profile,
        profile_path: profilePath,
      };
      const contract = inspectInstalledWorkflowContract({
        rootDir,
        request: { thesisId: thesisProfile.thesis_id },
        thesisProfile,
        workflow: buildInstalledThesisWorkflow(
          rootDir,
          { thesisId: thesisProfile.thesis_id },
          thesisProfile,
        ),
        existsSync,
      });
      return profileSummary(rootDir, thesisProfile, {
        contractStatus: contract.contractStatus,
        validationErrors: contract.validationErrors,
      });
    })
    .sort((left, right) => left.thesisId.localeCompare(right.thesisId));
}

export function describeBundledThesisProfile(rootDir, thesisId, io = {}) {
  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profile = loadBundledThesisProfile(rootDir, { thesisId }, {
    existsSync,
    readFileSync,
  });
  if (!profile) {
    return null;
  }

  const workflow = buildInstalledThesisWorkflow(rootDir, { thesisId }, profile);
  const contract = inspectInstalledWorkflowContract({
    rootDir,
    request: { thesisId },
    thesisProfile: profile,
    workflow,
    existsSync,
  });
  const registryPath = resolveRepoPath(rootDir, profile.registry_file_path);
  const registryEntries =
    registryPath && existsSync(registryPath)
      ? parseJsonFile(readFileSync, registryPath, "thesis registry")
      : [];

  return {
    ...profileSummary(rootDir, profile, {
      contractStatus: contract.contractStatus,
      validationErrors: contract.validationErrors,
    }),
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
      statePath:
        resolveWorkspacePath(workspace, request[spec.stateRequestField]) ||
        resolveWorkspacePath(
          workspace,
          thesisProfile?.source_state_paths?.[spec.pluginId],
        ) ||
        path.join(
          workspace,
          "lobster-intel",
          "data",
          "runtime",
          "sources",
          spec.defaultState,
        ),
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
  const contract = inspectInstalledWorkflowContract({
    rootDir,
    request,
    thesisProfile,
    workflow,
    existsSync,
  });
  if (contract.profileErrors.length > 0) {
    return {
      kind: "invalid_profile",
      thesisProfile,
      validationErrors: contract.validationErrors,
      workflow,
    };
  }
  if (contract.missingPaths.length > 0) {
    return {
      kind: "missing_paths",
      missingPaths: contract.missingPaths,
      workflow,
      validationErrors: contract.validationErrors,
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
