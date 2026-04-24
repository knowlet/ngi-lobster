# Focused review request for 姨太

## Cut
live runtime artifact still emits off-contract suppress reason even though repo runtime/tests already normalize to `legacy_target_mismatch`

## Why this review now
Current product contract is unchanged: Product Cut v0 requires the legacy-target suppression on the active-target path to surface one stable downstream reason code, `legacy_target_mismatch`.

Repo implementation already appears aligned:
- `lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py` sets `TARGET_CONTRACT_MISMATCH_REASON = "legacy_target_mismatch"`
- `lobster-intel/tests/test_alert_target_contract.py` expects `legacy_target_mismatch`
- `lobster-intel/tests/test_runtime_spine_dispatcher_path.py` expects dispatcher-visible suppressed runtime output to carry `legacy_target_mismatch`

But the live runtime artifact is still off-contract:
- `shared-projects/intelligence-model/latest_ngi.json`
- `alert_disposition.reason_code = "target_contract_market_slug_mismatch"`
- `alert_explain_contract.reason_code = "target_contract_market_slug_mismatch"`
- active target market id still matches `1517836`, but runtime `market_target.market_slug` and `target_detail.market_slug` differ, so the live writer path is likely still using stale mismatch labeling or stale build output.

Current ops state at check time:
- OpenAlice health: `ok`
- DQ: `pass`
- freshness: `0.02h`
- active divergence: `46.95pp` (`first_principles_probability=0.18045685279187818` vs `market_yes_probability=0.65`)

## Please review exactly this
1. Given repo code/tests are already normalized, what is the thinnest explanation for live artifact output still emitting `target_contract_market_slug_mismatch`?
2. Is the likely blocker stale deploy/runtime path, duplicated logic outside `lobster_runtime.monitor`, or a writer layer that rewrites the reason code after contract validation?
3. What is the smallest next implementation cut to make the real artifact writer path emit `legacy_target_mismatch` without weakening the target-id guard?

## Evidence checked
- product contract: `docs/PRODUCT_CUT_V0.md`
- implementation: `lobster-intel/packages/lobster-runtime/lobster_runtime/monitor.py`
- contract tests: `lobster-intel/tests/test_alert_target_contract.py`
- dispatcher-path tests: `lobster-intel/tests/test_runtime_spine_dispatcher_path.py`
- live artifact: `shared-projects/intelligence-model/latest_ngi.json`
- repo state: `main` clean before this note, no open PR

## Proposed next cut after review
Trace the exact live writer/runtime entrypoint that produced the current `latest_ngi.json`, remove the stale/off-contract reason-code path, then regenerate one fresh active-target artifact proving `alert_disposition.reason_code=legacy_target_mismatch` on the real runtime path.
