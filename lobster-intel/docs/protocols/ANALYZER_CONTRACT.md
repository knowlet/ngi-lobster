# ANALYZER_CONTRACT

## Purpose

Analyzers transform evidence artifacts into normalized observation drafts for the runtime spine.

They do not:

- select active targets
- compute compare mode
- emit alerts
- send delivery output

Those decisions remain runtime-owned so delivery stays downstream of runtime truth.

## Draft Contract

Each analyzer returns one observation draft with:

- `event_type`
- `stance`
- `entity_refs`
- `semantic_tags`
- `extractive_rationale`
- `metadata`

The runtime spine owns artifact ids, provenance wiring, timestamps, confidence scoring, and downstream compare behavior.

## Fallback Rule

If no source-specific analyzer is registered, runtime uses the default analyzer.

The default analyzer preserves:

- `event_type=source_type`
- `stance=escalatory_signal`
- title or summary as `extractive_rationale`
- source metadata as observation metadata

That keeps new source families replayable without letting unknown sources bypass runtime-owned truth.

## Current Built-In Analyzer

- `prediction_market` maps to `event_type=market_candidate` and `stance=market_snapshot`

Prediction-market analyzers may enrich metadata like `market_id`, `market_slug`, and `market_question`, but they still do not resolve the active target contract. Registry matching and fallback target resolution remain inside the runtime spine.
