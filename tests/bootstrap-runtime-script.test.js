import test from "node:test";
import assert from "node:assert/strict";
import { execFile } from "node:child_process";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);

test("bootstrap_runtime.sh prints help and exits before performing setup", async () => {
  const { stdout, stderr } = await execFileAsync(
    "bash",
    ["./scripts/bootstrap_runtime.sh", "--help"],
    {
      cwd: new URL("..", import.meta.url),
    },
  );

  assert.equal(stderr, "");
  assert.match(stdout, /Usage:/);
  assert.match(stdout, /bootstrap_runtime\.sh/);
  assert.match(stdout, /python3/);
});
