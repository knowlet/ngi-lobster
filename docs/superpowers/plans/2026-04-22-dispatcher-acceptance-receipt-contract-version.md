# Dispatcher Acceptance Receipt Contract Version Plan

> **For agentic workers:** Keep this change scoped to the dispatcher acceptance wrapper CLI, dispatcher receipt writer, focused tests, and short operator docs. Do not change runtime gate behavior in this plan.

**Goal:** Fail closed when dispatcher acceptance reuses a persisted positive-control receipt from a different contract version, and persist that contract version on dispatcher receipt artifacts for auditability.

**Architecture:** Restore the one-shot `run_dispatcher_acceptance.py` wrapper as the operator entrypoint, validate any reused persisted receipt against the requested `thesis_id`, `positive_run_id`, and `contract_version`, then keep that same `contract_version` on the emitted dispatcher receipt artifact so the shared E2E bundle can be audited against one contract lineage.

**Tech Stack:** Python 3.11+, stdlib `argparse`/`json`/`pathlib`, unittest, Markdown docs

**Status:** Implemented in the writable workspace on 2026-04-22.

---

### Task 1: Lock The Contract-Version Guard

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add a focused test that requires dispatcher receipt artifacts to persist `contract_version`.
- [x] Add a focused CLI test that rejects persisted positive-control receipts whose `contract_version` no longer matches the requested runtime run.

### Task 2: Restore The Acceptance Wrapper And Receipt Audit Field

**Files:**
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`
- Create: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [x] Restore the one-shot dispatcher acceptance wrapper CLI for suppressed + positive runtime runs.
- [x] Validate persisted receipt reuse against `thesis_id`, `run_id`, and `contract_version`.
- [x] Persist `contract_version` on dispatcher receipt artifacts.

### Task 3: Document The Fail-Closed Operator Flow

**Files:**
- Modify: `lobster-intel/README.md`
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document the wrapper CLI usage and output bundle path.
- [x] Document that persisted receipt reuse now fails closed on `contract_version` mismatch.
