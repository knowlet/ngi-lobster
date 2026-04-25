# Review request for Yitai — live NGI contract drift moved to `no_novelty_within_24h`

## Why this needs review now

The highest-priority blocker is no longer the older stale `target_contract_market_slug_mismatch` output.
The real live artifact now fails for a different reason on the actual runtime path:

- live artifact: `shared-projects/intelligence-model/latest_ngi.json`
- current active target: Polymarket `1517836`
- market yes probability: `0.645`
- P_AI: `0.17711066522611518`
- divergence: `46.79pp`
- DQ: `pass`
- freshness: `0.07h`
- OpenAlice health: `ok`

So freshness/DQ are not the blocker. The blocker is still contract integrity on the live writer path.

## Current live failure

Running:

```bash
python3 lobster-intel/scripts/verify_latest_ngi_contract.py \
  /Users/knowlet/.openclaw/workspace/shared-projects/intelligence-model/latest_ngi.json
```

returns `contract_violation` with:

- `reason_code_off_contract:no_novelty_within_24h`
- `explain_reason_code_off_contract:no_novelty_within_24h`
- missing contract fields in the alert contract view:
  - `target_contract_match`
  - `alert_target_id`
  - `contract_version`
  - `e2e_run_id`
- probable blocker still points to workspace/runtime drift:
  - `probable_blocker:standalone_workspace_runtime_copy_stale`

## Why this matters

Product Cut v0 requires dispatcher-visible structured disposition on the real path, with stable contract fields.
Even if `should_send=false` is correct from a novelty policy perspective, the current live output is still off-contract because downstream consumers cannot audit:

1. which target contract actually fired,
2. whether runtime and alert target matched,
3. which contract version emitted the decision,
4. whether the suppression belongs to a shared E2E run record.

So this is still a P0 delivery blocker.

## Focused review questions

1. Do you agree the thinnest implementation cut is to patch the real live writer/runtime entrypoint so suppressed `no_novelty_within_24h` outputs still emit the same required contract envelope fields (`target_contract_match`, `alert_target_id`, `contract_version`, `e2e_run_id`) instead of only patching verifier expectations?
2. Is `no_novelty_within_24h` intended to be a valid downstream-facing `reason_code`, or should the live path map it onto one of the existing product-contract reason codes before writing `latest_ngi.json`?
3. Where is the exact runtime seam that currently strips or never populates those four fields on the real artifact path?

## Requested next cut

Trace the exact live writer path that generated the current `latest_ngi.json`, then make the smallest implementation change that proves one fresh runtime artifact where:

- the output stays on the active target `1517836`,
- suppressed outcomes still carry the full contract envelope,
- the downstream-facing `reason_code` is explicitly on-contract,
- verifier status becomes `ok` for that real artifact path, not just a fixture.
