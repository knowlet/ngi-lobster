# Firehose Fusion Signal Scoring Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn normalized Firehose events into a deterministic `firehose.peace_score` so source-fusion artifacts carry an actual replayable Firehose signal instead of a hard-coded placeholder.

**Architecture:** Keep the existing normalized Firehose artifact contract unchanged and compute the score inside source fusion from replayed `evidence.items`. Use a small heuristic based on normalized tags plus priority weighting so the same source run always produces the same score in both latest and historical replay paths.

**Tech Stack:** Python 3.11+, unittest, existing Lobster runtime/source-fusion scripts, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Prove Firehose artifacts produce a score

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused unit test that feeds source fusion one peace-oriented Firehose item and one escalation-oriented Firehose item with different priorities.
- [x] Require the fusion result to persist a non-zero `firehose.peace_score` derived from those items.
- [x] Verify the score is stable for historical replay by extending the CLI replay test summary expectations.

### Task 2: Implement replayable Firehose scoring

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_fusion.py`

- [x] Add small helpers for priority normalization, tag polarity classification, and weighted score aggregation.
- [x] Compute `firehose.peace_score` from normalized Firehose items without changing other source-fusion inputs.
- [x] Keep empty or unclassified Firehose input mapped to a neutral score instead of throwing.

### Task 3: Document the new score

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `README.md`

- [x] Document that source fusion now emits a heuristic Firehose peace score derived from normalized tags/priorities.
- [x] Keep the docs explicit that this remains a lightweight runtime heuristic, not delivery policy.
