# 2026-04-28 Runtime `latest_ngi.json` contract gap

**Status:** Open
**Priority:** P0
**Cut:** explain-contract E2E still blocking

## Why this exists

Current heartbeat evidence shows the live runtime artifact is still failing the active product contract even though dispatcher bundle plumbing already exists elsewhere in the repo.

Observed contract gap from the latest workspace heartbeat state:

- `latest_ngi.status = contract_violation`
- `reason_code = no_novelty_within_24h`
- missing dispatcher-visible contract fields:
  - `target_contract_match`
  - `alert_target_id`
  - `contract_version`
  - `e2e_run_id`
- runtime target identity is also not projected back as a complete reviewable disposition on the live artifact

## Product consequence

PO still cannot audit the live NGI suppression/delivery decision from the runtime artifact alone. That keeps the current cut blocked because the product contract requires dispatcher-visible explain fields on the same active target lineage.

## Thin next cut

Make the smallest implementation delta that causes the live `latest_ngi.json` path to project the same machine-readable contract fields already enforced on dispatcher acceptance artifacts:

1. preserve the active runtime target lineage,
2. emit a structured disposition with `should_send` plus stable `reason_code`,
3. include `alert_target_id`, `target_contract_match`, `contract_version`, and `e2e_run_id` when available,
4. fail closed when the active target contract is missing or mismatched.

## Acceptance for this cut

- one focused implementation lands against the live runtime path,
- one regression test proves the runtime artifact exposes the required contract fields for a suppressed decision,
- docs/review can point to one concrete live-artifact contract instead of inferring from legacy prose.
