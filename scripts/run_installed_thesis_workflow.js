#!/usr/bin/env node

import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

import {
  createInstalledWorkflowCliRunners,
  runInstalledWorkflowCli,
} from "../installed-workflow-cli.js";

const rootDir = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const { runSourcePlugin, runThesisRuntime } = createInstalledWorkflowCliRunners({
  rootDir,
  existsSync: fs.existsSync,
  env: process.env,
});

const result = await runInstalledWorkflowCli({
  rootDir,
  argv: process.argv.slice(2),
  existsSync: fs.existsSync,
  readFileSync: fs.readFileSync,
  runSourcePlugin,
  runThesisRuntime,
});

if (result.exitCode !== 0) {
  console.error(result.stderr);
  process.exit(result.exitCode);
}

console.log(JSON.stringify(result.payload));
