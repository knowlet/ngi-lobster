# Review request for Daping — live NGI suppression reason code contract

## Why this needs product review now

The live NGI artifact is still off-contract on the real runtime path even after target alignment was restored.
Current live facts from `shared-projects/intelligence-model/latest_ngi.json`:

- active target: Polymarket `1517836`
- market question: `Trump announces end of military operations against Iran by June 30th?`
- market yes probability: `0.645`
- P_AI: `0.16953895071542135`
- divergence: `47.55pp`
- DQ: `pass`
- freshness: latest snapshot is fresh (`2026-04-26T09:24:42.315384+00:00` in heartbeat state)

So the P0 blocker is not data health. The blocker is product-contract drift on the live suppression path.

## Current contract problem

The live writer currently emits:

- `alert_disposition.reason_code=no_novelty_within_24h`
- `alert_explain_contract.reason_code=no_novelty_within_24h`

This is important because Product Cut v0 requires a stable downstream-facing suppression contract on the real dispatcher path, not just an internally convenient runtime label.

We already know the live output must also carry the full contract envelope (`target_contract_match`, `alert_target_id`, `contract_version`, `e2e_run_id`).
What still needs explicit PO sign-off is whether `no_novelty_within_24h` is itself an allowed product reason code or just an internal runtime policy label that should be mapped before delivery.

## Focused product questions

1. Should `no_novelty_within_24h` be treated as a valid downstream-facing product `reason_code` for suppressed live NGI delivery?
2. If not, what exact stable product-facing code should the live path emit instead?
3. Should the explain contract preserve the internal runtime label separately while the outward `reason_code` stays on-contract?

## Proposed next cut after review

Once this decision is explicit, implement the thinnest live-path patch so fresh suppressed artifacts on the active target `1517836`:

- keep the full contract envelope,
- emit a PO-approved downstream `reason_code`, and
- pass `verify_latest_ngi_contract.py` on the real artifact path.
