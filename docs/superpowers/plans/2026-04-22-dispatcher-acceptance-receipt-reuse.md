# Dispatcher Acceptance Receipt Reuse Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Let dispatcher acceptance reuse the real runtime receipt proof instead of requiring operators to retype delivery-proof fields.

**Architecture:** Keep `run_dispatcher_acceptance.py` as the operator entrypoint, but teach it to load the persisted runtime receipt for the positive-control run before writing dispatcher artifacts. Preserve explicit CLI overrides for exceptional cases, fail closed when the positive path lacks both an existing receipt and complete overrides, and document the preferred operator flow.

**Tech Stack:** Python 3.11+, stdlib `json`/`pathlib`, pytest, Markdown docs

---

### Task 1: Lock The Receipt-Reuse Contract

**Files:**
- Modify: `lobster-intel/tests/test_dispatcher_acceptance_cli.py`

- [ ] Add a focused CLI test that seeds a real runtime receipt and runs `run_dispatcher_acceptance.py` without explicit proof arguments.
- [ ] Verify the command succeeds, writes dispatcher artifacts plus the shared bundle, and preserves the existing `delivery_proof.proof_id`.

### Task 2: Reuse Persisted Runtime Receipts

**Files:**
- Modify: `lobster-intel/scripts/run_dispatcher_acceptance.py`

- [ ] Add a helper that loads `lobster-intel/data/delivery/<thesis-id>/receipts/<run-id>.json` when present.
- [ ] Make positive-control receipt arguments optional and merge any explicit overrides onto the persisted receipt payload.
- [ ] Fail closed with a clear error when the positive run still lacks a complete delivery receipt after merge.

### Task 3: Document The Preferred Acceptance Path

**Files:**
- Modify: `lobster-intel/README.md`

- [ ] Update the dispatcher acceptance section to state that operators should reuse persisted runtime receipts by default.
- [ ] Keep the explicit proof flags documented as an override path, not the primary flow.
