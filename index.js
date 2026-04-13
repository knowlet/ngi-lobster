import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";
import { execFile } from "node:child_process";
import { promisify } from "node:util";
import path from "node:path";

const execFileAsync = promisify(execFile);

export default definePluginEntry({
  id: "ngi-lobster",
  name: "NGI Lobster",
  description:
    "Open intelligence plugin framework for OpenClaw. NGI stands for Narrative Gap Index.",
  register(api) {
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
          const rootDir = api.pluginRootDir ?? path.dirname(new URL(import.meta.url).pathname);
          const venvPython = path.join(rootDir, '.venv', 'bin', 'python');
          const bootstrap = path.join(rootDir, 'scripts', 'bootstrap_runtime.sh');
          // Check venv
          try {
            const which = await execFileAsync(venvPython, ['-V'], { cwd: rootDir });
          } catch (err) {
            // venv missing or invalid - return repair instructions instead of throwing
            return {
              content: [
                {
                  type: 'text',
                  text: `NGI Lobster runtime not ready. Run the bootstrap to create a compatible Python environment:\n
cd ${rootDir} && ./scripts/bootstrap_runtime.sh\n\nAfter bootstrap completes, run the demo tool again.`
                }
              ],
              details: { error: (err && err.message) || 'venv check failed' }
            };
          }

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
  },
});
