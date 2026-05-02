# Focused review request for 姨太 — signed divergence ops-health cut

## Cut
`b2623aa` `Add ops-health signed divergence reporting`

## Why this review now
目前 live NGI 最大 blocker 不是資料新鮮度，而是 active target 上的 NGI vs Polymarket 分歧持續遠高於 15pp，PO 需要一個足夠薄、可 upstream 的 machine-readable health seam，讓後續任何 delivery / review 都先對齊「現在到底是升級還是降溫、差多少、是否仍 blocking」。

這一刀已把 `verify_runtime_ops_health.py` 從只有固定 gap，推進到直接產出 signed divergence：
- `first_principles_minus_market_pp`
- `direction`
- `blockers`

用現在 live artifact 來看，signed divergence 已可直接表達「第一性明顯低於市場和平機率」這個 blocking 現況，而不是只剩一個抽象的絕對值。

## Please review exactly this
1. `first_principles_minus_market_pp` + `direction` 是否已是目前最薄、足夠穩定的 product-facing ops-health contract？
2. `direction=first_principles_below_market` 這種命名，是否足以讓後續 delivery / Paperclip / review 直接消費，而不需要再做第二層翻譯？
3. 若這層 contract 你認可，下一刀應優先是：
   - 把 signed divergence 直接帶進對外 progress / Paperclip 同步，還是
   - 先補一個 fail-closed gate，要求 live report 缺少 `direction` 時直接視為不合格？

## Evidence checked
- branch: `main`
- HEAD: `b2623aa`
- repo state when request prepared: clean and synced with `origin/main`
- live blocker facts from current heartbeat state:
  - active target: Polymarket `1517836`
  - P_AI: `0.11563298545602181`
  - market yes probability: `0.54`
  - divergence: `42.44pp`
  - signed divergence: `-42.44pp`
  - direction: `first_principles_below_market`
  - DQ: `pass`
  - freshness: `0.04h`

## Proposed next cut after review
若你認可這層 contract，下一刀就不要再擴 scope，只補最薄的 fail-closed enforcement / downstream projection，確保 signed divergence 變成所有 live progress 判讀的單一契約來源。
