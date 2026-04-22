# Firehose Fusion Audit Metadata Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Expose Firehose audit timestamps in saved source-fusion artifacts without changing ranking or delivery decisions.

**Architecture:** Keep Firehose normalization as the source of truth, then project only summary metadata from the normalized source-run payload into the source-fusion result. Preserve existing probability math and CLI defaults so this slice improves auditability only.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, unittest, Markdown docs

---

### Task 1: Lock The Firehose Audit Metadata Gap

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [ ] Add a focused test that passes Firehose items with distinct `published_at_utc` and `collected_at_utc` values into source fusion.
- [ ] Require the fusion result to persist `firehose.latest_event_at_utc` and `firehose.latest_collected_at_utc`.

### Task 2: Project Firehose Audit Metadata Into Fusion Results

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_fusion.py`
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/fusion.py`
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [ ] Derive the latest Firehose event timestamp from normalized evidence items and the latest collection timestamp from the source-run payload.
- [ ] Persist those fields under the existing `firehose` summary object in the fusion artifact and CLI output path.
- [ ] Keep all ranking, gap, and delivery inputs unchanged.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [ ] Document that source fusion now reports Firehose event freshness metadata in addition to the analyzed count.
- [ ] Keep the docs explicit that Firehose ranking/filtering remains a separate unfinished slice.
