# Firehose Fusion Run Provenance Plan

> **For agentic workers:** Keep this change scoped to source-fusion audit metadata, one focused CLI summary path, its tests, and short operator docs. Do not change ranking or delivery behavior in this plan.

**Goal:** Let saved source-fusion artifacts identify which Firehose normalized source run supplied the audit metadata.

**Architecture:** Reuse the existing `run_id` already persisted by the Firehose normalization bridge, then project that value into the saved fusion artifact and CLI summary under the existing `firehose` audit object. Preserve all current probability math, gap logic, and optional-input behavior.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Lock The Firehose Provenance Contract

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Extend the focused source-fusion test to require `firehose.source_run_id` when Firehose input is present.
- [x] Extend the missing-Firehose CLI test to require a null `firehose_source_run_id` summary instead of a failure.

### Task 2: Project Firehose Run Provenance Into Fusion Results

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_fusion.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/fusion.py`
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Read `run_id` from the normalized Firehose source artifact when present.
- [x] Persist that value under `firehose.source_run_id` in saved fusion output and CLI summary paths.
- [x] Keep missing Firehose input mapped to a null provenance field instead of changing optional-input behavior.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that source-fusion audit metadata now includes the normalized Firehose source run id.
- [x] Keep the docs explicit that Firehose ranking/filtering remains a separate unfinished slice.
