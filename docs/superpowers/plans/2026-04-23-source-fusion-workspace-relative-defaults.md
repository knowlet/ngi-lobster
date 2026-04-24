# Source Fusion Workspace Relative Defaults Plan

> **For agentic workers:** Keep this change scoped to source-fusion CLI path resolution, one focused CLI test, and short operator docs. Do not change fusion math, ranking, or delivery behavior in this plan.

**Goal:** Make `build_source_fusion.py --workspace ...` resolve its default relative input/output paths from that workspace instead of the caller's current shell directory.

**Architecture:** Treat `--workspace` as the base directory for every non-absolute source-fusion path. Preserve explicit absolute paths unchanged, keep historical Firehose replay behavior untouched, and only change how the CLI resolves relative file locations before loading artifacts or writing the output JSON.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`pathlib`/`json`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Lock Workspace-Relative CLI Behavior

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused CLI test that runs from a directory outside the requested workspace.
- [x] Require default source-fusion input and output paths to resolve inside the passed `--workspace`.

### Task 2: Resolve Relative Paths From Workspace

**Files:**
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Add one path helper that keeps absolute paths unchanged and anchors relative paths to `--workspace`.
- [x] Use that helper for all source-fusion input artifacts and the default output artifact path.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that source-fusion path defaults are anchored to `--workspace`.
- [x] Keep existing replay and optional-Firehose behavior descriptions intact.
