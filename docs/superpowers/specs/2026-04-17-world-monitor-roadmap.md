# World Monitor Roadmap

Date: 2026-04-17

## Status Snapshot

As of 2026-04-19, the baseline `Per-Thesis Runtime Core` spine has landed in the repo.

The implemented baseline currently proves:

- one thesis run can consume installed source runtime artifacts and emit evidence, observations, fusion, runtime snapshot, compare, alert, and delivery receipt artifacts
- compare can emit `full_compare`, `degraded_compare`, and `suppressed`
- compare results can be replayed from artifacts and indexed back into a rebuildable SQLite view
- delivery crosses the OpenClaw heartbeat boundary through `lobster_delivery`

What remains before Phase 1 is fully productized:

- make `openclaw plugins install` the primary operator/runtime entrypoint
- harden active-target resolution beyond registry plus local market candidate artifacts
- extract explicit source-analyzer seams from the current inline MVP runtime logic
- turn the current single-thesis path into a stable operator workflow rather than a baseline proof

## Vision

Build NGI Lobster into a world-monitor-grade intelligence system that can ingest many OSINT and market-facing signals, find information gaps, and surface thesis-level opportunities where first-principles reality and public market pricing diverge.

The end-state is not a single report generator. It is a fleet of thesis runtimes plus a portfolio layer that can discover and rank global opportunities.

## Program Structure

The work is divided into three programs:

1. `Per-Thesis Runtime Core`
2. `Source Platform`
3. `Portfolio / World Monitor Layer`

These programs must be built in that order. The portfolio layer depends on stable per-thesis truth contracts. The source platform must expand without forcing repeated rewrites of fusion and compare logic.

## Guiding Rules

- Bottom-layer stability is more important than top-layer breadth.
- File artifacts remain primary truth.
- Indexes are rebuildable and non-authoritative.
- Each thesis owns its own runtime truth and active target.
- Cross-thesis portfolio logic consumes runtime truth; it does not redefine it.

## Phase 1: Per-Thesis Runtime Core

### Goal

Ship an installable OpenClaw plugin that produces a hard runtime truth for one thesis and auto-delivers through OpenClaw heartbeat.

### Scope

- thin trackers
- source-specific AI analyzers
- observation schema
- fusion to `P_AI`
- active target resolver
- compare contract
- alert decision
- delivery receipt

### Current Status

Implemented baseline:

- thesis-scoped runtime orchestration in `lobster_runtime.runtime_spine`
- thesis runtime CLI in `lobster-intel/scripts/run_thesis_runtime.py`
- runtime spine contract coverage in `lobster-intel/tests/test_runtime_spine.py`
- replay, lineage, and SQLite rebuild helpers for runtime artifacts

Remaining Phase 1 closure work:

- OpenClaw plugin-surface packaging and operator-facing install flow
- stronger registry and live-search target resolution
- cleaner source analyzer boundaries so source families can expand without inflating the runtime core
- more operational fixtures around real thesis inputs and delivery review flows

### Exit Criteria

- `openclaw plugins install` works for the plugin package
- one thesis run produces a full artifact lineage
- compare can emit `full_compare`, `degraded_compare`, and `suppressed`
- live OpenClaw delivery emits a receipt artifact

### Initial Thesis Candidates

- Iran / regional escalation
- oil shipping disruption
- semiconductor supply risk
- TSMC-related geopolitical stress
- satellite or space-related escalation signals

## Phase 2: Source Platform

### Goal

Make source onboarding cheap enough that many new trackers and analyzers can be added without destabilizing fusion.

### Scope

- tracker SDK
- plugin manifests and capability declarations
- analyzer interface contract
- replay and backfill tooling
- source-level test fixtures
- source indexing and local analytics support

### Exit Criteria

- a new source family can be added by implementing a tracker and analyzer without changing the runtime core contract
- source replay works from artifact files
- source indexes rebuild cleanly from files

### Priority Source Families

Priority 1:

- Firehose event streams
- RSS and official statements
- crawler and linked-content extraction
- Polymarket market feeds

Priority 2:

- ADS-B aircraft movement
- AIS shipping and choke-point monitoring
- NOTAM and no-fly notices

Priority 3:

- public satellite pass predictions
- GNSS interference heatmaps
- geolocated social video
- public rocket or missile trajectory data

## Phase 3: Multi-Thesis Runtime Fleet

### Goal

Run many thesis runtimes under one installation while preserving per-thesis truth boundaries.

### Scope

- thesis registry
- scheduling and cadence control
- per-thesis configuration
- backfill policies
- retry and recovery logic
- shared source infrastructure

### Exit Criteria

- multiple theses can run concurrently without overwriting each other's truth
- each thesis maintains its own `active_target`, `P_AI`, compare state, and delivery history
- scheduling and retries are auditable by thesis and run

## Phase 4: Portfolio / World Monitor Layer

### Goal

Consume many thesis runtimes and surface a global monitor view of information gaps, novel anomalies, and opportunity ranking.

### Scope

- cross-thesis ranking by `ngi_gap`
- cross-thesis novelty detection
- signal cluster discovery
- resource and attention prioritization
- world-monitor digests
- global operator views

### Exit Criteria

- portfolio logic reads only runtime outputs and artifact indexes
- portfolio ranking can explain why a thesis was prioritized
- portfolio artifacts can trace every surfaced opportunity back to thesis-level truth

## Long-Term Product Shape

The long-term product shape is:

```text
many source families
-> many per-source analyzers
-> many thesis runtimes
-> one portfolio / world monitor layer
-> OpenClaw-native operator and delivery surfaces
```

This keeps the system composable:

- new sources do not force portfolio rewrites
- new theses do not force tracker rewrites
- new delivery routes remain downstream of the same truth contract

## Planning Implications

Near-term implementation planning should prioritize:

1. closing the remaining per-thesis Phase 1 gaps above
2. hardening registry and target-resolution behavior under real source data
3. extracting source platform seams from the baseline runtime implementation
4. delaying portfolio features until thesis truth is stable

## Summary

The roadmap commits to the full world-monitor ambition, but the build order is strict:

1. hard per-thesis runtime truth
2. extensible source platform
3. multi-thesis fleet operations
4. portfolio / world monitor intelligence

This ordering minimizes rework and keeps the system aligned with the core product thesis: runtime truth first, global breadth second.
