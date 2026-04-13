# lobster-core

Shared contracts and models for Lobster Intel.

## Current contents
- `lobster_core/types.py`
- `lobster_core/models.py`
- `lobster_core/__init__.py`

## Purpose

This package is the common language for the rest of the system.

Nothing in `lobster-core` should depend on:
- Telegram
- OpenClaw sessions
- UI code
- specific delivery channels

## Immediate next step

Add tests and JSON serialization helpers for the core objects.
