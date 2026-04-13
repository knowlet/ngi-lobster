import { definePluginEntry } from "openclaw/plugin-sdk/plugin-entry";

export default definePluginEntry({
  id: "ngi-lobster",
  name: "NGI Lobster",
  description:
    "Open intelligence plugin framework for OpenClaw. NGI stands for Narrative Gap Index.",
  register() {
    // v0 native wrapper plugin.
    // Core runtime currently lives in the repo's lobster-intel/ Python packages.
    // This wrapper exists so the project can be installed through
    // `openclaw plugins install <path-or-package>` while the runtime is being
    // migrated into a native OpenClaw plugin surface.
  },
});

