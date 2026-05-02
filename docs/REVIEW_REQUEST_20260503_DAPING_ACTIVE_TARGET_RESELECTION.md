# REVIEW REQUEST｜2026-05-03｜大餅｜active-target reselection cut

## 背景
- canonical repo：`projects/ngi-lobster`
- current branch：`codex/pr29-clean-runtime-cut`
- latest synced commit：`b46ca0a` (`fix: validate runtime source config object`)
- live ops 目前仍 blocked：
  - `latest_ngi_stale=true`（最新 NGI 約 15h 舊）
  - active target `market_id=1517836` 已 `market_closed=true`
  - `market_accepting_orders=false`
  - `next_contract_action=reselect_active_target`
  - `rollover_candidate=null`
  - NGI / Polymarket divergence = `84.5096pp`

## 這次想請你只 review 一件事
請判斷 **「active-target reselection + rollover_candidate」是否應升為目前唯一 P0 next cut**，並回答下面 3 個問題。

1. 這刀是否應被視為目前唯一 P0 blocker？
2. 若 Albert / operator 只看一份 blocking 摘要，最少一定要看到哪 3 個欄位？
3. 如果今天只能再切一刀，最推薦的 acceptance evidence 是什麼？

## 我目前的 PO 預設答案（供你挑戰）
- 是，應升為唯一 P0，因為現在不是 schema guard 不夠，而是 active target 合約已失效但沒有可執行 successor。
- blocking 摘要最低欄位應包含：
  1. `runtime_target_id` / `market_question`
  2. `reselection_required` / `next_contract_action`
  3. `rollover_candidate`（若無則明確 `null + why`）
- acceptance evidence 最小包：同一輪 real-path 產出一份 machine-readable summary，對 closed target 明確給出 `reselection_required=true`，且當 tracker 有明確 open successor 時必須輸出唯一可執行 candidate；若沒有，則必須 fail closed 並保留 blocker 原因。
