# ngi-lobster

A cleaned private repo for the current NGI + Lobster Intel productization effort.

## Included
- `lobster-intel/`: plugin-oriented intelligence platform scaffold
- `legacy/intelligence-model/`: current NGI workflow code and reference artifacts being migrated into the plugin/runtime architecture

## Excluded on purpose
- local databases
- logs
- venvs
- secrets / tokens
- personal memory files
- runtime state dumps

## Current direction
The goal is to turn the NGI workflow into an installable, open-source-friendly plugin system for OpenClaw-style agents.
