# Dispatcher Artifact Writer Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Write real dispatcher alert and receipt artifacts from runtime payloads so the existing runtime verifier and dispatcher E2E bundle builder can operate on actual delivery outputs instead of hand-installed fixtures.

**Architecture:** Add a `dispatcher_artifacts` helper under `lobster_delivery` that accepts one runtime payload plus an optional delivery proof, writes `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json`, and writes `receipts/<run-id>.json` only for positive-control `would_send` runs. Keep the contract helpers and bundle builder unchanged; they should read the emitted artifacts without extra translation.

**Tech Stack:** Python 3.11+, stdlib `json`/`argparse`/`pathlib`, pytest

**Status:** Implemented in the writable workspace on 2026-04-21 and re-verified with `PYTHONPATH=lobster-intel/packages/lobster-core:lobster-intel/packages/lobster-delivery:lobster-intel/packages/lobster-runtime:lobster-intel/packages/lobster-ingest .venv/bin/python -m pytest lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/tests/test_dispatcher_e2e_bundle.py lobster-intel/tests/test_alert_contract_view.py lobster-intel/tests/test_runtime_contract_bundle.py -q` (`21 passed`). Commit/push remains blocked here because this workspace is not a git repo.

---

### Task 1: Lock The Dispatcher Artifact Contract In Tests

**Files:**
- Create: `lobster-intel/tests/test_dispatcher_artifact_writer.py`

- [x] Add a happy-path test for a suppressed runtime payload that writes only the alert artifact.
- [x] Add a happy-path test for a delivered runtime payload that writes both alert and receipt artifacts with normalized `delivery_proof.proof_id`.
- [x] Add a compatibility test that proves the written artifacts can be consumed by the existing dispatcher bundle loader / runtime contract loader.
- [x] Add CLI coverage that reads a runtime payload file and writes the expected alert + receipt artifacts.

### Task 2: Implement Dispatcher Artifact Writer And CLI

**Files:**
- Create: `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`
- Create: `lobster-intel/scripts/write_dispatcher_artifact.py`

- [x] Implement a helper that writes `alerts/<run-id>.json` from a runtime payload.
- [x] Implement receipt writing for positive-control `would_send` runs and fail closed when `delivery_proof` is incomplete.
- [x] Add a CLI that reads a runtime payload file and optional receipt metadata, then prints the written artifact paths.

### Task 3: Document Operator Flow

**Files:**
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `lobster-intel/README.md`

- [x] Document how operators emit real dispatcher artifacts before running the runtime verifier or dispatcher bundle builder.
- [x] Run focused verification for the new writer plus the affected contract tests.
- [ ] Commit

```bash
git add docs/superpowers/plans/2026-04-21-dispatcher-artifact-writer.md lobster-intel/tests/test_dispatcher_artifact_writer.py lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py lobster-intel/scripts/write_dispatcher_artifact.py lobster-intel/docs/operations/reporting.md lobster-intel/README.md
git commit -m "feat: add dispatcher artifact writer"
```
