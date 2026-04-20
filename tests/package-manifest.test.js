import test from "node:test";
import assert from "node:assert/strict";
import fs from "node:fs";

const pkg = JSON.parse(fs.readFileSync(new URL("../package.json", import.meta.url), "utf8"));

test("package manifest exposes helper scripts for runtime setup and workflow execution", () => {
  assert.equal(pkg.scripts["bootstrap-runtime"], "./scripts/bootstrap_runtime.sh");
  assert.equal(
    pkg.scripts["run-installed-workflow"],
    "node ./scripts/run_installed_thesis_workflow.js",
  );
  assert.equal(pkg.scripts["demo-gooaye"], "./scripts/demo_run_gooaye.sh");
});

test("package manifest exposes executable bin commands", () => {
  assert.equal(
    pkg.bin["ngi-lobster-bootstrap-runtime"],
    "./scripts/bootstrap_runtime.sh",
  );
  assert.equal(
    pkg.bin["ngi-lobster-run-installed-workflow"],
    "./scripts/run_installed_thesis_workflow.js",
  );
});
