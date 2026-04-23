# Source Fusion Path Expansion Hardening Plan

> **For agentic workers:** Keep this change scoped to source-fusion path normalization, one focused CLI regression test, and short operator docs. Do not change fusion math, ranking, or delivery behavior in this plan.

**Goal:** Treat `~` home-style absolute paths as true absolute paths in `build_source_fusion.py`, while keeping the existing workspace-anchor behavior for plain relative paths.

**Architecture:** Expand incoming source-fusion path arguments with `expanduser()` before absolute-path detection in `build_source_fusion.py`. Preserve fallback behavior where non-absolute paths continue to resolve from `--workspace`.

**Tech Stack:** Python 3.11+, stdlib `pathlib`/`subprocess`/`json`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Lock User-Home Path Expansion

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused CLI test that passes input/output paths using `~` and validates command success plus output path resolution.
- [x] Ensure the test confirms this behavior is independent of the current working directory.

### Task 2: Expand User Paths Before Workspace Resolution

**Files:**
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Call `Path(...).expanduser()` before deciding whether a path is absolute for CLI path resolution.
- [x] Keep existing `--workspace` defaults and absolute/relative semantics unchanged for non-`~` paths.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that absolute paths, including home-expanded forms, are not workspace-rooted.
