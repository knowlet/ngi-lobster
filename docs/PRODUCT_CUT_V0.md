# Product Cut v0

## Product principle

NGI Lobster must be:

- **usable by default**
- **extensible by design**

## Default workflow (must work after install)

After plugin install, the default system path should be:

```text
scheduled ingest -> normalized evidence -> local artifact store -> readable markdown digest
```

### Required default behavior

1. plugin runs on a declared schedule
2. source data is normalized into evidence artifacts
3. evidence is written to local storage
4. a simple markdown digest is generated automatically
5. no chat delivery is required for the workflow to be considered usable

### Success condition

A fresh install should let a user see:

- evidence files being created
- runtime state being updated
- a readable digest being produced

without needing custom fusion logic, custom thresholds, or custom delivery setup.

## Runtime target contract for live gap tracking

For any live NGI gap view, the product contract is the runtime artifact itself, not a fixed historical market.

1. `latest_ngi.json.market_target` and `latest_ngi.json.target_detail` are the sole source of truth for the active comparison target.
2. Any digest, alert, or dashboard must compare `P_AI` against the exact same active market resolved by runtime state.
3. When runtime state changes, the comparison market may change with it, and downstream surfaces must follow automatically.
4. Fallback targets may exist for resilience, but they cannot replace the active target in user-facing gap reporting unless runtime explicitly marks fallback mode.
5. Alert gating must validate against the current runtime active target contract, not merely an internally self-consistent payload. A stale but self-consistent legacy target is still a product failure and must be silently suppressed with a machine-readable reason.
6. The suppression must be surfaced on the same dispatcher path as a structured disposition, with `should_send=false` and a stable `reason_code` that downstream delivery, logs, and review tooling can consume. For the legacy ceasefire mismatch case, the required code is `legacy_target_mismatch`.
7. That structured disposition is not complete unless it also carries the runtime target identity used for the gate, at minimum `market_target.market_id` or `market_target.market_slug`, plus the human-readable market name/question, so PO can audit which contract actually fired.
8. The dispatcher log for both `would_send` and `suppressed` outcomes must preserve the same `reason_code` and target identity fields verbatim. A silent drop or generic "no update" message does not satisfy the product cut.
9. The next acceptance cut is ordered, not vague: first prove gate-hit evidence on the real delivery path, then prove positive-control delivery on that same contract. Delivery/renderer code is only allowed to read and render contract fields, never re-infer target, state, or evidence from legacy prose.
10. The canonical acceptance set remains exactly two fixtures on the real delivery path, both carrying dispatcher-visible `runtime_target_id`, `alert_target_id`, and a boolean-equivalent match result. Those two fixtures must be captured under the same contract version and the same E2E run record, so PO can compare suppress/pass outcomes without cross-run ambiguity.
11. That “same E2E run record” requirement is not satisfied by timestamps alone. The evidence bundle must expose a stable shared identifier, at minimum `e2e_run_id` or an equivalent machine-readable bundle id, on both the suppressed and delivered fixture records.
12. The legacy ceasefire fixture must be suppressed with `reason_code=legacy_target_mismatch`, with target identity visible in dispatcher output/logs.
13. The current June 30 fixture must expose the same gate-hit evidence and then be actually delivered on that same path as the positive control, proving the active-target path is not accidentally blocked.
14. Positive-control delivery is not valid if it only exists inside mocks, unit-test doubles, or local log replays. The E2E evidence bundle must include machine-readable proof that the delivered fixture crossed the real dispatcher or delivery network boundary, or an explicitly declared external sink boundary used by production wiring.
15. `runtime_target_id` in dispatcher-visible output must come directly from the runtime active target contract (`latest_ngi.json.market_target` / `target_detail` lineage), not merely from a self-consistent alert payload.
16. Renderer-only or markdown-only smoke does not close this cut. The cut closes only when consumer or dispatcher output on the real delivery path shows the exact contract fields for both fixtures, so PO can audit the gate decision without reading source code.
17. Internal runtime policy labels are not automatically valid downstream product `reason_code`s. In particular, `no_novelty_within_24h` may exist inside runtime gating or explain/debug traces, but live delivery surfaces must map it onto an approved dispatcher-facing contract code before writing `latest_ngi.json`, and that outward record must still preserve `target_contract_match`, `alert_target_id`, `contract_version`, and `e2e_run_id`.
18. Until step 16 is proven, `positive-control delivered` is not a valid project status. The only valid status is `explain-contract E2E still blocking`, even if background generation, renderer output, or manual replay already look correct.

### Current DoD for the highest-priority cut

The current cut is complete only when all six statements are true in the same E2E run record on the same delivery path:

1. legacy ceasefire fixture is suppressed,
2. suppression shows `reason_code=legacy_target_mismatch`,
3. dispatcher-visible output preserves `runtime_target_id` and `alert_target_id`, and `runtime_target_id` is sourced from the runtime active target contract,
4. current June 30 fixture keeps the same explain fields visible and is actually delivered on that same path,
5. the delivered case includes machine-readable proof that it crossed the real dispatcher or delivery network boundary, not just a mock, test double, or local replay log,
6. both suppress and delivered cases are recorded under the same contract version and same E2E evidence bundle, with a shared `e2e_run_id` (or equivalent machine-readable bundle id) visible on both records.

This keeps `ACTIVE_TRUCE` style monitoring aligned with the live product question and prevents stale 4/30 ceasefire framing from leaking into delivery.

## Extension seam (must stay out of core v0)

These stay outside the default product cut:

1. **Fusion / synthesis**
   - cross-source reasoning
   - LLM-based signal fusion
   - advanced NGI filtering

2. **State / alerts**
   - custom thresholds
   - anomaly definitions
   - black swan logic

3. **Active delivery**
   - Telegram / Discord / chat push
   - channel formatting
   - notification policy

## Immediate implementation implication

Next build target is not “more features”.
It is one complete default path:

```text
gooaye-tracker -> evidence -> compiled markdown digest -> runtime snapshot
```

Once this path is solid, other trackers should plug into the same artifact flow.

