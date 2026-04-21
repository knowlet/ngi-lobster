# Plugin System

## Purpose

Plugins let other lobster agents add capabilities without directly mutating the core packages.

## Plugin contract

Each plugin should declare:
- manifest
- entrypoints
- hooks
- capabilities
- artifacts produced

## Execution pattern

A plugin should usually follow this flow:
1. ingest raw input
2. summarize or compile
3. optionally produce runtime output
4. optionally produce delivery output

## Gooaye tracker as reference

The Gooaye tracker demonstrates a minimal plugin that:
- ingests public Telegram channel updates
- produces a simple summary artifact
- returns `NO_REPLY` when no user-visible output is needed

## Future work

- plugin loader
- manifest validation
- capability enforcement
- standard plugin test harness
