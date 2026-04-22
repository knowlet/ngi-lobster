# Firehose Historical Fusion Replay Plan

> **For agentic workers:** Keep this change scoped to the source-fusion CLI, one focused replay test, and short operator docs. Do not change fusion math, ranking, or delivery behavior in this plan.

**Goal:** Let operators build a source-fusion artifact from a specific historical Firehose normalized source run instead of only the current `latest.json`.

**Architecture:** Reuse `replay_source_run()` as the single history reader, then map its replay view back into the existing source-fusion artifact shape before calling `build_source_fusion_result()`. Keep the default `latest.json` path unchanged so normal runs behave exactly as before.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-23.

---

### Task 1: Lock Historical Replay CLI Behavior

**Files:**
- Modify: `lobster-intel/tests/test_source_fusion.py`

- [x] Add a focused CLI test that writes one historical `firehose-tracker/runs/<run_id>.json` artifact in a temp workspace.
- [x] Require `build_source_fusion.py --workspace ... --firehose-run-id ...` to emit the historical Firehose event count, source run id, and latest timestamps in both stdout summary and saved fusion JSON.

### Task 2: Reuse Source History In Fusion CLI

**Files:**
- Modify: `lobster-intel/scripts/build_source_fusion.py`

- [x] Add `--workspace` and `--firehose-run-id` arguments without changing the current default latest-artifact path.
- [x] Reuse `replay_source_run()` and normalize that replay payload back into the `evidence.items` shape expected by source fusion.

### Task 3: Keep Operator Docs Honest

**Files:**
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document how to target a specific historical Firehose source run when rebuilding source-fusion artifacts for audit or replay work.
