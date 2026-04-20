import { execFile } from "node:child_process";
import fs from "node:fs";
import path from "node:path";
import { promisify } from "node:util";

import { runInstalledThesisWorkflow } from "./thesis-workflow-tool.js";

const execFileAsync = promisify(execFile);

const CLI_FLAG_MAP = new Map([
  ["--thesis-id", "thesisId"],
  ["--workspace", "workspace"],
  ["--source-pack-dir", "sourcePackDir"],
  ["--thesis-profile-path", "thesisProfilePath"],
  ["--official-statements-config", "officialStatementsConfigPath"],
  ["--official-statements-state", "officialStatementsStatePath"],
  ["--watchlist-config", "watchlistConfigPath"],
  ["--watchlist-state", "watchlistStatePath"],
  ["--polymarket-config", "polymarketConfigPath"],
  ["--polymarket-state", "polymarketStatePath"],
  ["--registry-file", "registryFilePath"],
  ["--semantic-frame", "semanticFrame"],
  ["--probability-direction", "probabilityDirection"],
  ["--state", "state"],
  ["--now-utc", "nowUtc"],
]);

function parseArgvPairs(argv = []) {
  const request = {};
  for (let index = 0; index < argv.length; index += 1) {
    const flag = argv[index];
    if (!CLI_FLAG_MAP.has(flag)) {
      continue;
    }
    const value = argv[index + 1];
    if (value === undefined) {
      throw new Error(`missing value for ${flag}`);
    }
    request[CLI_FLAG_MAP.get(flag)] = value;
    index += 1;
  }
  return request;
}

function resolvePythonPath(rootDir, existsSync = fs.existsSync) {
  const venvPython = path.join(rootDir, ".venv", "bin", "python");
  return existsSync(venvPython) ? venvPython : "python3";
}

function errorResult(stderr, exitCode = 2) {
  return {
    exitCode,
    stdout: "",
    stderr,
    payload: null,
  };
}

export function formatInstalledWorkflowCliHelp() {
  return [
    "Usage:",
    "  node scripts/run_installed_thesis_workflow.js --thesis-id <id> [options]",
    "",
    "Key options:",
    "  --thesis-id <id>",
    "  --workspace <path>",
    "  --source-pack-dir <path>",
    "  --official-statements-config <path>",
    "  --official-statements-state <path>",
    "  --watchlist-config <path>",
    "  --watchlist-state <path>",
    "  --polymarket-config <path>",
    "  --polymarket-state <path>",
    "  --registry-file <path>",
    "  --semantic-frame <value>",
    "  --probability-direction <value>",
    "  --state <value>",
    "  --now-utc <iso8601>",
  ].join("\n");
}

async function execJsonCli({ command, args, cwd, env, fallbackText }) {
  let stdout;
  let stderr;
  try {
    ({ stdout, stderr } = await execFileAsync(command, args, {
      cwd,
      env,
    }));
  } catch (err) {
    const rawStdout = err?.stdout?.trim?.() || "";
    const rawStderr = err?.stderr?.trim?.() || err?.message || "";
    throw new Error(rawStderr || rawStdout || fallbackText);
  }

  const rawStdout = stdout?.trim() || "";
  const rawStderr = stderr?.trim() || "";
  if (!rawStdout) {
    throw new Error(rawStderr || fallbackText);
  }

  try {
    return JSON.parse(rawStdout);
  } catch (err) {
    throw new Error(
      rawStderr ||
        rawStdout ||
        ((err && err.message) || "failed to parse CLI JSON output"),
    );
  }
}

export function parseInstalledWorkflowCliArgs(argv = []) {
  return parseArgvPairs(argv);
}

export function createInstalledWorkflowCliRunners({
  rootDir,
  existsSync = fs.existsSync,
  env = process.env,
} = {}) {
  const python = resolvePythonPath(rootDir, existsSync);
  const sourcePluginScript = path.join(
    rootDir,
    "lobster-intel",
    "scripts",
    "run_source_plugin.py",
  );
  const thesisRuntimeScript = path.join(
    rootDir,
    "lobster-intel",
    "scripts",
    "run_thesis_runtime.py",
  );

  return {
    runSourcePlugin: async ({ pluginDir, workspace, configPath, statePath }) => {
      const args = [sourcePluginScript, pluginDir, "--workspace", workspace];
      if (configPath) {
        args.push("--config-file", configPath);
      }
      if (statePath) {
        args.push("--state-path", statePath);
      }
      return execJsonCli({
        command: python,
        args,
        cwd: rootDir,
        env,
        fallbackText: `NGI Lobster source plugin failed: ${pluginDir}`,
      });
    },
    runThesisRuntime: async ({
      workspace,
      thesisId,
      registryFilePath,
      semanticFrame,
      probabilityDirection,
      state,
      nowUtc,
    }) => {
      const args = [
        thesisRuntimeScript,
        "--workspace",
        workspace,
        "--thesis-id",
        thesisId,
      ];
      if (registryFilePath) {
        args.push("--registry-file", registryFilePath);
      }
      if (semanticFrame) {
        args.push("--semantic-frame", semanticFrame);
      }
      if (probabilityDirection) {
        args.push("--probability-direction", probabilityDirection);
      }
      if (state) {
        args.push("--state", state);
      }
      if (nowUtc) {
        args.push("--now-utc", nowUtc);
      }
      return execJsonCli({
        command: python,
        args,
        cwd: rootDir,
        env,
        fallbackText: `NGI Lobster thesis runtime failed for ${thesisId}`,
      });
    },
  };
}

export async function runInstalledWorkflowCli({
  rootDir,
  argv = [],
  existsSync = fs.existsSync,
  readFileSync = fs.readFileSync,
  runSourcePlugin,
  runThesisRuntime,
}) {
  let request;
  try {
    if (argv.includes("--help") || argv.includes("-h")) {
      return {
        exitCode: 0,
        stdout: formatInstalledWorkflowCliHelp(),
        stderr: "",
        payload: null,
      };
    }

    request = parseInstalledWorkflowCliArgs(argv);
  } catch (err) {
    return errorResult(`ERROR: ${err.message}`);
  }

  if (!request.thesisId) {
    return errorResult("ERROR: --thesis-id is required");
  }

  try {
    const workflowResult = await runInstalledThesisWorkflow({
      rootDir,
      request,
      existsSync,
      readFileSync,
      runSourcePlugin,
      runThesisRuntime,
    });

    if (workflowResult.kind === "missing_paths") {
      return errorResult(
        `ERROR: missing workflow input files:\n${workflowResult.missingPaths.join("\n")}`,
      );
    }
    if (workflowResult.kind === "invalid_profile") {
      return errorResult(
        `ERROR: invalid thesis profile:\n${workflowResult.validationErrors.join("\n")}`,
        1,
      );
    }

    return {
      exitCode: 0,
      stdout: "",
      stderr: "",
      payload: {
        thesis_id: workflowResult.workflow.runtimeRequest.thesisId,
        workspace: workflowResult.workflow.runtimeRequest.workspace,
        source_results: workflowResult.sourceResults,
        runtime_result: workflowResult.runtimeResult,
        summary: workflowResult.summary,
      },
    };
  } catch (err) {
    return errorResult(`ERROR: ${err.message}`, 1);
  }
}
