# Source Fusion Workspace Tilde Expansion Plan

> **For agentic workers:** Keep this plan scoped to path-anchoring behavior for `build_source_fusion.py` and do not alter fusion scoring, ranking, or delivery logic.

**Goal:** Ensure `build_source_fusion.py` accepts `--workspace` values expressed with home expansion (`~`) and resolves non-absolute artifact paths beneath that workspace.

**Architecture:** Treat `--workspace` as user input that should be expanded through `Path(...).expanduser()` before default path anchors apply. Keep absolute arg semantics unchanged for input/output override paths.

**Tech Stack:** Python 3.11+, pathlib, unittest

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Add workspace tilde regression test

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a CLI test that passes `--workspace` as `~/workspace`, sets `HOME`, and runs from a different cwd.
- [x] Verify output path and firehose summary still resolve under the expanded workspace.

### Task 2: Clarify operator docs

**Files:**
- Modify: `lobster-intel/README.md`

- [x] Document that `--workspace` is expanded with `~` before resolving default non-absolute paths.
