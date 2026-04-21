# Focused review request for 姨太

## Cut
explain-contract E2E still blocking

## Why this review now
`projects/ngi-lobster` is already the tracked upstream repo (`knowlet/ngi-lobster`). The current blocker is no longer repo boundary. The blocker is acceptance evidence on the real dispatcher path: we still need one shared `e2e_run_id` bundle that shows both the suppressed legacy ceasefire case and the positive-control delivered case, with machine-readable delivery proof preserved on the same contract.

## Please review exactly this
1. Do you agree the current highest-priority acceptance gap is still: same real dispatcher path, same contract version, same `e2e_run_id`, one `legacy_target_mismatch` suppression, and one positive-control delivered record with machine-readable delivery proof?
2. What is the thinnest implementation path to capture that bundle without introducing mock-only or renderer-only evidence?
3. Which dispatcher-visible fields are still missing on the positive-control path today: `runtime_target_id`, `alert_target_id`, `reason_code`, `e2e_run_id`, or delivery-proof payload?

## Evidence checked
- product contract: `projects/ngi-lobster/docs/PRODUCT_CUT_V0.md`
- upstream repo: `knowlet/ngi-lobster`
- current branch: `codex/visual-evidence-backfill`
- DQ status: pass
- freshness: pending this heartbeat report from local state check
- active divergence still needs same-target audit against runtime `latest_ngi.json`

## Proposed next cut after review
Make the smallest implementation delta that emits one same-run E2E evidence bundle on the real dispatcher path, preserving `runtime_target_id`, `alert_target_id`, `reason_code`, shared `e2e_run_id`, and machine-readable delivery proof for the positive-control case.
