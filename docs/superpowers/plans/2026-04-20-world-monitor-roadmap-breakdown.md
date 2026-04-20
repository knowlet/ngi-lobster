# World Monitor Roadmap Breakdown

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Decompose `docs/superpowers/specs/2026-04-17-world-monitor-roadmap.md` into concrete workstreams, ordered slices, and execution checkpoints that can be planned and shipped incrementally.

**Architecture:** Keep the roadmap's original build order intact: per-thesis runtime truth first, source platform second, multi-thesis fleet third, and portfolio logic last. Treat this document as the execution companion that maps already-landed work to roadmap phases and defines the next slices without redefining the product thesis.

**Tech Stack:** Markdown planning docs, current OpenClaw plugin surface, Node.js wrapper layer, Python runtime spine and source-platform code under `lobster-intel/`

---

## Purpose

The roadmap spec sets direction correctly, but it is still too coarse to drive day-to-day implementation choices. This companion breaks the roadmap into:

- **tracks** aligned to the original phases
- **slices** small enough to implement and verify independently
- **dependencies** so later work does not pull unstable assumptions upward
- **status markers** showing what is already landed versus still missing

This is not a new vision document. It is the operational breakdown of the existing roadmap.

## Current State Mapped To The Roadmap

### Phase 1: Per-Thesis Runtime Core

**Already landed on `codex/develop`:**

- thesis runtime spine and artifact lineage
- compare modes for `full_compare`, `degraded_compare`, and `suppressed`
- installed thesis workflow defaults
- packaged runtime commands and cron entrypoint
- default source state persistence for installed runs
- installed thesis catalog for operator discovery
- default thesis registry discovery

**Interpretation:**

Phase 1 is no longer blank. The core thesis runtime contract exists and is installable. What remains is mostly **hardening** and **contract tightening**, not first-pass scaffolding.

### Phase 2: Source Platform

**Already landed on `codex/develop`:**

- replayable per-plugin source run artifacts under `runs/*.json`
- rebuildable per-plugin SQLite source index
- operator CLI for source replay and index rebuild

**Interpretation:**

Phase 2 has started, but only at the artifact support layer. The platform still lacks a generic tracker SDK, analyzer seams, richer fixtures, linked-content extraction, and stronger Firehose onboarding.

### Phase 3: Multi-Thesis Runtime Fleet

**Partial prerequisites landed:**

- bundled thesis profiles
- bundled target registries
- runtime discovery by `thesis_id`
- operator-facing installed thesis catalog

**Interpretation:**

These are **fleet prerequisites**, not fleet operations. The repo can describe multiple theses, but it does not yet schedule, isolate, retry, and audit multiple thesis runtimes as a fleet.

### Phase 4: Portfolio / World Monitor Layer

**Not started in the product sense.**

There is no fleet-level ranking artifact, no cross-thesis novelty layer, and no global operator digest that consumes only thesis runtime truth.

## Dependency Rules

The roadmap's dependency order should stay strict:

1. **Per-thesis truth contract must stabilize before fleet logic.**
2. **Source onboarding seams must stabilize before scaling source count.**
3. **Fleet coordination must exist before portfolio ranking.**
4. **Portfolio logic must only read thesis outputs and rebuildable indexes.**

That gives the following effective dependency chain:

```text
runtime truth contract
-> source replay / indexing / onboarding seams
-> multi-thesis execution + audit
-> cross-thesis ranking and operator views
```

## Execution Tracks

## Track A: Per-Thesis Runtime Core Closeout

This track is already underway. The remaining work should be treated as **hardening slices**, not as a restart.

### A1. Thesis Contract Validation

**What it closes:**

- invalid thesis profiles
- invalid registry references
- missing required runtime contract fields

**Why it matters:**

Installed workflows are only safe to scale if invalid thesis metadata fails early and concretely.

**Exit signal:**

- thesis profiles and registries validate before execution
- invalid contracts produce machine-readable errors

### A2. Thesis Pack Discovery Defaults

**What it closes:**

- per-thesis bundling of profile + registry + source defaults
- cleaner operator-facing thesis packaging

**Why it matters:**

The fleet layer will need a thesis-owned package shape. This is the bridge from single-thesis defaults to multi-thesis execution.

**Exit signal:**

- a thesis can be resolved from one pack-level contract instead of many loose override flags

### A3. Runtime Fallback Hardening

**What it closes:**

- explicit fallback reason codes
- live-search or degraded target resolution paths
- consistent suppressed/degraded behavior when direct registry matches fail

**Why it matters:**

Portfolio logic later depends on trustworthy compare semantics. It cannot reason over ad hoc fallback behavior.

**Exit signal:**

- degraded and fallback states are explicit, replayable, and test-covered

### A4. Real Delivery Path E2E Proof

**What it closes:**

- proof that the real delivery boundary receives runtime truth correctly
- shared E2E run record for suppressed vs delivered fixtures

**Why it matters:**

The roadmap allows portfolio work only after per-thesis truth and delivery receipts are real, not simulated.

**Exit signal:**

- real dispatcher or declared production sink boundary emits verifiable receipt evidence

## Track B: Source Platform Expansion

This is the current priority program after runtime closeout.

### B1. Source History And Indexing

**Status:** landed

This slice is the first correct Phase 2 seam because it proves source artifacts are replayable and indexes are rebuildable from files.

### B2. Tracker Capability Surface

**What it should add:**

- source capability declarations
- tracker interface helpers
- normalized per-source metadata expectations

**Why it matters:**

Without a stable tracker contract, new source families will keep forcing one-off runtime changes.

### B3. Analyzer Interface Contract

**What it should add:**

- source-specific analyzer outputs
- observation-shaping contract between trackers and thesis runtime
- test fixtures for analyzer outputs

**Why it matters:**

The roadmap explicitly wants "source-specific AI analyzers" without fusion instability. That needs a first-class interface.

### B4. Source Fixture Packs

**What it should add:**

- replayable fixture bundles per source family
- deterministic backfill and regression inputs
- local analytics support against source indexes

**Why it matters:**

This is the lowest-cost way to expand source count without losing testability.

### B5. Linked-Content Extraction Platform Slice

**What it should add:**

- crawler / linked-content queue handling
- extraction artifacts
- replayable downstream inputs for analyzers

**Why it matters:**

The repo still calls out linked-content extraction as incomplete. This is one of the largest blockers to real Phase 2 breadth.

### B6. Firehose Platformization

**What it should add:**

- normalized Firehose event contract
- ingest/replay tooling
- source indexing and filtering support

**Why it matters:**

Firehose is still an operator burden instead of a stable source platform component.

## Track C: Multi-Thesis Runtime Fleet

This track should start only after Tracks A and B are stable enough that new theses do not re-open core runtime design.

### C1. Thesis Registry And Pack Catalog

**What it should add:**

- one authoritative thesis registry for installed fleets
- pack-to-thesis resolution
- explicit enabled/disabled thesis state

### C2. Scheduler And Cadence Control

**What it should add:**

- per-thesis cadence configuration
- auditable run scheduling
- operator-visible next-run and last-run state

### C3. Thesis-Isolated Runtime Paths

**What it should add:**

- strict isolation for `active_target`, runtime state, compare history, and delivery receipts by thesis
- no accidental overwrite across concurrent runs

### C4. Retry / Recovery / Backfill Policies

**What it should add:**

- explicit retry states
- failure receipts
- safe replay and backfill semantics by thesis

### C5. Shared Source Infrastructure

**What it should add:**

- reuse of shared source families across multiple theses
- per-thesis consumption without cross-thesis truth leakage

## Track D: Portfolio / World Monitor Layer

This track should not start until the fleet layer is real.

### D1. Fleet Runtime Catalog Artifact

**What it should add:**

- one rebuildable catalog of thesis runtime outputs
- summary rows keyed by thesis id and latest run id

### D2. Ranking Artifact

**What it should add:**

- cross-thesis ordering by `ngi_gap`, freshness, confidence, and novelty
- explicit explanation fields for why a thesis was ranked

### D3. Novelty And Cluster Detection

**What it should add:**

- cross-thesis signal clustering
- anomaly grouping
- overlap and correlation hints for operators

### D4. World-Monitor Digest

**What it should add:**

- global operator digest derived only from thesis outputs
- machine-readable and human-readable portfolio artifacts

### D5. Global Operator View

**What it should add:**

- OpenClaw-native portfolio inspection surface
- drill-down from ranking entry to thesis truth artifacts

## Recommended Near-Term Execution Order

If we continue working strictly in roadmap order, the next slices should be:

1. **A1 Thesis Contract Validation**
   Because installed thesis defaults now exist, but they still need a stricter contract gate before scale.
2. **A2 Thesis Pack Discovery Defaults**
   Because the fleet layer will need a thesis-owned package shape, not loose file references.
3. **A3 Runtime Fallback Hardening**
   Because fallback semantics must be stable before any cross-thesis aggregation.
4. **B2 Tracker Capability Surface**
   Because Phase 2 needs a reusable onboarding seam, not just replay utilities.
5. **B3 Analyzer Interface Contract**
   Because new source families need a stable analyzer boundary into observations and fusion.
6. **B5 Linked-Content Extraction Platform Slice**
   Because the repo still names this as a major product gap and it unlocks richer source breadth.
7. **B6 Firehose Platformization**
   Because Firehose is still one of the main operator-heavy gaps blocking source scale.
8. **C1 Multi-Thesis Registry And Pack Catalog**
   Only after the above slices stop moving foundational contracts.

## What Counts As "Roadmap Decomposed"

This breakdown is complete only if future work follows these rules:

1. New plans should reference one program and one slice from this breakdown.
2. No Phase 4 portfolio slice should start until Programs A and B are materially stable.
3. Multi-thesis work should not redefine per-thesis truth contracts.
4. Source-platform work should preserve replayability and rebuildability from files.

## Immediate Next Planning Targets

The most sensible next plan files to author from this breakdown are:

- `2026-04-20-installed-thesis-contract-validation.md`
- `2026-04-20-default-thesis-pack-discovery.md`
- `2026-04-20-runtime-live-search-fallback.md`
- `2026-04-20-tracker-capability-surface.md`
- `2026-04-20-analyzer-interface-contract.md`
- `2026-04-20-linked-content-extraction-platform.md`

Those six plans would turn the roadmap from a broad sequence into an actively executable queue.
