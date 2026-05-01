# Review Request — 2026-05-01 — Yitai — same-run real-path bundle cut

## Context

Current live status is healthier on freshness but still not product-complete:

- `dq_status=pass`
- database freshness is within 4h
- `latest_ngi.json` freshness is within 4h
- active target is still market `1517836`
- live outward reason is now `active_target_contract_ok` on the active-target suppressed path
- NGI / Polymarket divergence is still blocking at `41.09pp`

That means runtime freshness is no longer the main product blocker. The highest-priority blocker remains Product Cut v0 acceptance evidence on the real dispatcher path.

## Product blocker to close

PO still does **not** have one fresh machine-auditable evidence bundle that proves, on the same real dispatcher path and same shared `e2e_run_id`:

1. suppressed legacy control,
2. `reason_code=legacy_target_mismatch`,
3. visible `runtime_target_id` / `alert_target_id` / `target_contract_match`,
4. positive-control delivered record,
5. machine-readable delivery proof,
6. same `contract_version` and same `e2e_run_id` across both records.

## Why this review now

The repo is clean and synced to `origin/main`, but product upstreaming is still blocked because PO lacks one canonical, low-ambiguity operator cut for regenerating that same-run bundle without stale artifact reuse.

## What I want you to inspect

Please review the current path centered on:

- `lobster-intel/scripts/run_dispatcher_acceptance.py`
- `lobster-intel/scripts/verify_latest_ngi_contract.py`
- `lobster-intel/scripts/build_live_progress_sync_payload.py`
- `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`
- `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`

## Focused questions

1. What is the single canonical operator sequence PO should require today to generate one fresh same-run real-path bundle?
2. Where is the highest-risk stale-artifact reuse point that could fake a closed cut?
3. Is one small implementation guard still missing, or is the remaining gap now purely operator-path discipline?
4. After your review, should project status still remain `explain-contract E2E still blocking`?

## PO acceptance bar for your answer

Please answer with:

- one exact recommended command/order,
- one exact stale-reuse risk,
- one smallest next cut recommendation,
- explicit yes/no on whether current status is still blocking.
