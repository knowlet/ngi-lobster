# Default Workflow Digest Contract Plan

**Goal:** Make the installed default workflow preserve the generated digest path through the thesis runtime handoff, so operator-facing output matches the product cut requirement for a readable markdown digest.

**Architecture:** Keep `process_gooaye_channel.py` as the digest producer, then have `lobster_runtime.runtime_spine` carry forward any existing `digest_path` and `latest_digest_path` from the prior thesis `latest.json` before it writes the runtime snapshot. Expose those preserved paths through the runtime `artifact_paths` summary.

**Tech Stack:** Python 3.11+, pytest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-21.

### Task 1: Lock The Default Workflow Contract

**Files:**
- Modify: `lobster-intel/tests/test_default_workflow.py`

- [x] Require the default workflow summary to expose a `latest_digest` artifact path.
- [x] Verify RED before runtime changes.

### Task 2: Preserve Digest Metadata Across Runtime Handoff

**Files:**
- Modify: `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`

- [x] Carry forward `digest_path` and `latest_digest_path` from the prior thesis `latest.json` when present.
- [x] Add preserved digest paths to the emitted `artifact_paths` payload.

### Task 3: Align Operator Docs

**Files:**
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Update the native wrapper description so it reflects the preserved digest surface alongside runtime and delivery artifacts.
