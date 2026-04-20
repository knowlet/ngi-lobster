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

function hasValue(value) {
  return value !== undefined && value !== null && value !== "";
}

function defaultSourcePackDir(rootDir) {
  return path.join(rootDir, "lobster-intel", "examples", "source-packs");
}

function defaultThesisProfileDir(rootDir) {
  return path.join(rootDir, "lobster-intel", "examples", "thesis-profiles");
}

function defaultThesisProfilePath(rootDir, thesisId) {
  return path.join(defaultThesisProfileDir(rootDir), `${thesisId}.json`);
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
    return {
      value: JSON.parse(readFileSync(filePath, "utf8")),
      error: null,
    };
  } catch (err) {
    return {
      value: null,
      error: `Failed to parse ${label} JSON: ${err.message}`,
    };
  }
}

function readBundledThesisProfile(rootDir, request = {}, io = {}) {
  const thesisId = request.thesisId;
  if (!thesisId) {
    return { profile: null, error: null, profilePath: null };
  }

  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profilePath =
    resolveRepoPath(rootDir, request.thesisProfilePath) ||
    defaultThesisProfilePath(rootDir, thesisId);

  if (!existsSync(profilePath)) {
    return { profile: null, error: null, profilePath };
  }

  const { value, error } = parseJsonFile(readFileSync, profilePath, "profile");
  if (!value || typeof value !== "object" || Array.isArray(value)) {
    return {
      profile: null,
      error: error || `Failed to parse profile JSON: expected object at ${profilePath}`,
      profilePath,
    };
  }

  return {
    profile: {
      ...value,
      profile_path: profilePath,
    },
    error: null,
    profilePath,
  };
}

function sourceConfigSummaries(workflow, existsSync) {
  return workflow.sourceRuns.map((sourceRun) => ({
    pluginId: sourceRun.pluginId,
    configPath: sourceRun.configPath,
    exists: existsSync(sourceRun.configPath),
  }));
}

function profileSummary(rootDir, profile, extras = {}) {
  return {
    thesisId: profile.thesis_id,
    title: profile.title || profile.thesis_id,
    summary: profile.summary || "",
    semanticFrame: profile.semantic_frame,
    probabilityDirection: profile.probability_direction,
    state: profile.state,
    profilePath: profile.profile_path,
    registryFilePath: resolveRepoPath(rootDir, profile.registry_file_path),
    ...extras,
  };
}

function validateInstalledWorkflowContract(request, thesisProfile, workflow) {
  const thesisId = request.thesisId || thesisProfile?.thesis_id || "unknown-thesis";
  const errors = [];

  if (!thesisProfile) {
    if (request.thesisProfilePath) {
      errors.push(`Provided thesis profile path does not exist: ${request.thesisProfilePath}`);
      return errors;
    }

    const missingRuntimeFields = [];
    if (!hasValue(workflow.runtimeRequest.semanticFrame)) {
      missingRuntimeFields.push("semanticFrame");
    }
    if (!hasValue(workflow.runtimeRequest.probabilityDirection)) {
      missingRuntimeFields.push("probabilityDirection");
    }
    if (!hasValue(workflow.runtimeRequest.state)) {
      missingRuntimeFields.push("state");
    }
    if (!hasValue(workflow.runtimeRequest.registryFilePath)) {
      missingRuntimeFields.push("registryFilePath");
    }

    if (missingRuntimeFields.length > 0) {
      errors.push(
        `No bundled thesis profile found for "${thesisId}". Provide thesisProfilePath or explicit ${missingRuntimeFields.join(", ")}.`,
      );
    }
    return errors;
  }

  if (!hasValue(workflow.runtimeRequest.semanticFrame)) {
    errors.push(`Thesis profile "${thesisId}" does not resolve semanticFrame.`);
  }
  if (!hasValue(workflow.runtimeRequest.probabilityDirection)) {
    errors.push(`Thesis profile "${thesisId}" does not resolve probabilityDirection.`);
  }
  if (!hasValue(workflow.runtimeRequest.state)) {
    errors.push(`Thesis profile "${thesisId}" does not resolve state.`);
  }
  if (!hasValue(workflow.runtimeRequest.registryFilePath)) {
    errors.push(`Thesis profile "${thesisId}" does not resolve registryFilePath.`);
  }

  return errors;
}

export function loadBundledThesisProfile(rootDir, request = {}, io = {}) {
  return readBundledThesisProfile(rootDir, request, io).profile;
}

export function listBundledThesisProfiles(rootDir, io = {}) {
  const existsSync = io.existsSync || fs.existsSync;
  const readdirSync = io.readdirSync || fs.readdirSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profileDir = defaultThesisProfileDir(rootDir);

  if (!existsSync(profileDir)) {
    return [];
  }

  return readdirSync(profileDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => {
      const thesisId = entry.name.replace(/\.json$/, "");
      const { profile, error, profilePath } = readBundledThesisProfile(
        rootDir,
        {
          thesisId,
          thesisProfilePath: path.join(profileDir, entry.name),
        },
        { existsSync, readFileSync },
      );
      if (!profile) {
        return profileSummary(
          rootDir,
          { thesis_id: thesisId, profile_path: profilePath },
          {
            contractStatus: "incomplete",
            validationErrors: [
              error || `Failed to load profile metadata: ${profilePath}`,
            ],
          },
        );
      }

      const workflow = buildInstalledThesisWorkflow(
        rootDir,
        { thesisId: profile.thesis_id },
        profile,
      );
      const validationErrors = [
        ...validateInstalledWorkflowContract(
          { thesisId: profile.thesis_id },
          profile,
          workflow,
        ),
        ...collectInstalledWorkflowMissingPaths(workflow, existsSync).map(
          (missingPath) => `Missing file: ${missingPath}`,
        ),
      ];

      return profileSummary(rootDir, profile, {
        contractStatus: validationErrors.length === 0 ? "ready" : "incomplete",
        validationErrors,
      });
    })
    .sort((left, right) => left.thesisId.localeCompare(right.thesisId));
}

export function describeBundledThesisProfile(rootDir, thesisId, io = {}) {
  const existsSync = io.existsSync || fs.existsSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const request = { thesisId };
  const { profile, error, profilePath } = readBundledThesisProfile(rootDir, request, {
    existsSync,
    readFileSync,
  });
  if (!profile) {
    if (!error) {
      return null;
    }

    return {
      ...profileSummary(
        rootDir,
        { thesis_id: thesisId, profile_path: profilePath },
        {
          contractStatus: "incomplete",
          validationErrors: [error],
        },
      ),
      sourceConfigs: [],
      registry: {
        path: null,
        exists: false,
        entryCount: 0,
        markets: [],
      },
    };
  }

  const workflow = buildInstalledThesisWorkflow(rootDir, request, profile);
  const registryPath = workflow.runtimeRequest.registryFilePath;
  const validationErrors = [
    ...validateInstalledWorkflowContract(request, profile, workflow),
    ...collectInstalledWorkflowMissingPaths(workflow, existsSync).map(
      (missingPath) => `Missing file: ${missingPath}`,
    ),
  ];
  let registryEntries = [];
  if (registryPath && existsSync(registryPath)) {
    const { value, error: registryError } = parseJsonFile(
      readFileSync,
      registryPath,
      "registry",
    );
    if (registryError) {
      validationErrors.push(registryError);
    } else if (Array.isArray(value)) {
      registryEntries = value;
    } else {
      validationErrors.push(
        `Failed to parse registry JSON: expected array at ${registryPath}`,
      );
    }
  }

  return {
    ...profileSummary(rootDir, profile, {
      contractStatus: validationErrors.length === 0 ? "ready" : "incomplete",
      validationErrors,
    }),
    sourceConfigs: sourceConfigSummaries(workflow, existsSync),
    registry: {
      path: registryPath || null,
      exists: Boolean(registryPath && existsSync(registryPath)),
      entryCount: registryEntries.length,
      markets: registryEntries.map((entry) => ({
        marketId: entry.market_id || null,
        marketQuestion: entry.market_question || null,
      })),
    },
  };
}

function profileSummary(rootDir, profile) {
  return {
    thesisId: profile.thesis_id,
    title: profile.title || profile.thesis_id,
    summary: profile.summary || "",
    semanticFrame: profile.semantic_frame,
    probabilityDirection: profile.probability_direction,
    state: profile.state,
    profilePath: profile.profile_path,
    registryFilePath: resolveRepoPath(rootDir, profile.registry_file_path),
  };
}

export function listBundledThesisProfiles(rootDir, io = {}) {
  const readdirSync = io.readdirSync || fs.readdirSync;
  const readFileSync = io.readFileSync || fs.readFileSync;
  const profileDir = defaultThesisProfileDir(rootDir);

  return readdirSync(profileDir, { withFileTypes: true })
    .filter((entry) => entry.isFile() && entry.name.endsWith(".json"))
    .map((entry) => {
      const profilePath = path.join(profileDir, entry.name);
      const profile = JSON.parse(readFileSync(profilePath, "utf8"));
      return profileSummary(rootDir, {
        ...profile,
        profile_path: profilePath,
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

  const registryPath = resolveRepoPath(rootDir, profile.registry_file_path);
  const registryEntries =
    registryPath && existsSync(registryPath)
      ? JSON.parse(readFileSync(registryPath, "utf8"))
      : [];

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
  const { profile: thesisProfile, error: profileError } = readBundledThesisProfile(rootDir, request, {
    existsSync,
    readFileSync,
  });
  const workflow = buildInstalledThesisWorkflow(
    rootDir,
    request,
    thesisProfile,
  );
  const validationErrors = validateInstalledWorkflowContract(
    request,
    thesisProfile,
    workflow,
  );
  if (profileError && validationErrors.length > 0) {
    validationErrors.unshift(profileError);
  }
  if (validationErrors.length > 0) {
    return {
      kind: "invalid_profile",
      validationErrors,
      workflow,
      thesisProfile,
    };
  }

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
