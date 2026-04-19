import test from "node:test";
import assert from "node:assert/strict";

import { formatDefaultWorkflowText } from "../workflow-default-tool.js";

test("returns a user-facing message when workflow stdout is NO_REPLY", () => {
  const digestPath = "/tmp/latest_digest.md";

  assert.equal(
    formatDefaultWorkflowText("NO_REPLY", "", digestPath),
    `Workflow ran with no new posts. Digest: ${digestPath}`
  );
});

test("preserves explicit workflow output when new posts were processed", () => {
  const digestPath = "/tmp/latest_digest.md";
  const workflowOutput = "Gooaye 有 2 則新貼文";

  assert.equal(
    formatDefaultWorkflowText(workflowOutput, "", digestPath),
    workflowOutput
  );
});

test("falls back to stderr when stdout is empty", () => {
  const digestPath = "/tmp/latest_digest.md";
  const errorOutput = "tracker failed";

  assert.equal(
    formatDefaultWorkflowText("", errorOutput, digestPath),
    errorOutput
  );
});

test("falls back to the digest path when both outputs are empty", () => {
  const digestPath = "/tmp/latest_digest.md";

  assert.equal(
    formatDefaultWorkflowText("", "", digestPath),
    `Workflow ran with no new posts. Digest: ${digestPath}`
  );
});
