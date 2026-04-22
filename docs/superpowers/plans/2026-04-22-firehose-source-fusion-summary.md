# Firehose Source Fusion Summary Plan

> **For agentic workers:** Keep this change scoped to source-fusion inputs, one focused test, the fusion CLI, and short operator docs. Do not change probability weighting or delivery behavior in this plan.

**Goal:** Let saved source-fusion artifacts report the actual Firehose source-run event count instead of ignoring Firehose input or reusing another source's counts.

**Architecture:** Extend `SourceFusionInput` and `SourceFusionArtifacts` with one optional-looking but required Firehose payload path, load `firehose-tracker/latest.json` through the existing fusion CLI, and project only summary metadata such as analyzed event count plus timestamp freshness. Preserve the current decision math so this slice improves auditability without silently changing ranking behavior.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Firehose Summary Gap

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused test that passes Firehose source-run artifacts into source fusion.
- [x] Require the saved fusion result to report the correct `firehose.events_analyzed` count.

### Task 2: Load Firehose Into Source Fusion

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/source_fusion.py`
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Extend fusion inputs and artifact loading with the Firehose source payload.
- [x] Read `firehose-tracker/latest.json` by default from the fusion CLI and project the Firehose count into the result.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document that source fusion now reads the Firehose latest artifact by default.
- [x] Keep the docs explicit that Firehose ranking/filtering logic is still a separate unfinished slice.
