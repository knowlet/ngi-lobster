export function formatDefaultWorkflowText(stdout, stderr, digestPath) {
  const stdoutText = stdout?.trim() || "";
  if (stdoutText && stdoutText !== "NO_REPLY") {
    return stdoutText;
  }

  const stderrText = stderr?.trim() || "";
  if (stderrText) {
    return stderrText;
  }

  return `Workflow ran with no new posts. Digest: ${digestPath}`;
}
