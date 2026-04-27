# Focused review request for 姨太

## Cut
explain-contract E2E still blocking on live `latest_ngi.json` contract projection

## Why this review now
Dispatcher acceptance artifacts are already green, but the live runtime artifact still fails the active product contract. PO still cannot audit the suppression decision directly from `latest_ngi.json`, so the current upstream cut is blocked on the runtime handoff rather than the dispatcher bundle path.

## Please review exactly this
1. Do you agree the current highest-priority blocker is the live runtime artifact missing dispatcher-visible explain fields, not the dispatcher bundle writer itself?
2. What is the thinnest implementation path to project the runtime handoff as one reviewable contract on `latest_ngi.json` without duplicating dispatcher-only code paths?
3. Which field should be treated as required vs optional on the live runtime artifact for the next cut: `alert_target_id`, `target_contract_match`, `contract_version`, `e2e_run_id`, and the structured `alert_disposition` envelope?
4. Where is the safest seam to add the regression test so the suppressed live path fails closed when the active target lineage is incomplete or mismatched?

## Evidence checked
- product contract: `docs/PRODUCT_CUT_V0.md`
- blocker plan: `docs/superpowers/plans/2026-04-28-runtime-latest-ngi-contract-gap.md`
- latest merged upstream PR: `#25 fix: add latest NGI contract repair bridge`
- current local branch for follow-up cut: `codex/pr21-recut-dispatcher-receipt-guard`
- repo state at review request time: working tree clean, no open PR, branch synced with `origin/codex/pr21-recut-dispatcher-receipt-guard`

## Proposed next cut after review
Make the smallest implementation delta that causes the live `latest_ngi.json` path to emit one machine-readable explain contract for the suppressed decision, including stable `reason_code`, `should_send`, active target lineage, and any available cross-artifact ids needed for PO audit.
