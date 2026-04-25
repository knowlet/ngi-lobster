# Focused review request for 姨太 — sync path cut

## Cut
live artifact is almost certainly being written by a stale non-git workspace runtime copy, not the already-normalized repo copy under `ngi-lobster/lobster-intel`

## New evidence from this heartbeat
I traced the exact stale reason-code string in the workspace and found:

- repo copy (`ngi-lobster/lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py`)
  - `TARGET_CONTRACT_MISMATCH_REASON = "legacy_target_mismatch"`
  - alert target validation already allows same `market_id` when slug drifts
- live workspace copy (`/Users/knowlet/.openclaw/workspace/lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py`)
  - still emits `target_contract_market_slug_mismatch`
  - `active_target_contract_reason()` hard-fails when `market_target.market_slug != target_detail.market_slug`
- live artifact still matches the stale workspace behavior:
  - `shared-projects/intelligence-model/latest_ngi.json`
  - `alert_disposition.reason_code = target_contract_market_slug_mismatch`
  - `alert_explain_contract.reason_code = target_contract_market_slug_mismatch`

So the new highest-confidence explanation is no longer just “maybe stale deploy path”; it is specifically that the real writer path is still coupled to the standalone workspace copy or code cloned from it.

## Please review exactly this
1. Do you agree the smallest implementation cut is to trace and switch the real writer/runtime entrypoint onto the repo-normalized contract path, instead of patching downstream verifiers again?
2. If both copies must temporarily coexist, what is the thinnest sync mechanism to guarantee one canonical reason-code source (`legacy_target_mismatch`) and prevent slug-drift-only suppressions from reappearing?
3. Which file/entrypoint would you inspect first to prove which runtime copy generated `latest_ngi.json`?

## Why this matters now
- DQ is currently `pass`
- freshness is current (`latest market_snapshots` at `2026-04-25T04:33:19Z`)
- active-target NGI vs Polymarket divergence remains blocking (`first_principles_probability=0.1968` vs `market_yes_probability=0.65`, gap ≈ `45.32pp`)
- because divergence is live and blocking, PO needs the real artifact writer path on-contract before any claim of production-ready alerting

## Proposed next cut after review
Trace the runtime entrypoint that generated `shared-projects/intelligence-model/latest_ngi.json`, point it at the repo-normalized contract logic (or sync the stale copy in one explicit seam), then regenerate one fresh artifact proving:
- same `market_id=1517836`
- slug drift no longer yields `target_contract_market_slug_mismatch`
- live output emits `legacy_target_mismatch` only for true legacy-target mismatch, not active-target slug drift
