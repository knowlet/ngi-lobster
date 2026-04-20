# NGI Runtime Spine Design

Status: validated design for MVP direction; thesis-scoped baseline implemented on 2026-04-19
Date: 2026-04-17

## Purpose

Define the MVP architecture for an installable NGI Lobster runtime that:

- installs through `openclaw plugins install`
- treats NGI as runtime truth rather than a static report
- computes `P_AI` / escalation view from first-principles signals
- compares that runtime output against the same active Polymarket target on the same semantic and numeric frame
- auto-delivers alerts through the OpenClaw-native heartbeat path

This document defines the MVP spine only. It also establishes the contracts that later source expansion and world-monitor portfolio work must consume without rewriting runtime truth.

## Implementation Snapshot

As of 2026-04-19, the per-thesis runtime core described here exists in the repo as a baseline implementation centered on:

- `lobster-intel/packages/lobster-runtime/lobster_runtime/runtime_spine.py`
- `lobster-intel/scripts/run_thesis_runtime.py`
- `lobster-intel/tests/test_runtime_spine.py`

The implemented slice currently proves:

- thesis-scoped evidence, observation, fusion, compare, runtime, alert, and receipt artifacts
- compare modes `full_compare`, `degraded_compare`, and `suppressed`
- replayable compare logic and lineage tracing from receipt back to evidence
- a rebuildable SQLite index over runtime run artifacts
- OpenClaw heartbeat-boundary delivery receipts through `lobster_delivery`

The implemented slice does not yet prove:

- a true live market search fallback beyond the currently installed market source artifacts
- a fully separated analyzer SDK or source-platform seam per source family
- multi-thesis scheduling and fleet operations
- `openclaw plugins install` as the fully productized runtime/operator entrypoint

## Product Decisions Locked In

- MVP architecture: `Layered Runtime Spine`
- First implementation target: `per-thesis runtime core`
- Primary truth store: file artifacts
- Secondary index: `SQLite` or `PGlite`, rebuildable from artifacts
- Tracker contract: thin trackers for fetch, normalize, dedupe, cursor, provenance, and basic ETL
- Analyzer contract: source-specific AI analyzers that emit a common observation schema
- Fusion contract: fusion consumes observations, not raw source payloads
- Active target selection: runtime-managed resolver
- Target candidate strategy: curated registry first, live market search fallback
- Compare modes: `full_compare`, `degraded_compare`, `suppressed`
- Delivery policy: `auto-deliver`
- Canonical sink boundary: OpenClaw-native heartbeat / review loop path

## Goals

- Produce a single machine-readable runtime truth for each thesis run.
- Preserve full lineage from raw source evidence to delivered alert.
- Keep source onboarding cheap so many new trackers can be added later.
- Prevent target drift by making `active_target` explicit and runtime-owned.
- Make compare legality explicit so no downstream component silently compares the wrong market or the wrong semantic frame.
- Keep the install surface portable and auditable for OpenClaw users.

## Non-Goals For MVP

- A full portfolio ranking layer across all theses.
- A world-monitor UI.
- A database as primary truth.
- Tracker-local probability scoring.
- Delivery adapters that bypass OpenClaw and push directly to Telegram or Discord.

## System Boundaries

The system is divided into three product layers:

### 1. Per-Thesis Runtime Core

This is the MVP product. It owns:

- evidence ingestion outputs
- AI semantic analysis outputs
- fusion outputs
- `active_target`
- compare legality
- alert decisions
- OpenClaw delivery receipts

This layer is the only layer allowed to produce runtime truth.

### 2. Source Platform

This layer comes after MVP. It owns:

- tracker SDK and manifests
- analyzer contracts and source templates
- source replay and backfill helpers
- source indexing and operational tooling

It does not redefine truth. It only feeds the runtime core.

### 3. Portfolio / World Monitor Layer

This layer comes later. It owns:

- cross-thesis ranking
- opportunity discovery
- thesis fleet scheduling
- global anomaly surfacing

It consumes runtime outputs from many thesis instances. It does not rewrite per-thesis truth.

## Artifact Store Model

Primary truth is file-based. The directory model should extend the current repo convention:

```text
lobster-intel/data/
  evidence/<thesis_id>/<source_id>/...
  compiled/<thesis_id>/observations/...
  compiled/<thesis_id>/fusion/...
  compiled/<thesis_id>/digests/...
  runtime/<thesis_id>/runs/<run_id>.json
  runtime/<thesis_id>/latest.json
  runtime/<thesis_id>/compare/<run_id>.json
  delivery/<thesis_id>/alerts/<run_id>.json
  delivery/<thesis_id>/receipts/<run_id>.json
```

`SQLite` or `PGlite` may index these artifacts for search, filtering, replay, and local analytics, but index rows are always derived state. If the index is deleted, it must be rebuildable from files.

## Runtime Pipeline

The MVP runtime core consists of seven fixed stages.

### 1. Tracker

Responsibility:

- fetch source payloads
- normalize source records
- dedupe
- maintain cursor state
- attach provenance

Tracker outputs evidence artifacts and never decides:

- thesis truth
- active target
- final probability
- delivery policy

### 2. Source-Specific Analyzer

Each source family may have its own analyzer. Examples:

- Firehose analyzer
- RSS / official statement analyzer
- crawler / article analyzer
- ADS-B analyzer
- AIS analyzer
- geolocated social video analyzer

Each analyzer converts evidence into a common observation schema. This keeps tracker contracts thin while still allowing source-aware AI reasoning.

### 3. Fusion Engine

Fusion consumes observations only. It computes:

- `P_AI`
- escalation view
- feature contributions
- confidence
- freshness
- DQ status

Fusion may suppress or downweight bad observations, but must record that decision in its artifact.

### 4. Active Target Resolver

This stage chooses the single market target for the thesis run. It consumes:

- thesis registry entries
- target aliases
- candidate market records
- search fallback candidates
- semantic alignment rules

The resolver owns target identity. No downstream component may infer target identity again.

### 5. Compare Engine

This stage determines whether runtime output and market output can be legally compared. It produces:

- `full_compare`
- `degraded_compare`
- `suppressed`

### 6. Alert Decision

This stage decides whether a compare result should be sent. It evaluates:

- compare legality
- novelty
- target changes
- explanation changes
- confidence
- freshness
- DQ

### 7. Delivery Adapter

This stage sends to the canonical sink:

- OpenClaw-native heartbeat / review loop path

It writes delivery receipts with sink-visible evidence that the message crossed the boundary.

## Artifact Contracts

Every artifact must carry the following base fields:

- `schema_version`
- `artifact_id`
- `run_id`
- `thesis_id`
- `created_at_utc`
- `provenance`
- `contract_version`

### Evidence Artifact

Required fields:

- `source_id`
- `source_type`
- `external_id`
- `collected_at_utc`
- `published_at_utc`
- `content_refs`
- `checksum`
- `cursor_lineage`
- `raw_pointer`

Purpose:

- preserve the source record that analyzers reason over
- make every downstream output auditable back to original inputs

### Observation Artifact

Required fields:

- `evidence_refs`
- `entity_refs`
- `event_type`
- `stance`
- `time_window`
- `location`
- `semantic_tags`
- `source_confidence`
- `extractive_rationale`

Purpose:

- define the common semantic unit that fusion consumes
- isolate source-specific AI analysis from source-agnostic fusion logic

### Fusion Artifact

Required fields:

- `used_observation_ids`
- `suppressed_observation_ids`
- `P_AI`
- `escalation_view`
- `feature_contributions`
- `confidence`
- `freshness`
- `dq_status`

Purpose:

- preserve the computation inputs and intermediate reasoning behind runtime truth

### Runtime Snapshot

This is the only runtime truth artifact.

Required fields:

- `state`
- `active_target`
- `target_resolution_mode`
- `P_AI`
- `market_implied_probability`
- `compare_mode`
- `ngi_gap`
- `decision_basis`
- `confidence`
- `freshness`
- `dq_status`

Rule:

- digest rendering, dashboards, alerting, and delivery must read this artifact rather than recompute target identity or semantic alignment.

### Compare Artifact

Required fields:

- `runtime_target_id`
- `market_target_id`
- `semantic_alignment_status`
- `numeric_alignment_status`
- `compare_mode`
- `alignment_confidence`
- `fallback_reason_codes`
- `operator_actionable_notes`

Purpose:

- formalize the claim that the system is comparing the same target, semantic frame, and numeric direction

### Alert Decision Artifact

Required fields:

- `should_send`
- `reason_code`
- `severity`
- `novelty_basis`
- `compare_mode`
- `confidence_gate`
- `freshness_gate`
- `dq_gate`

Purpose:

- freeze the machine-readable reason the system did or did not alert

### Delivery Receipt Artifact

Required fields:

- `sink`
- `delivery_status`
- `dispatch_time_utc`
- `delivered_at_utc`
- `sink_receipt_id`
- `alert_artifact_id`
- `run_id`

Purpose:

- prove that a valid alert crossed the canonical sink boundary

## Active Target Resolver

The active target resolver is `registry-first + live-search fallback`.

### Registry-First Path

Each thesis defines a curated target registry entry containing:

- thesis identity
- known relevant markets
- aliases
- semantic frame
- numeric direction
- resolution hints

The resolver first tries to choose a target from this registry.

### Live Search Fallback

If no registry target is sufficient, the resolver may search live market candidates and rank them against the same target contract.

Rules:

- live search expands the candidate set
- live search does not become truth by itself
- fallback usage must be written into the runtime snapshot and compare artifact

Implementation note:

- the current baseline implementation resolves against curated registry data plus the currently ingested market observation set
- an external live-search expansion step is still a follow-on item rather than part of the shipped MVP baseline

### Resolver Output

The resolver output must include:

- `market_id`
- `market_slug`
- `market_question`
- `semantic_frame`
- `probability_direction`
- `resolution_mode`
- `resolver_confidence`
- `fallback_used`

## Compare Contract

The compare engine formalizes three states.

### `full_compare`

Conditions:

- target identity matches
- semantic frame matches
- numeric direction matches or is directly normalized

Effects:

- official `ngi_gap` may be computed
- alerting remains eligible

### `degraded_compare`

Conditions:

- comparison is useful but not fully proven at the highest confidence
- one or more fallback transforms were used
- search fallback may have supplied the market candidate
- semantic or numeric alignment is partially inferred but still actionable

Effects:

- `ngi_gap` may still be computed
- compare artifact must include fallback reasons and alignment confidence
- alert severity may be capped by policy if needed later, but MVP still allows auto-delivery

### `suppressed`

Conditions:

- target identity is unstable
- semantic frame is not aligned
- numeric direction cannot be normalized safely

Effects:

- runtime may still expose `P_AI`
- no official gap alert may be produced
- suppression reason must be machine-readable

Rule:

- no downstream component may bypass compare mode and invent its own compare outcome

## Alert And Delivery Contract

MVP policy is `auto-deliver`.

### Eligibility Gate

- `full_compare` is eligible
- `degraded_compare` is eligible if compare artifact explicitly allows it
- `suppressed` is not eligible

### Novelty / Significance Gate

The alert decision may send when at least one of these changes materially:

- `ngi_gap`
- active target
- explanation / reason keys
- confidence
- freshness
- DQ

### Canonical Sink

The only canonical sink for MVP is OpenClaw-native heartbeat delivery. If that boundary is crossed successfully, delivery is official. Telegram, Discord, or any later user-configured routing is downstream of the OpenClaw sink and outside the NGI runtime contract.

### Minimum Alert Payload

Every delivered payload must contain:

- `thesis_id`
- `active_target`
- `compare_mode`
- `P_AI`
- `market_implied_probability`
- `ngi_gap`
- `reason_codes`
- `contract_version`
- `run_id`
- `artifact_links`

## Failure Handling

Failures are contract states, not just exceptions.

### Ingest Failure

- source fetch failed
- source payload malformed
- cursor could not advance safely

Effect:

- no new evidence artifact for that failed input
- previous runtime truth remains intact

### Analysis Failure

- analyzer could not produce valid observations from evidence

Effect:

- evidence remains available
- fusion receives fewer observations
- confidence, freshness, or DQ may degrade

### Compare Failure

- target alignment failed
- numeric alignment failed

Effect:

- runtime may still carry `P_AI`
- compare result becomes `degraded_compare` or `suppressed`

### Delivery Failure

- alert was valid
- sink dispatch failed or is pending retry

Effect:

- delivery receipt must record the failure
- retry logic may operate on the alert artifact and receipt, not by rebuilding truth

## Testing Strategy

### 1. Artifact Schema Tests

Validate all artifact shapes and required fields.

### 2. Source Contract Tests

Use fixtures for trackers and analyzers to validate:

- normalization
- dedupe
- cursor behavior
- observation mapping

### 3. Target Alignment Tests

Use fixed fixtures to prove the system routes cases into:

- `full_compare`
- `degraded_compare`
- `suppressed`

### 4. Delivery Path Tests

Prove that OpenClaw heartbeat delivery crosses a real sink boundary and emits a receipt artifact.

### 5. Replay / Rebuild Tests

Prove that:

- indexes can be rebuilt from files
- compare can be replayed from artifacts
- audit lineage remains intact

## Verification Gates For MVP Completion

MVP is complete only when all of the following are true:

1. A thesis run produces evidence, observation, fusion, runtime, compare, alert, and receipt artifacts with a shared `run_id`.
2. `runtime/<thesis_id>/latest.json` is the only truth artifact consumed by delivery and digest paths.
3. Compare fixtures prove `full_compare`, `degraded_compare`, and `suppressed` behavior.
4. OpenClaw-native delivery creates a machine-readable receipt showing sink crossing.
5. Artifact lineage is auditable from delivered alert back to source evidence.
6. `SQLite` or `PGlite` indexes can be deleted and rebuilt without losing truth.

## MVP Summary

The MVP is not a general world-monitor platform. It is a hard runtime spine for one thesis instance that:

- ingests first-principles evidence
- analyzes it with source-specific AI analyzers
- computes `P_AI`
- resolves the active market target
- compares on the correct semantic and numeric frame
- auto-delivers through OpenClaw

That spine becomes the dependency for later source expansion and world-monitor portfolio work.
