# NGI Lobster

A repo for rebuilding the NGI / Lobster runtime into a product-grade path with tracked contracts, replayable artifacts, and upstreamable acceptance cuts.

## Quick start

Create the local venv and install the editable packages:

```bash
python3 -m venv .venv
./.venv/bin/pip install -e lobster-intel/packages/lobster-core \
  -e lobster-intel/packages/lobster-delivery \
  -e lobster-intel/packages/lobster-ingest \
  -e lobster-intel/packages/lobster-plugins \
  -e lobster-intel/packages/lobster-runtime
```

Run the existing dispatcher acceptance cut:

```bash
npm run test:dispatcher-cut
```

That command keeps the delivery contract, runtime spine, and dispatcher receipt path on one repeatable gate before merge.

## Repo layout

- `lobster-intel/packages/lobster-core`: shared typing and base contracts
- `lobster-intel/packages/lobster-delivery`: delivery contract bundle helpers
- `lobster-intel/packages/lobster-ingest`: ingest-side helpers and models
- `lobster-intel/packages/lobster-plugins`: plugin contract and loader
- `lobster-intel/packages/lobster-runtime`: runtime dispatch helpers
- `lobster-intel/scripts`: repo-level acceptance and verification scripts
- `lobster-intel/tests`: focused contract and cut tests

## Current acceptance cuts

The repo keeps product slices in small repeatable cuts.

When PO needs the dispatcher + delivery contract acceptance slice, use:

```bash
npm run test:dispatcher-cut
```

When PO needs the full current P0 explain-contract acceptance path on one operator entrypoint, use:

```bash
npm run test:p0-cut
```

That shortcut runs the dispatcher path gate first and then the shared E2E bundle gate, so PO can validate the suppressed legacy control and delivered positive control without manually reassembling the cut.

When PO needs one fast gate for the `latest_ngi.json` runtime contract, use:

```bash
npm run test:latest-ngi-cut
```

That shortcut verifies the current product contract for:

- required top-level fields
- required market target detail payload
- explainer visibility for the first-principles vs market comparison
- target alignment between the internal contract and the market detail payload
- a signed divergence field and direction that downstream ops can read directly

When the live runtime artifact is still off-contract but PO needs one repeatable repair step on the real workspace path, use:

```bash
npm run repair:latest-ngi-contract
```

That shortcut rewrites the default live `shared-projects/intelligence-model/latest_ngi.json` path in place so suppressed active-target artifacts regain the dispatcher-visible contract envelope (`alert_target_id`, `target_contract_match`, `contract_version`, `e2e_run_id`) before re-running the runtime contract gate.

When PO needs one fast gate for the dispatcher evidence bundle contract, use:

```bash
npm run test:e2e-bundle-cut
```

That shortcut keeps the real dispatcher-path evidence bundle on one repeatable acceptance command before review or merge.

When PO needs one fast gate for current live ops health — DQ pass/fail, market snapshot freshness, and same-target NGI divergence from `latest_ngi.json` — use:

```bash
npm run test:ops-health-cut
```

That shortcut keeps the current operational blocker on one repeatable local validation path instead of reassembling ad hoc checks each heartbeat.

## Current state

The repo already contains:

- a minimal plugin contract
- a plugin loader
- a run-once runtime path
- a delivery gate
- a first ingest plugin example (`gooaye-tracker`)
- legacy NGI scripts kept as migration references

## Current gaps

- Firehose local `events.jsonl` normalization now writes replayable source-run artifacts, but signal filtering still needs work
- live NGI cron still needs to be rebuilt as a product-grade path
- tracked git history, remote sync, and PR flow are still split from this writable workspace
