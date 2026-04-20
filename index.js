import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import fs from "node:fs";
import { fileURLToPath } from "node:url";

import {
  describeBundledThesisProfile,
  listBundledThesisProfiles,
  runInstalledThesisWorkflow
} from "./thesis-workflow-tool.js";
import { formatDefaultWorkflowText } from "./workflow-default-tool.js";

const execFileAsync = promisify(execFile);

export default definePluginEntry({
  id: "ngi-lobster",
  name: "NGI Lobster",
  description:
    "Open intelligence plugin framework for OpenClaw. NGI stands for Narrative Gap Index.",
  register(api) {
    const rootDir = api.pluginRootDir ?? path.dirname(fileURLToPath(import.meta.url));
    const venvPython = path.join(rootDir, ".venv", "bin", "python");
    const bootstrap = path.join(rootDir, "scripts", "bootstrap_runtime.sh");
    const sourcePluginScript = path.join(rootDir, "lobster-intel", "scripts", "run_source_plugin.py");
    const thesisRuntimeScript = path.join(rootDir, "lobster-intel", "scripts", "run_thesis_runtime.py");

    async function ensureRuntimeReady() {
      try {
        await execFileAsync(venvPython, ["-V"], { cwd: rootDir });
        return null;
      } catch (err) {
        return {
          content: [
            {
              type: "text",
              text: `NGI Lobster runtime not ready. Run:\n\ncd ${rootDir} && ./scripts/bootstrap_runtime.sh\n\nThen retry.`
            }
          ],
          details: { error: (err && err.message) || "venv check failed", bootstrap }
        };
      }
    }

    function buildMissingFileError(missingPaths) {
      return {
        ok: false,
        content: [
          {
            type: "text",
            text: `NGI Lobster runtime input file(s) not found:\n\n${missingPaths.map((item) => `- ${item}`).join("\n")}`
          }
        ],
        details: { missingPaths }
      };
    }

    function buildInvalidProfileError(validationErrors) {
      return {
        content: [
          {
            type: "text",
            text: `NGI Lobster thesis profile is incomplete:\n\n${validationErrors.map((item) => `- ${item}`).join("\n")}`
          }
        ],
        details: { validationErrors }
      };
    }

    function readRuntimeJsonSafe(runtimePath) {
      if (!fs.existsSync(runtimePath)) {
        return {};
      }
      try {
        return JSON.parse(fs.readFileSync(runtimePath, "utf8"));
      } catch {
        return {};
      }
    }

    async function runThesisRuntimeCli(args) {
      const preflight = await ensureRuntimeReady();
      if (preflight) return { ok: false, ...preflight };

      const scriptPath = thesisRuntimeScript;
      const cliArgs = [scriptPath];
      for (const [flag, value] of args) {
        if (value !== undefined && value !== null && value !== "") {
          cliArgs.push(flag, String(value));
        }
      }
      let stdout;
      let stderr;
      try {
        ({ stdout, stderr } = await execFileAsync(venvPython, cliArgs, {
          cwd: rootDir,
          env: process.env
        }));
      } catch (err) {
        const rawStdout = err?.stdout?.trim?.() || "";
        const rawStderr = err?.stderr?.trim?.() || err?.message || "";
        return {
          ok: false,
          content: [
            {
              type: "text",
              text: rawStderr || rawStdout || "NGI Lobster thesis runtime failed."
            }
          ],
          details: {
            scriptPath,
            stdout: rawStdout,
            stderr: rawStderr,
            exitCode: err?.code ?? null
          }
        };
      }
      const rawStdout = stdout?.trim() || "";
      const rawStderr = stderr?.trim() || "";
      let parsed = {};
      if (rawStdout) {
        try {
          parsed = JSON.parse(rawStdout);
        } catch (err) {
          return {
            ok: false,
            content: [
              {
                type: "text",
                text: rawStdout
              }
            ],
            details: {
              scriptPath,
              stdout: rawStdout,
              stderr: rawStderr,
              parseError: (err && err.message) || "failed to parse thesis runtime output"
            }
          };
        }
      }
      return {
        ok: true,
        content: [
          {
            type: "text",
            text: JSON.stringify(parsed)
          }
        ],
        details: {
          scriptPath,
          stdout: rawStdout,
          stderr: rawStderr,
          ...parsed
        }
      };
    }

    async function runSourcePluginCli({ pluginDir, workspace, configPath }) {
      const preflight = await ensureRuntimeReady();
      if (preflight) return { ok: false, ...preflight };

      const scriptPath = sourcePluginScript;
      const cliArgs = [scriptPath, pluginDir, "--workspace", workspace];
      if (configPath) {
        cliArgs.push("--config-file", configPath);
      }

      let stdout;
      let stderr;
      try {
        ({ stdout, stderr } = await execFileAsync(venvPython, cliArgs, {
          cwd: rootDir,
          env: process.env
        }));
      } catch (err) {
        const rawStdout = err?.stdout?.trim?.() || "";
        const rawStderr = err?.stderr?.trim?.() || err?.message || "";
        return {
          ok: false,
          content: [
            {
              type: "text",
              text: rawStderr || rawStdout || `NGI Lobster source plugin failed: ${pluginDir}`
            }
          ],
          details: {
            scriptPath,
            pluginDir,
            workspace,
            configPath,
            stdout: rawStdout,
            stderr: rawStderr,
            exitCode: err?.code ?? null
          }
        };
      }

      const rawStdout = stdout?.trim() || "";
      const rawStderr = stderr?.trim() || "";
      let parsed = {};
      if (rawStdout) {
        try {
          parsed = JSON.parse(rawStdout);
        } catch (err) {
          return {
            ok: false,
            content: [
              {
                type: "text",
                text: rawStdout
              }
            ],
            details: {
              scriptPath,
              pluginDir,
              workspace,
              configPath,
              stdout: rawStdout,
              stderr: rawStderr,
              parseError: (err && err.message) || "failed to parse source plugin output"
            }
          };
        }
      }

      return {
        ok: true,
        content: [
          {
            type: "text",
            text: JSON.stringify(parsed)
          }
        ],
        details: {
          scriptPath,
          pluginDir,
          workspace,
          configPath,
          stdout: rawStdout,
          stderr: rawStderr,
          ...parsed
        }
      };
    }

    function resultToError(result, fallbackText) {
      const error = new Error(result?.content?.[0]?.text || fallbackText);
      error.toolResult = result;
      return error;
    }

    api.registerTool(
      {
        name: "ngi_lobster_list_installed_theses",
        label: "NGI Lobster List Installed Theses",
        description:
          "List bundled thesis profiles and runtime defaults for the installed thesis workflow.",
        parameters: {
          type: "object",
          additionalProperties: false,
          properties: {
            thesisId: {
              type: "string",
              description: "Optional thesis id to return a detailed single-thesis view."
            }
          }
        },
        async execute(input) {
          const request = input || {};
          const details = request.thesisId
            ? describeBundledThesisProfile(rootDir, request.thesisId)
            : { theses: listBundledThesisProfiles(rootDir) };
          if (request.thesisId && !details) {
            return {
              ok: false,
              content: [
                {
                  type: "text",
                  text: `No bundled thesis found for id: ${request.thesisId}`
                }
              ],
              details: { thesisId: request.thesisId }
            };
          }

          return {
            content: [
              {
                type: "text",
                text: JSON.stringify(details)
              }
            ],
            details
          };
        }
      },
      { name: "ngi_lobster_list_installed_theses" }
    );

    api.registerTool(
      {
        name: "ngi_lobster_demo",
        label: "NGI Lobster Demo",
        description:
          "Run the local NGI Lobster demo path and return the current Gooaye ingest smoke-test result.",
        parameters: {
          type: "object",
          additionalProperties: false,
          properties: {}
        },
        async execute() {
          const preflight = await ensureRuntimeReady();
          if (preflight) return { ok: false, ...preflight };

          const scriptPath = path.join(rootDir, "scripts", "run_default_workflow.sh");
          const { stdout, stderr } = await execFileAsync(scriptPath, [], {
            cwd: rootDir,
            env: process.env
          });
          const runtimePath = path.join(rootDir, "lobster-intel", "data", "runtime", "gooaye", "latest.json");
          const runtime = readRuntimeJsonSafe(runtimePath);
          const result = {
            plugin: "gooaye-tracker",
            version: "0.1.0",
            new_count: runtime.new_count ?? 0,
            channel: runtime.channel ?? "@Gooaye",
            run_id: runtime.run_id ?? null,
            digest_path: runtime.digest_path ?? null
          };
          const text = JSON.stringify(result);
          return {
            content: [
              {
                type: "text",
                text
              }
            ],
            details: {
              runtimePath,
              stdout: stdout?.trim() || "",
              stderr: stderr?.trim() || "",
              ...result
            }
          };
        }
      },
      { name: "ngi_lobster_demo" }
    );

    api.registerTool(
      {
        name: "ngi_lobster_run_default_workflow",
        label: "NGI Lobster Run Default Workflow",
        description:
          "Run the default installed workflow: ingest Gooaye, write evidence/compiled/runtime artifacts, and return the latest digest path.",
        parameters: {
          type: "object",
          additionalProperties: false,
          properties: {}
        },
        async execute() {
          const preflight = await ensureRuntimeReady();
          if (preflight) return { ok: false, ...preflight };

          const scriptPath = path.join(rootDir, "scripts", "run_default_workflow.sh");
          const { stdout, stderr } = await execFileAsync(scriptPath, [], {
            cwd: rootDir,
            env: process.env
          });
          const runtimePath = path.join(rootDir, "lobster-intel", "data", "runtime", "gooaye", "latest.json");
          const runtime = readRuntimeJsonSafe(runtimePath);
          const digestPath = runtime.digest_path || path.join(rootDir, "lobster-intel", "data", "compiled", "gooaye", "latest_digest.md");
          const text = formatDefaultWorkflowText(stdout, stderr, digestPath);
          return {
            content: [{ type: "text", text }],
            details: {
              digestPath,
              runtimePath,
              newCount: runtime.new_count ?? null,
              stdout: stdout?.trim() || "",
              stderr: stderr?.trim() || ""
            }
          };
        }
      },
      { name: "ngi_lobster_run_default_workflow" }
    );

    api.registerTool(
      {
        name: "ngi_lobster_run_thesis_runtime",
        label: "NGI Lobster Run Thesis Runtime",
        description:
          "Run the thesis runtime spine through lobster-intel/scripts/run_thesis_runtime.py and return the runtime snapshot plus artifact paths.",
        parameters: {
          type: "object",
          additionalProperties: false,
          required: ["thesisId"],
          properties: {
            thesisId: {
              type: "string",
              description: "Thesis identifier used in runtime artifact paths."
            },
            workspace: {
              type: "string",
              description: "Workspace root passed to the thesis runtime CLI. Defaults to the plugin root."
            },
            officialStatementsPath: {
              type: "string",
              description: "Optional path to a JSON file with official statements input."
            },
            watchlistPath: {
              type: "string",
              description: "Optional path to a JSON file with watchlist input."
            },
            polymarketPath: {
              type: "string",
              description: "Optional path to a JSON file with polymarket input."
            },
            registryFilePath: {
              type: "string",
              description:
                "Optional path to a JSON file with target registry entries. If omitted, the runtime discovers lobster-intel/data/runtime/thesis-registry/<thesisId>.json automatically."
            },
            semanticFrame: {
              type: "string",
              description: "Semantic frame passed to the runtime spine."
            },
            probabilityDirection: {
              type: "string",
              description: "Probability direction passed to the runtime spine."
            },
            state: {
              type: "string",
              description: "Runtime state passed to the runtime spine."
            },
            nowUtc: {
              type: "string",
              description: "Optional ISO-8601 timestamp used as the run clock."
            }
          }
        },
        async execute(input) {
          const request = input || {};
          const missingPaths = [
            request.officialStatementsPath,
            request.watchlistPath,
            request.polymarketPath,
            request.registryFilePath
          ].filter((candidate) => candidate && !fs.existsSync(candidate));
          if (missingPaths.length > 0) {
            return buildMissingFileError(missingPaths);
          }

          const result = await runThesisRuntimeCli([
            ["--workspace", request.workspace || rootDir],
            ["--thesis-id", request.thesisId],
            ["--official", request.officialStatementsPath],
            ["--watchlist", request.watchlistPath],
            ["--polymarket", request.polymarketPath],
            ["--registry-file", request.registryFilePath],
            ["--semantic-frame", request.semanticFrame],
            ["--probability-direction", request.probabilityDirection],
            ["--state", request.state],
            ["--now-utc", request.nowUtc]
          ]);
          return result;
        }
      },
      { name: "ngi_lobster_run_thesis_runtime" }
    );

    api.registerTool(
      {
        name: "ngi_lobster_run_installed_thesis_workflow",
        label: "NGI Lobster Run Installed Thesis Workflow",
        description:
          "Run the installed source trackers from bundled or explicit source-pack configs, then invoke the thesis runtime spine with bundled or explicit thesis defaults.",
        parameters: {
          type: "object",
          additionalProperties: false,
          required: ["thesisId"],
          properties: {
            thesisId: {
              type: "string",
              description: "Thesis identifier used in runtime artifact paths."
            },
            workspace: {
              type: "string",
              description: "Workspace root passed to source plugins and the thesis runtime. Defaults to the plugin root."
            },
            sourcePackDir: {
              type: "string",
              description: "Optional directory containing bundled source-pack JSON files."
            },
            thesisProfilePath: {
              type: "string",
              description: "Optional path to a thesis profile JSON file. Defaults to lobster-intel/examples/thesis-profiles/<thesisId>.json when present."
            },
            officialStatementsConfigPath: {
              type: "string",
              description: "Optional path to the official statements source-pack JSON."
            },
            watchlistConfigPath: {
              type: "string",
              description: "Optional path to the watchlist source-pack JSON."
            },
            polymarketConfigPath: {
              type: "string",
              description: "Optional path to the polymarket source-pack JSON."
            },
            registryFilePath: {
              type: "string",
              description:
                "Optional path to a JSON file with target registry entries. If omitted, the runtime discovers lobster-intel/data/runtime/thesis-registry/<thesisId>.json automatically."
            },
            semanticFrame: {
              type: "string",
              description: "Semantic frame passed to the runtime spine."
            },
            probabilityDirection: {
              type: "string",
              description: "Probability direction passed to the runtime spine."
            },
            state: {
              type: "string",
              description: "Runtime state passed to the runtime spine."
            },
            nowUtc: {
              type: "string",
              description: "Optional ISO-8601 timestamp used as the run clock."
            }
          }
        },
        async execute(input) {
          const preflight = await ensureRuntimeReady();
          if (preflight) return { ok: false, ...preflight };

          try {
            const request = input || {};
            const workflowResult = await runInstalledThesisWorkflow({
              rootDir,
              request,
              existsSync: fs.existsSync,
              runSourcePlugin: async (sourceRun) => {
                const result = await runSourcePluginCli(sourceRun);
                if (!result.ok) {
                  throw resultToError(
                    result,
                    `NGI Lobster source plugin failed: ${sourceRun.pluginId}`
                  );
                }
                return result.details;
              },
              runThesisRuntime: async (runtimeRequest) => {
                const result = await runThesisRuntimeCli([
                  ["--workspace", runtimeRequest.workspace],
                  ["--thesis-id", runtimeRequest.thesisId],
                  ["--registry-file", runtimeRequest.registryFilePath],
                  ["--semantic-frame", runtimeRequest.semanticFrame],
                  ["--probability-direction", runtimeRequest.probabilityDirection],
                  ["--state", runtimeRequest.state],
                  ["--now-utc", runtimeRequest.nowUtc]
                ]);
                if (!result.ok) {
                  throw resultToError(
                    result,
                    `NGI Lobster thesis runtime failed for ${runtimeRequest.thesisId}`
                  );
                }
                return result.details;
              }
            });

            if (workflowResult.kind === "invalid_profile") {
              return buildInvalidProfileError(workflowResult.validationErrors);
            }

            if (workflowResult.kind === "missing_paths") {
              return buildMissingFileError(workflowResult.missingPaths);
            }

            return {
              ok: false,
              content: [
                {
                  type: "text",
                  text: workflowResult.summary
                }
              ],
              details: workflowResult
            };
          } catch (err) {
            if (err?.toolResult) {
              return err.toolResult;
            }
            return {
              content: [
                {
                  type: "text",
                  text: err?.message || "NGI Lobster installed thesis workflow failed."
                }
              ],
              details: {
                error: err?.message || "workflow failure"
              }
            };
          }
        }
      },
      { name: "ngi_lobster_run_installed_thesis_workflow" }
    );
  }
});
