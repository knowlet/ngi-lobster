# Firehose Normalization Filtering Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let operators filter low-signal Firehose records during normalization so replayable source artifacts only include the tags and priorities they want to carry into downstream audit flows.

**Architecture:** Extend `normalize_firehose_events()` with a small, explicit filtering contract that runs after raw-event normalization and before runtime artifacts are written. Keep the output artifact shape stable, add filter metadata under `normalization`, and expose the same controls through the existing CLI so operators can use the feature without editing code.

**Tech Stack:** Python 3, unittest, existing Lobster ingest/runtime scripts

---

### Task 1: Add failing coverage for normalization filters

**Files:**
- Modify: `lobster-intel/tests/test_firehose_events.py`

- [x] Add one focused unit test for `include_tags` and `min_priority` filtering.
- [x] Add one focused CLI test that passes repeated `--include-tag` and `--min-priority` arguments.
- [x] Require the artifact summary to report both kept and filtered event counts.

### Task 2: Implement normalization-side filtering

**Files:**
- Modify: `lobster-intel/packages/lobster-ingest/lobster_ingest/firehose.py`

- [x] Add normalized tag matching and priority ranking helpers.
- [x] Filter normalized Firehose items before writing `runs/<run_id>.json` and `latest.json`.
- [x] Persist filter settings plus kept/filtered counts under the `normalization` object without changing the replay artifact contract.

### Task 3: Expose filtering in the CLI and docs

**Files:**
- Modify: `lobster-intel/scripts/normalize_firehose_events.py`
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`
- Modify: `README.md`

- [x] Add repeatable `--include-tag` flags and `--min-priority` to the CLI.
- [x] Document that filtering happens at normalization time and still does not change runtime ranking logic.
- [x] Update the top-level gap note so the repository status matches the new behavior.
