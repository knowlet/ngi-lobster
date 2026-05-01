# Reporting Operations

## Purpose

Reports turn runtime and compiled knowledge into scheduled human-facing summaries.

## Report types

- morning report
- evening report
- incident report
- ad hoc analysis report

## Inputs

Reports should combine:
- runtime snapshots
- compiled knowledge
- cited evidence where needed
- alert history

## Rules

- reports summarize, they do not redefine runtime truth
- every material claim should remain traceable
- repeated boilerplate should be minimized
- if nothing matters, the report should say little

## Live gap rendering contract

For any NGI gap report, the active market must be rendered from the runtime artifact, not from a hard-coded historical market.

Canonical fields:
- `latest_ngi.json.market_target`
- `latest_ngi.json.target_detail`
- `latest_ngi.json.first_principles_probability` as `P_AI`
- `latest_ngi.json.target_detail.market_yes_probability` as market yes probability when `probability_mode = yes_is_peace`
- `latest_ngi.json.timestamp_utc` (or equivalent runtime timestamp field) as the freshness anchor for the live artifact itself

Required rendering behavior:
1. show the exact active market name/question from runtime
2. compare `P_AI` against the same active market probability resolved by runtime
3. if runtime target changes, the next report must follow automatically with no delivery-side override
4. if fallback mode is used, the report must say so explicitly instead of silently reusing an old target
5. always render the live runtime freshness state alongside divergence: artifact timestamp, artifact age in hours, threshold, and whether the artifact is blocking because it is older than 4 hours
6. if the artifact is stale, fail closed and mark the report/delivery status as blocking instead of presenting the divergence as fresh live intent

This prevents stale `4/30 ceasefire` framing from leaking into heartbeat, digest, or scheduled report delivery when runtime has already switched to `ACTIVE_TRUCE` style monitoring.

## Paperclip / Albert sync contract

Any outward progress sync that claims live NGI status must reuse the same live contract instead of inventing a parallel summary layer.

Canonical fields:
- `latest_ngi.json.market_target`
- `latest_ngi.json.target_detail`
- `latest_ngi.json.first_principles_probability`
- `latest_ngi.json.target_detail.market_yes_probability`
- `latest_ngi.json.timestamp_utc` (or equivalent runtime timestamp field)
- signed divergence fields from the live ops-health output:
  - `divergence_pp`
  - `direction`
  - `first_principles_minus_market_pp`
- blocking verdict fields from the live ops-health output:
  - `dq_status`
  - `stale_data`
  - `latest_ngi_stale`
  - `blockers`

Required sync behavior:
1. sync the exact active target identity before any prose summary
2. always carry freshness and blocking verdict in the same payload as divergence so downstream readers cannot mistake stale output for fresh runtime intent
3. when `divergence_pp > 15`, mark the sync as blocking and preserve signed direction instead of flattening to an unsigned gap
4. when `dq_status != pass`, `stale_data = true`, or `latest_ngi_stale = true`, fail closed and mark the sync as blocked even if divergence is otherwise interesting
5. include at least one runtime-backed basis line each for logistics, energy, and key statement evidence when available
6. do not claim progress as shipped unless the sync has actually crossed the intended sink boundary or the blocker is explicitly stated

This is the delivery contract for routing the fresh `latest_ngi.json` state into Paperclip / Albert without losing target lineage, signed divergence meaning, or fail-closed freshness semantics.

## Alert explain contract

For any user-facing alert or suppression message, delivery must expose why the system sent, reviewed, or suppressed the item. Consumers must not invent their own explanation layer.

Canonical fields:
- `latest_ngi.json.alert_disposition.should_send`
- `latest_ngi.json.alert_disposition.decision`
- `latest_ngi.json.alert_disposition.reason_code`
- `latest_ngi.json.market_target`
- `latest_ngi.json.target_detail`
- `latest_ngi.json.first_principles_probability`
- `latest_ngi.json.target_detail.market_yes_probability`
- `latest_ngi.json.gap_triggered`

Required rendering behavior:
1. always render the runtime target identity first, before any prose summary
2. if `decision = suppressed`, show the exact `reason_code`; do not silently drop into generic "no update"
3. if `decision = would_send`, show the same active target plus the gap basis used by runtime
4. evidence summary must include at least one runtime-backed basis for each of: logistics proxy, energy proxy, key statement proxy, when available
5. for the current P0 cut, suppressed and delivered controls must be reviewable in the same machine-readable E2E evidence bundle, with a shared `e2e_run_id` (or equivalent bundle id) visible on both records so PO can compare them without cross-run ambiguity
6. if any required field is missing, consumer must fail closed and mark the output as `contract_incomplete` instead of guessing

Current P0 suppression reasons to preserve verbatim:
- `legacy_target_mismatch`
- `suppressed_runtime_target_missing`
- `active_target_contract_ok`
- `explanation_or_target_changed`
- `ngi_changed_major`

This is the product seam that makes active-target guardrails visible to users and reviewable by PO, instead of being buried in logs.

## P0 acceptance bundle verification

Use the bundle verifier to review the current highest-priority cut from raw runtime payloads instead of manual log reading:

```bash
cd lobster-intel
python scripts/verify_alert_contract_bundle.py path/to/suppressed.json path/to/would-send.json
```

Canonical example bundle for the current P0 cut:

```bash
cd lobster-intel
python scripts/verify_alert_contract_bundle.py examples/e2e_alert_contract_bundle.json
```

The example file shows the exact minimum machine-readable shape PO expects from one shared E2E run record:
- one `suppressed` legacy fixture with `reason_code=legacy_target_mismatch`
- one `would_send` positive-control fixture with `delivery_proof`
  - `delivery_proof.boundary` identifies the real sink boundary
  - `delivery_proof.proof_id` is the canonical receipt id surfaced to consumers
  - legacy sink-specific ids such as `sink_message_id` may still be present, but verifier output normalizes one stable `proof_id`
- matching `contract_version` and `e2e_run_id` across both fixtures

Behavior:
- accepts either multiple runtime payload files or one JSON file containing a list
- prints the machine-readable bundle view to stdout
- exits `0` only when the bundle contains both `suppressed` and `would_send` fixtures with matching `contract_version` and `e2e_run_id`
- exits non-zero when the bundle is incomplete, so CI or review scripts can fail closed

## Runtime artifact verification

Use the runtime verifier when you want to inspect one real thesis run directly from workspace artifacts instead of hand-curated payload snapshots:

```bash
./.venv/bin/python lobster-intel/scripts/verify_runtime_contract_bundle.py \
  --workspace . \
  --thesis-id gooaye \
  --run-id 20260419T123000Z
```

Use the two verifiers for different jobs:
- `verify_alert_contract_bundle.py` checks curated review fixtures or a prebuilt example bundle.
- `verify_runtime_contract_bundle.py` reconstructs the contract view from `runtime/runs`, `runtime/compare`, `delivery/alerts`, and `delivery/receipts`.

The runtime-backed verifier prints one fail-closed machine-readable view and exits non-zero when any required runtime, compare, alert, or receipt field is missing.

When PO needs to confirm a reviewed run still points at the same active target as the current runtime contract, run the target audit against `runtime/<thesis-id>/latest.json`:

```bash
./.venv/bin/python lobster-intel/scripts/verify_runtime_target_audit.py \
  --workspace . \
  --thesis-id gooaye \
  --run-id 20260419T123000Z
```

Behavior:
- reads `runtime/<thesis-id>/latest.json` as the current source of truth for the active target contract
- compares that latest active target against `runtime/runs/<run-id>.json` and `runtime/compare/<run-id>.json`
- fails closed when the audited run no longer points at the same runtime target id as the latest contract
- allows suppressed legacy fixtures to keep a divergent `market_target_id`, but still requires `compare.runtime_target_id` to match the latest active target
- also requires positive-control runs to keep `market_target_id` aligned with the latest active target

Before running the runtime verifier or dispatcher bundle builder, emit the real dispatcher delivery artifacts from the runtime payload:

```bash
./.venv/bin/python lobster-intel/scripts/write_dispatcher_artifact.py \
  --workspace . \
  --thesis-id gooaye \
  --runtime-file lobster-intel/data/runtime/gooaye/runs/positive-20260421T000500Z.json \
  --sink openclaw_heartbeat \
  --delivery-status delivered \
  --proof-boundary openclaw_heartbeat \
  --proof-id heartbeat:positive-20260421T000500Z
```

For suppressed runs, omit the receipt flags and the writer will emit only `alerts/<run-id>.json`.
When the input file is a real `runtime/runs/<run-id>.json` artifact from `runtime_spine`, the writer reconstructs dispatcher-visible `reason_code`, target identity, and contract fields from the workspace's existing `runtime/compare/<run-id>.json` and `delivery/alerts/<run-id>.json` artifacts before it writes the dispatcher-shaped alert record.

## Dispatcher E2E bundle artifact

Use the dispatcher bundle builder when you want one auditable artifact that groups the suppressed legacy control and the positive-control delivered fixture under the same shared bundle id:

```bash
./.venv/bin/python lobster-intel/scripts/build_dispatcher_e2e_bundle.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260421-01 \
  --run-id legacy-20260421T000000Z \
  --run-id positive-20260421T000500Z
```

Behavior:
- reads machine-readable dispatcher payloads from `lobster-intel/data/delivery/<thesis-id>/alerts/<run-id>.json`
- if those alert artifacts came straight from `runtime_spine`, it also reconstructs the missing contract fields from `runtime/runs`, `runtime/compare`, and `delivery/receipts`, then stamps the shared `--bundle-id` onto the synthesized contract view
- if those alert artifacts already came from `write_dispatcher_artifact.py` but still lack `alert_disposition.e2e_run_id`, it stamps the operator-provided `--bundle-id` onto the dispatcher payload before verifying the shared bundle contract
- fails closed if the payload set does not reconstruct one valid suppressed + would-send contract bundle
- writes one auditable bundle artifact to `lobster-intel/data/delivery/<thesis-id>/bundles/<bundle-id>.json`
- requires the reconstructed shared `e2e_run_id` to exactly match `--bundle-id`

## One-shot dispatcher acceptance path

When the operator already knows which suppressed runtime run and which positive-control runtime run should compose the acceptance bundle, use the wrapper CLI below to execute the entire dispatcher path in one command:

```bash
./.venv/bin/python lobster-intel/scripts/run_dispatcher_acceptance.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260421-operator \
  --suppressed-run-id legacy-20260421T000000Z \
  --positive-run-id positive-20260421T000500Z \
  --sink openclaw_heartbeat \
  --delivery-status delivered \
  --proof-boundary openclaw_heartbeat \
  --proof-id heartbeat:positive-20260421T000500Z
```

Behavior:
- reads `runtime/runs/<suppressed-run-id>.json` and `runtime/runs/<positive-run-id>.json`
- preflights the shared dispatcher bundle contract before rewriting any workspace artifacts
- writes the suppressed dispatcher alert plus the positive-control dispatcher alert/receipt artifacts only after the preflight passes
- reuses the persisted positive-control receipt by default, but fails closed if `thesis_id`, `run_id`, or `contract_version` are missing or no longer match the requested run
- writes one auditable dispatcher bundle under `lobster-intel/data/delivery/<thesis-id>/bundles/<bundle-id>.json`
- prints one machine-readable JSON summary covering the suppressed artifact write, positive artifact write, and final bundle path

## Recommended pipeline

1. gather runtime state
2. gather compiled summaries
3. pull supporting evidence only where needed
4. render concise narrative
5. deliver through the delivery layer

## Output quality

A report should answer:
- what changed?
- why does it matter?
- what evidence supports it?
- what should be watched next?
