# Review Request — 2026-04-26 — Yitai — real-path E2E evidence recut

## Context

Product Cut v0 is still blocked on the same acceptance claim:

- one suppressed legacy fixture on the real dispatcher path,
- `reason_code=legacy_target_mismatch`,
- visible `runtime_target_id` / `alert_target_id` / `target_contract_match`,
- one positive-control delivered fixture on that same path,
- machine-readable delivery proof,
- both fixtures under the same `contract_version` and same `e2e_run_id`.

Repo/runtime contract code is already aligned to `legacy_target_mismatch`, but PO still does not have one fresh real-path artifact bundle that closes the cut.

## Why this review now

The product risk is no longer abstract contract wording. It is operator-path execution drift:

1. which live entrypoint should be treated as the canonical real-path regeneration path,
2. where that path can still silently reuse stale runtime or receipt artifacts,
3. what the thinnest implementation / operator cut is to regenerate one auditable bundle without mixing old contract lineage.

## What I want you to inspect

Please review the current repo path centered on:

- `lobster-intel/scripts/run_dispatcher_acceptance.py`
- `lobster-intel/scripts/verify_latest_ngi_contract.py`
- `lobster-intel/packages/lobster-delivery/lobster_delivery/runtime_contract.py`
- `lobster-intel/packages/lobster-delivery/lobster_delivery/dispatcher_artifacts.py`
- any doc/operator path that still makes the real-path recut ambiguous

## Focused questions

1. What is the single canonical operator path PO should require for a fresh real-path recut today: runtime regeneration first, dispatcher acceptance second, then latest-contract verification — or a different thinner sequence?
2. Where is the most likely stale-artifact reuse point that could let us claim a closed cut without a genuinely fresh same-lineage bundle?
3. If one small change is still needed, what is the smallest safe delta: guardrail in `run_dispatcher_acceptance.py`, guardrail in `verify_latest_ngi_contract.py`, or docs/operator-path tightening only?

## PO acceptance bar for your answer

Please answer with:

- recommended canonical command/order,
- exact stale-reuse risk you think is highest,
- smallest next cut you recommend,
- whether current status must remain `explain-contract E2E still blocking` after your review.
