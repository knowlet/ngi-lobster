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

Required rendering behavior:
1. show the exact active market name/question from runtime
2. compare `P_AI` against the same active market probability resolved by runtime
3. if runtime target changes, the next report must follow automatically with no delivery-side override
4. if fallback mode is used, the report must say so explicitly instead of silently reusing an old target

This prevents stale `4/30 ceasefire` framing from leaking into heartbeat, digest, or scheduled report delivery when runtime has already switched to `ACTIVE_TRUCE` style monitoring.

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
- matching `contract_version` and `e2e_run_id` across both fixtures

Behavior:
- accepts either multiple runtime payload files or one JSON file containing a list
- prints the machine-readable bundle view to stdout
- exits `0` only when the bundle contains both `suppressed` and `would_send` fixtures with matching `contract_version` and `e2e_run_id`
- exits non-zero when the bundle is incomplete, so CI or review scripts can fail closed

## One-shot dispatcher acceptance path

When the operator already knows which suppressed runtime run and which positive-control runtime run should compose the acceptance bundle, use the wrapper CLI below to execute the dispatcher path in one command:

```bash
python3 lobster-intel/scripts/run_dispatcher_acceptance.py \
  --workspace . \
  --thesis-id gooaye \
  --bundle-id bundle-20260422-acceptance \
  --suppressed-run-id legacy-20260421T000000Z \
  --positive-run-id positive-20260421T000500Z
```

Behavior:
- reads `runtime/runs/<suppressed-run-id>.json` and `runtime/runs/<positive-run-id>.json`
- preflights the shared dispatcher bundle contract before rewriting any workspace artifacts
- writes the suppressed dispatcher alert plus the positive-control dispatcher alert/receipt artifacts only after the preflight passes
- reuses the persisted positive-control receipt by default, but fails closed if `thesis_id`, `run_id`, `contract_version`, or `alert_artifact_id` are missing or no longer match the requested run
- rejects runtime contract verification when a delivery receipt omits `alert_artifact_id` or points at a different alert artifact than the run being audited
- writes one auditable dispatcher bundle under `lobster-intel/data/delivery/<thesis-id>/bundles/<bundle-id>.json`

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
