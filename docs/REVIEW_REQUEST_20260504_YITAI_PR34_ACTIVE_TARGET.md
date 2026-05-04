# Focused review request for 姨太 — PR34 active-target reselection cut

## Cut
PR34 (`codex/pr29-clean-runtime-cut` → `main`) has already synced the runtime cut with `main`, but live ops-health still fails closed because the active Polymarket target is closed and no successor market is available.

## Why this review now
Current product state is no longer blocked by freshness or DQ:
- DQ: `pass`
- OpenAlice health: `ok`
- freshness: `0.03h`

The P0 blocker is the live active-target contract itself:
- current market is closed: `market_closed=true`
- market is not accepting orders: `market_accepting_orders=false`
- live path requires reselection: `reselection_required=true`
- next action is explicit: `next_contract_action=reselect_active_target`
- current blocker remains: `rollover_candidate_blocker=no_successor_market`
- divergence is still extreme: `89.41pp`

So before PR34 can be treated as shippable product progress, I need implementation review on whether the branch now exposes the right fail-closed evidence and the thinnest next cut for active-target reselection.

## Please review exactly this
1. Do you agree PR34 now contains the minimum correct fail-closed behavior for a closed active market, rather than silently letting the closed contract continue as user-facing compare state?
2. Is the next thinnest implementation cut to add/confirm one deterministic successor-selection path once a valid open market exists, while preserving the current fail-closed gate when none exists?
3. Is any acceptance evidence still missing on this branch besides one fresh live run that proves reselection can move from `no_successor_market` to a concrete open candidate?

## Evidence checked
- PR: `https://github.com/knowlet/ngi-lobster/pull/34`
- branch head: `fc3459c`
- branch: `codex/pr29-clean-runtime-cut`
- live blocker summary from heartbeat state:
  - `market_closed=true`
  - `market_accepting_orders=false`
  - `reselection_required=true`
  - `next_contract_action=reselect_active_target`
  - `rollover_candidate_blocker=no_successor_market`

## Proposed next cut after review
Keep PR34 focused on fail-closed correctness, then land one narrow follow-up that only handles actionable successor reselection when a valid open Polymarket market is discoverable.
