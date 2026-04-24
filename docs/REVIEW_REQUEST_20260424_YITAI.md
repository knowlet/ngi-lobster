# Focused review request for 姨太

## Cut
active-target divergence is visible, but dispatcher suppress reason code is off-contract

## Why this review now
Current runtime shows the live target is Polymarket market `1517836` (Trump announces end of military operations against Iran by June 30th) with market yes probability `0.625`, while `latest_ngi.json.first_principles_probability` is `0.182944`, so the divergence is `44.21pp` and clearly above the 15pp alert threshold. DQ is `pass`, OpenAlice health is `ok`, and freshness is only `0.01h`, so the highest-priority blocker is no longer data freshness.

The blocker is contract integrity on the real active target path: `latest_ngi.json.alert_disposition.reason_code` is currently `target_contract_market_slug_mismatch`, but Product Cut v0 requires the legacy ceasefire suppression code to be a stable downstream-facing `legacy_target_mismatch`. Until that contract is aligned, downstream review and delivery consumers cannot rely on one canonical machine-readable suppression reason.

## Please review exactly this
1. Do you agree the current highest-priority implementation cut is to normalize the runtime/dispatcher-visible suppression code for active-target contract mismatch to the stable product contract value `legacy_target_mismatch`?
2. What is the thinnest code path to make `latest_ngi.json`, dispatcher artifacts, and any delivery-visible log surface emit the same stable reason code without breaking the current target-id guard?
3. Which acceptance evidence is still missing after that change: same-run suppressed fixture, positive-control delivered fixture, or both?

## Evidence checked
- product contract: `docs/PRODUCT_CUT_V0.md`
- runtime state: `shared-projects/intelligence-model/latest_ngi.json`
- repo state: `main` clean, no open PR, no open issue
- DQ status: `pass`
- OpenAlice health: `ok`
- freshness: `0.01h`
- live divergence: `44.21pp` (`0.182944` vs `0.625`)
- current suppress reason: `target_contract_market_slug_mismatch`

## Proposed next cut after review
Make the smallest implementation delta that keeps the active-target mismatch silently suppressed but rewrites the downstream contract to one stable reason code (`legacy_target_mismatch`), then capture the same dispatcher path evidence bundle needed by Product Cut v0.
