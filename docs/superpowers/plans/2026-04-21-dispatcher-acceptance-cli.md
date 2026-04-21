# Dispatcher Acceptance CLI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Give operators one machine-readable CLI that turns a known suppressed runtime run and positive-control runtime run into dispatcher artifacts plus a shared E2E bundle.

**Architecture:** Keep the lower-level `write_dispatcher_artifact.py` and `build_dispatcher_e2e_bundle.py` entrypoints unchanged, but add `run_dispatcher_acceptance.py` as a thin wrapper that loads the two runtime run artifacts, writes the suppressed and positive dispatcher outputs with the supplied delivery proof, then builds one shared bundle and returns a single JSON summary.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, pytest

**Status:** Implemented in the writable workspace on 2026-04-21. Follow-up on 2026-04-21 preserved the shared `bundle_id` as `alert_disposition.e2e_run_id` on the written dispatcher artifacts as well, verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-ingest:lobster-intel/packages/lobster-plugins:lobster-intel/packages/lobster-runtime ./.venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_artifact_writer.py -q` (`6 passed`).

---

### Task 1: Lock The One-Shot Operator Contract

**Files:**
- Create: `lobster-intel/tests/test_dispatcher_acceptance_cli.py`

- [x] Add a focused CLI acceptance test that installs real runtime/compare/alert artifacts and asserts one command writes suppressed + delivered dispatcher artifacts plus the shared bundle.
- [x] Run the focused test and verify RED on the missing CLI entrypoint.

### Task 2: Add The Wrapper CLI

**Files:**
- Create: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [x] Load the two runtime run payloads directly from the workspace.
- [x] Call `write_dispatcher_artifacts()` once for the suppressed run and once for the positive run with explicit delivery proof.
- [x] Call `write_dispatcher_e2e_bundle()` with the same two run ids and emit one JSON summary payload.

### Task 3: Document The Operator Shortcut

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `lobster-intel/docs/operations/reporting.md`

- [x] Document the new one-shot acceptance command and required flags.
- [x] Explain that the wrapper emits dispatcher alert/receipt artifacts and the bundle artifact in one run.
