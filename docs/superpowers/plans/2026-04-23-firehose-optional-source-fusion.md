# Firehose Optional Source Fusion Input Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let source-fusion artifacts build successfully even when the Firehose normalization bridge has not produced a `latest.json` artifact yet.

**Architecture:** Keep Firehose wired into source fusion, but treat the Firehose artifact as an optional input at load time. When the configured Firehose path is missing, load an empty source payload so fusion output still renders deterministic zero-count Firehose metadata instead of crashing the CLI.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Lock The Missing Firehose Contract

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused unit test that proves `load_source_fusion_artifacts()` returns an empty Firehose payload when the Firehose artifact path does not exist.
- [x] Add a focused CLI test that proves `build_source_fusion.py` still writes a fusion artifact and reports zero analyzed Firehose events when Firehose input is absent.

### Task 2: Make Firehose Input Optional

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_fusion.py`
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Add a small loader helper so required source artifacts still fail closed, while the Firehose artifact path can fall back to an empty payload.
- [x] Keep fusion output shape stable by preserving the `firehose` summary object with `events_analyzed = 0` and null latest timestamps when the input artifact is missing.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`

- [x] Document that source-fusion can run before Firehose normalization exists, and that missing Firehose input yields zero-count audit metadata instead of a hard failure.
