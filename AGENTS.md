# AGENTS

## Project Goal

NGI Lobster exists to turn the current NGI workflow into an installable OpenClaw plugin product.

The product goal is:

- `openclaw plugins install` must be the primary install surface
- the runtime must treat NGI as live runtime truth, not a static report
- source plugins ingest and normalize evidence
- runtime computes thesis state, target resolution, compare mode, and alert decisions
- delivery stays downstream of runtime truth

## Current Product Shape

There are two active development routes and both matter:

1. **OpenClaw plugin surface**
   - files like `index.js`, `openclaw.plugin.json`, `package.json`
   - this is the user-facing install and tool surface

2. **Python runtime spine**
   - files under `lobster-intel/`
   - this is the implementation engine behind thesis runtime, artifacts, compare, and delivery receipts

Do not collapse these into a false either/or. The plugin route is the product surface; the Python runtime route is the current execution engine.

## Engineering Rules

- Prefer additive changes over rewrites unless explicitly requested.
- Keep runtime truth in artifacts under `lobster-intel/data/`.
- Do not move decision logic into delivery-only code.
- Do not let source plugins bypass runtime and send chat messages directly.
- When changing install or tooling behavior, preserve the `openclaw plugins install` direction.
- When changing runtime behavior, preserve replayability, lineage, and artifact auditability.

## Documentation Rule

High-signal entry documents should state the project goal clearly.

At minimum, keep the goal visible in:

- `README.md`
- `docs/INSTALL_OPENCLAW.md`
- `docs/PRODUCT_CUT_V0.md`
- `lobster-intel/README.md`

If a new top-level workflow or install doc is added, include the project goal or explicitly link to it.
