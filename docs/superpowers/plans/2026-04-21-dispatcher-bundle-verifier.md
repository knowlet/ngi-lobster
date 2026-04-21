# Dispatcher Bundle Verifier Plan

> **For agentic workers:** Keep this change scoped to the existing verification CLI, its focused tests, and operator docs that mention bundle verification. Do not change dispatcher runtime behavior in this plan.

**Goal:** Let operators verify the actual `dispatcher_e2e_bundle` artifact emitted by the acceptance workflow, not just raw example payloads.

**Architecture:** Teach `verify_alert_contract_bundle.py` to recognize a persisted `lobster.delivery.dispatcher_e2e_bundle.v1` JSON artifact and feed its `fixtures` list into the same contract validator already used for raw runtime payloads. Lock the behavior with a focused CLI test and document the operator flow in the repo docs.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, pytest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-21.

---

### Task 1: Lock The Dispatcher Bundle Artifact Contract

**Files:**
- Modify: `lobster-intel/tests/test_verify_alert_contract_bundle_cli.py`

- [x] Add a focused CLI test that writes a real `dispatcher_e2e_bundle.v1` artifact and expects verifier success.
- [x] Run the focused pytest command and verify RED before changing the script.

### Task 2: Accept Persisted Bundle Artifacts In The Verifier

**Files:**
- Modify: `lobster-intel/scripts/verify_alert_contract_bundle.py`

- [x] Detect the persisted dispatcher bundle shape and expand its `fixtures` payloads for validation.
- [x] Keep the existing raw payload and list input behavior unchanged.

### Task 3: Document The Operator Verification Path

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Add the post-acceptance verification command that points at `bundles/<bundle-id>.json`.
- [x] Explain that the verifier now accepts either raw payload fixtures or the persisted bundle artifact.
