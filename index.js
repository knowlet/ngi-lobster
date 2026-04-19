import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";
import fs from "node:fs";

import { formatDefaultWorkflowText } from "./workflow-default-tool.js";

const execFileAsync = promisify(execFile);

export default definePluginEntry({
  id: "ngi-lobster",
  name: "NGI Lobster",
  description:
    "Open intelligence plugin framework for OpenClaw. NGI stands for Narrative Gap Index.",
  register(api) {
    const rootDir = api.pluginRootDir ?? path.dirname(new URL(import.meta.url).pathname);
    const venvPython = path.join(rootDir, '.venv', 'bin', 'python');
    const bootstrap = path.join(rootDir, 'scripts', 'bootstrap_runtime.sh');

    async function ensureRuntimeReady() {
      try {
        await execFileAsync(venvPython, ['-V'], { cwd: rootDir });
        return null;
      } catch (err) {
        return {
          content: [
            {
              type: 'text',
              text: `NGI Lobster runtime not ready. Run:\n\ncd ${rootDir} && ./scripts/bootstrap_runtime.sh\n\nThen retry.`
            }
          ],
          details: { error: (err && err.message) || 'venv check failed', bootstrap }
        };
      }
    }

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
          if (preflight) return preflight;

          const scriptPath = path.join(rootDir, 'scripts', 'demo_run_gooaye.sh');
          const { stdout, stderr } = await execFileAsync(scriptPath, [], {
            cwd: rootDir,
            env: process.env
          });
          const text = (stdout || stderr || '').trim();
          return {
            content: [
              {
                type: 'text',
                text: text || 'NGI Lobster demo ran with no output.'
              }
            ],
            details: {
              stdout: stdout?.trim() || '',
              stderr: stderr?.trim() || ''
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
          if (preflight) return preflight;

          const scriptPath = path.join(rootDir, 'scripts', 'run_default_workflow.sh');
          const { stdout, stderr } = await execFileAsync(scriptPath, [], {
            cwd: rootDir,
            env: process.env
          });
          const runtimePath = path.join(rootDir, 'lobster-intel', 'data', 'runtime', 'gooaye', 'latest.json');
          let runtime = {};
          if (fs.existsSync(runtimePath)) {
            runtime = JSON.parse(fs.readFileSync(runtimePath, 'utf8'));
          }
          const digestPath = runtime.digest_path || path.join(rootDir, 'lobster-intel', 'data', 'compiled', 'gooaye', 'latest_digest.md');
          const text = formatDefaultWorkflowText(stdout, stderr, digestPath);
          return {
            content: [{ type: 'text', text }],
            details: {
              digestPath,
              runtimePath,
              newCount: runtime.new_count ?? null,
              stdout: stdout?.trim() || '',
              stderr: stderr?.trim() || ''
            }
          };
        }
      },
      { name: "ngi_lobster_run_default_workflow" }
    );
  },
});
