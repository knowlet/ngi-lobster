# Runtime Contract Bundle Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a runtime-artifact-backed verifier that reads thesis runtime, compare, alert, and receipt JSON files directly from the workspace and fails closed when required contract fields are missing.

**Architecture:** Keep the existing example `verify_alert_contract_bundle.py` flow for curated PO review fixtures. Add a separate `runtime_contract` helper under `lobster_delivery` plus a thin CLI that reconstructs one contract view from `lobster-intel/data/runtime/<thesis-id>/...` and `lobster-intel/data/delivery/<thesis-id>/...`.

**Tech Stack:** Python 3.11+, stdlib `json`/`argparse`/`pathlib`, pytest

**Status:** Implemented on 2026-04-21 in the writable workspace. Commit/push remains blocked here because this workspace is not a git repo.

---

### Task 1: Freeze The Runtime Artifact Contract

**Files:**
- Create: `lobster-intel/tests/test_runtime_contract_bundle.py`

- [x] Add fixture-based tests for a complete runtime bundle, fail-closed receipt proof handling, workspace loading, and CLI verification.

### Task 2: Implement Runtime Contract Helpers

**Files:**
- Create: `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`
- Modify: `lobster-intel/packages/lobster-delivery/lobster_delivery/__init__.py`
- Create: `lobster-intel/scripts/verify_runtime_contract_bundle.py`

- [x] Add a normalized `proof_id` surface, required-field validation, and workspace artifact loading.

### Task 3: Document Operator Flow

**Files:**
- Modify: `lobster-intel/docs/operations/reporting.md`
- Modify: `docs/INSTALL_OPENCLAW.md`

- [x] Document when to use the example bundle verifier vs the runtime-artifact verifier.
