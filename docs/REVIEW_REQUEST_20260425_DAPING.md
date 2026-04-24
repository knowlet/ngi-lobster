# Focused review request for 大餅

## Cut
PO needs a product-level decision on the current highest-priority cut: live active-target suppression is still surfacing an off-contract reason code in the shipped artifact even though repo contract/tests already require `legacy_target_mismatch`.

## Why this review now
Product Cut v0 is already explicit:
- the active-target contract must be validated against the live runtime target,
- legacy ceasefire mismatch must stay silently suppressed,
- but downstream dispatcher-visible output must expose one stable machine-readable `reason_code=legacy_target_mismatch`,
- and the same contract fields must survive onto the real delivery path and shared E2E bundle.

Current situation is product-blocking, not cosmetic:
- repo code/tests appear normalized to `legacy_target_mismatch`
- live artifact `shared-projects/intelligence-model/latest_ngi.json` still emits `target_contract_market_slug_mismatch`
- that means PO cannot yet claim the real runtime/writer path is on-contract, even though unit/repo surfaces look close.

Current ops state at check time:
- OpenAlice health: `ok`
- DQ: blocking status not cleared in tooling output this round, but prior heartbeat state recorded `pass`
- freshness: `0.03h`
- active divergence: `40.09pp` (`first_principles_probability=0.23426124197002143` vs `market_yes_probability=0.635`)
- supporting data in live artifact:
  - logistics: `ADS-B 區域軍機活動 15 架`
  - energy: `能源/航運風險代理仍未跟上第一性升級定價（FP 76.6% vs 市場/代理 36.5%）`
  - key statement: `第一性升級機率 76.6% 高於市場/代理 36.5%`

## Please review exactly this
1. Do you agree the product status must remain `explain-contract E2E still blocking` until one fresh real-path artifact proves `legacy_target_mismatch` on the live runtime/writer path?
2. Is the next PO-acceptable cut simply: trace the exact live writer entrypoint, eliminate the stale/off-contract reason-code seam, then regenerate one fresh active-target artifact before asking for positive-control delivery evidence?
3. Do you want the implementation side to prioritize root-cause trace first, or to ship a narrower contract-normalization patch first if it can be proven on the real artifact path immediately?

## Evidence checked
- product contract: `docs/PRODUCT_CUT_V0.md`
- current implementation expectations: runtime/dispatcher tests in `lobster-intel/tests/`
- live artifact: `shared-projects/intelligence-model/latest_ngi.json`
- repo status: `main` clean before this note, no open PR, no unpushed commits

## Proposed next cut after review
Trace the exact runtime/writer entrypoint that generated the current live artifact, remove the stale reason-code path, then regenerate one fresh artifact proving:
- `alert_disposition.reason_code=legacy_target_mismatch`
- `alert_explain_contract.reason_code=legacy_target_mismatch`
- active target identity still points to the current runtime contract and does not weaken the target-id guard
