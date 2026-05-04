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

That shortcut runs the dispatcher path verification gate first and then the shared E2E bundle verification gate. It confirms the current blocking acceptance contract, but it does not regenerate the real-path artifacts by itself.

For the canonical same-run real-path recut, keep one lineage:

1. regenerate both runtime records first and keep the fresh suppressed and positive `run_id` values;
2. audit each `run_id` against the current runtime target before dispatcher acceptance;
3. run `run_dispatcher_acceptance.py` once with one explicit `bundle_id`;
4. verify the emitted bundle and then the live `latest_ngi.json` contract surface.

Do not treat the recut as PO-ready if the bundle mixes old and fresh `run_id` values, skips the target audit, or lacks machine-readable positive-control `delivery_proof`.

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

When the live runtime artifact is stale and PO needs one repeatable refresh entrypoint on the real workspace path, use:

```bash
npm run refresh:latest-ngi-live
```

That shortcut runs the legacy monitor from the repo-local package path and rewrites the live `shared-projects/intelligence-model/latest_ngi.json` artifact in place, so PO can refresh the active-target contract before re-checking live ops health.

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

When PO needs one fast gate for current live ops health — DQ pass/fail, market snapshot freshness, same-target NGI divergence from `latest_ngi.json`, and whether the runtime artifact itself is stale — use:

```bash
npm run check:ops-health-live
```

That shortcut runs the real workspace health verifier against the live `STATE.yaml`, `intelligence_store.sqlite`, and `latest_ngi.json` paths so PO can re-check the current operational blocker without reassembling ad hoc heartbeat commands.

Important product rule: a fresh database snapshot does **not** mean live NGI is current. If `latest_ngi_age_hours > 4`, the live runtime artifact is stale and any progress/delivery claim must remain blocking even when DQ is `pass` and snapshot freshness is green.

When implementation work changes the verifier itself, keep its focused regression gate on:

```bash
npm run test:ops-health-cut
```

## Dispatcher acceptance cut shortcut

The current P0 product cut is still the same dispatcher-path acceptance proof. From repo root, run:

```bash
npm run test:dispatcher-cut
```

That one command executes the focused dispatcher acceptance / contract test set against the local `.venv`, so PO can quickly re-check the highest-priority cut before asking for review or upstreaming.

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
- the highest-priority blocker is still one fresh same-run real dispatcher-path evidence bundle that proves the suppressed legacy control and delivered positive control under the same `contract_version` and `e2e_run_id`, with machine-readable delivery proof

## Current highest-priority cut

Until that evidence bundle exists on the real dispatcher path, project status stays `explain-contract E2E still blocking`.

PO's repeatable acceptance entrypoint is:

```bash
npm run test:p0-cut
```

That command must remain the smallest operator verification path for checking the current blocking cut before review or upstreaming. Real-path regeneration still follows the canonical recut lineage below.

For the real-path recut, PO should keep one canonical lineage and reject stale artifact mixing:

1. regenerate fresh runtime artifacts with `lobster-intel/scripts/run_thesis_runtime.py`
2. audit each fresh run with `lobster-intel/scripts/verify_runtime_target_audit.py`
3. materialize the shared dispatcher bundle with `lobster-intel/scripts/run_dispatcher_acceptance.py`
4. immediately verify the emitted bundle with `lobster-intel/scripts/verify_alert_contract_bundle.py`
5. re-check the live artifact surface with `lobster-intel/scripts/verify_latest_ngi_contract.py`
