# NGI Runtime Spine Implementation Flow Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Translate `docs/superpowers/specs/2026-04-17-ngi-runtime-spine-design.md` into a concrete execution flow that sequences landed runtime work, remaining hardening slices, and the gates that must pass before broader source-platform or fleet work moves forward.

**Architecture:** Treat the runtime-spine design doc as the contract source of truth and the world-monitor roadmap breakdown as the program-order source of truth. This companion maps the design's seven runtime stages, artifact contracts, and verification gates onto code that already exists on `codex/develop`, the plan docs already authored, and the remaining closeout slice still needed for MVP-grade runtime proof.

**Tech Stack:** Markdown planning docs, Python runtime spine under `lobster-intel/packages/lobster-runtime`, delivery helpers under `lobster-intel/packages/lobster-delivery`, OpenClaw install surface in Node.js, pytest and `node:test`

---

## Purpose

`docs/superpowers/specs/2026-04-17-ngi-runtime-spine-design.md` already locks the MVP architecture correctly:

- seven fixed runtime stages
- file artifacts as primary truth
- runtime-owned `active_target`
- `full_compare` / `degraded_compare` / `suppressed`
- OpenClaw heartbeat as the canonical sink

What it still lacked was an execution companion that answers three operational questions:

1. Which parts of the design are already landed on `codex/develop`?
2. Which remaining slices already have concrete plans?
3. In what order should those slices ship so source expansion does not reopen runtime truth design?

This document answers those questions.

## Design Coverage Map

### Stage 1: Tracker

**Landed:**

- source runner normalization and state persistence
- installed source-pack defaults
- replayable source run artifacts under `lobster-intel/data/runtime/sources/<plugin-id>/runs/*.json`
- rebuildable per-plugin source indexes and CLI tooling
- structured tracker manifest contracts for source family, replayability, state mode, and follow-up queues

**Current contract boundary:**

- trackers fetch, normalize, dedupe, and persist cursor lineage
- trackers do not decide `P_AI`, `active_target`, compare legality, or delivery

**Execution record:**

- [`2026-04-20-tracker-capability-surface.md`](2026-04-20-tracker-capability-surface.md)

### Stage 2: Source-Specific Analyzer

**Landed:**

- analyzer-driven observation shaping now lives in `lobster_runtime.analyzers`
- runtime preserves a generic fallback analyzer for unknown source types
- source-aware behavior is documented as a runtime seam instead of hardcoded policy scattered through delivery or wrappers

**Execution record:**

- [`2026-04-20-analyzer-interface-contract.md`](2026-04-20-analyzer-interface-contract.md)

### Stage 3: Fusion Engine

**Landed:**

- fusion artifact generation
- `P_AI`, confidence, freshness, and `dq_status`
- replayable lineage from fusion back to observations and evidence

**Hardening rule:**

- future source work must feed fusion through observations only
- no source-platform slice may reintroduce raw-source-specific fusion logic

### Stage 4: Active Target Resolver

**Landed:**

- thesis-scoped target registry support
- default registry discovery by `thesis_id`
- runtime-owned target resolution path
- bundled thesis-pack defaults
- conservative live-search fallback when registry resolution is absent but candidate metadata still aligns conservatively

**Execution record:**

- [`2026-04-20-default-thesis-pack-discovery.md`](2026-04-20-default-thesis-pack-discovery.md)
- [`2026-04-20-runtime-live-search-fallback.md`](2026-04-20-runtime-live-search-fallback.md)

### Stage 5: Compare Engine

**Landed:**

- explicit `full_compare`, `degraded_compare`, and `suppressed`
- machine-readable fallback reason codes
- replayable compare artifacts

**Still open:**

- fallback hardening must be completed before any cross-thesis ranking work

### Stage 6: Alert Decision

**Landed:**

- compare-aware alert decisions
- novelty gates against prior runtime snapshots
- artifact-backed alert records

**Still open:**

- design-level verification that downstream consumers only render runtime truth and do not silently infer target identity or explanation fields

### Stage 7: Delivery Adapter

**Partial:**

- runtime already writes OpenClaw heartbeat delivery receipts
- `lobster_delivery` already exposes contract helpers and bundle verification for review fixtures

**Still open:**

- direct verification from real thesis runtime artifacts, not only hand-built example payloads
- explicit MVP closeout proof for delivery receipt, truth-only consumption, and contract completeness

**Next dependency:**

- [`2026-04-20-runtime-spine-verification-gates.md`](2026-04-20-runtime-spine-verification-gates.md)

## Artifact And Verification Gate Map

The design doc defines six MVP completion gates. Their current execution status is:

### Gate 1: Full Artifact Chain From One Run

**Status:** landed

Backed by:

- `lobster-intel/tests/test_runtime_spine.py`
- [`2026-04-19-ngi-runtime-spine.md`](2026-04-19-ngi-runtime-spine.md)

### Gate 2: `runtime/<thesis_id>/latest.json` Is The Only Runtime Truth Consumed Downstream

**Status:** landed

Backed by:

- [`2026-04-20-runtime-spine-verification-gates.md`](2026-04-20-runtime-spine-verification-gates.md)
- runtime-artifact contract verification in `lobster_delivery.runtime_contract`

### Gate 3: Compare Fixtures Prove All Three Compare Modes

**Status:** landed

Backed by:

- [`2026-04-20-runtime-live-search-fallback.md`](2026-04-20-runtime-live-search-fallback.md)
- `lobster-intel/tests/test_runtime_spine.py`

### Gate 4: OpenClaw-Native Delivery Emits A Real Receipt Artifact

**Status:** landed

Backed by:

- [`2026-04-20-runtime-spine-verification-gates.md`](2026-04-20-runtime-spine-verification-gates.md)
- `lobster-intel/scripts/verify_runtime_contract_bundle.py`

### Gate 5: Artifact Lineage Is Auditable Back To Evidence

**Status:** landed

Backed by:

- runtime lineage helpers
- replay helpers
- source history replay/index tooling

### Gate 6: Indexes Can Be Deleted And Rebuilt Without Losing Truth

**Status:** landed for runtime/source indexes

Backed by:

- runtime rebuild helpers
- source index rebuild CLI

## Guardrails For Future Work

All remaining implementation must preserve these design constraints:

1. Trackers and source workers may write evidence, compiled, and queue artifacts, but they do not decide runtime truth.
2. Analyzers may shape observations, but they do not select targets, compare, or deliver.
3. Delivery renders runtime-owned fields and receipts; it does not reinterpret the target contract.
4. New work must keep rebuildability from files as a first-class property.
5. New source-platform work must use `runtime/sources/<plugin-id>/...` for source artifacts and must not create new delivery-owned truth paths.

## Recommended Execution Order

When the runtime-spine design is used as the controlling contract, the closeout sequence that has now landed was:

1. [`2026-04-20-installed-thesis-contract-validation.md`](2026-04-20-installed-thesis-contract-validation.md)
   Reason: the install surface must fail closed before more runtime defaults are added.
2. [`2026-04-20-default-thesis-pack-discovery.md`](2026-04-20-default-thesis-pack-discovery.md)
   Reason: the target resolver should consume a thesis-owned package shape, not loose overrides.
3. [`2026-04-20-runtime-live-search-fallback.md`](2026-04-20-runtime-live-search-fallback.md)
   Reason: compare legality depends on explicit fallback semantics.
4. [`2026-04-20-runtime-spine-verification-gates.md`](2026-04-20-runtime-spine-verification-gates.md)
   Reason: the design's MVP completion gates should close before broader source-platform work expands the surface area.
5. [`2026-04-20-tracker-capability-surface.md`](2026-04-20-tracker-capability-surface.md)
   Reason: once runtime closeout is stable, source onboarding needs a structured manifest seam.
6. [`2026-04-20-analyzer-interface-contract.md`](2026-04-20-analyzer-interface-contract.md)
   Reason: analyzer extraction should happen after runtime truth semantics stop moving.
7. [`2026-04-20-linked-content-extraction-platform.md`](2026-04-20-linked-content-extraction-platform.md)
   Reason: richer source breadth should consume the stable tracker/analyzer/runtime seam, not define it.

Those seven slices are now represented by concrete plan records. The next main-line work should therefore move up a layer: multi-thesis fleet operations and portfolio / world-monitor consumers that stay downstream of the runtime truth boundary.

## Implementation Flow Summary

The runtime-spine design is no longer a greenfield design. The core closeout program for MVP runtime truth is now landed:

- the thesis runtime core exists
- contract hardening and verification proof are in place
- source-platform seams now exist for tracker contracts and analyzers
- fleet and portfolio work remain downstream consumers of this runtime truth

That means the repo should be operated with this sequence in mind:

```text
runtime truth maintenance
-> source onboarding against stable seams
-> multi-thesis fleet operations
-> portfolio / world-monitor layer
```
