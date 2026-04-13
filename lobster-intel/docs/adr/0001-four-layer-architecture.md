# ADR 0001: Adopt a four-layer intelligence architecture

## Status
Accepted

## Context

The current system grew as a mix of scripts, cron jobs, reports, monitoring logic, and knowledge artifacts. This made it easy to ship fixes quickly, but hard to maintain, audit, and extend. Several recent failures were really boundary failures:
- stale market framing remained in one script after other components moved on
- service liveness and health semantics drifted apart
- runtime truth and delivered messages were mixed together

We need a structure that supports maintainability, documentation, pluginization, and operational safety.

## Decision

Adopt a four-layer architecture:
1. Evidence Layer
2. Compiled Knowledge Layer
3. Runtime Intelligence Layer
4. Delivery Layer

These layers will be supported by package boundaries:
- `lobster-core`
- `lobster-ingest`
- `lobster-compiler`
- `lobster-runtime`
- `lobster-delivery`
- `lobster-plugins`

## Consequences

### Positive
- clearer separation of truth, interpretation, state, and messaging
- easier audits and drift detection
- better plugin boundaries
- easier documentation and onboarding for other lobster agents
- less accidental coupling between heartbeat and business logic

### Negative
- migration overhead
- temporary duplication while old scripts are being extracted
- more up-front schema and protocol work

## Non-goals

This decision does not require:
- immediate vector or semantic memory adoption
- a large UI rewrite
- replacing every existing script at once

## Follow-up

Near-term tasks:
- define `INTEL_PROTOCOL.md`
- classify current artifacts by layer
- extract shared schemas into `lobster-core`
- make Gooaye tracker the first plugin example
