# Plugin System

## Purpose

Plugins let other lobster agents add capabilities without directly mutating the core packages.

## Plugin contract

Each plugin should declare:
- manifest
- entrypoints
- capabilities
- tracker contract
- artifacts produced

## Execution pattern

A plugin should usually follow this flow:
1. ingest raw input
2. summarize or compile
3. optionally produce runtime output

Delivery remains downstream of runtime truth. A source plugin can emit evidence, compiled artifacts, and runtime follow-up queue intents, but it should not send chat messages or other delivery output directly.

## Gooaye tracker as reference

The Gooaye tracker demonstrates a minimal plugin that:
- ingests public Telegram channel updates
- produces a simple summary artifact
- declares `tracker.source_family=telegram_channel`
- declares `tracker.follow_up_queues=["linked_content_queue", "image_analysis_queue"]`

That split matters:
- `capabilities` tells the host what the plugin depends on
- `tracker` tells Lobster runtime how to reason about replay, state, and downstream queue handling

## Future work

- plugin loader
- manifest validation
- capability enforcement
- standard plugin test harness
