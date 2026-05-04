# 這週開發沖刺（2026-05-04 ~ 2026-05-10）

## 目標（段落化里程碑）
將專案從「討論/修補」進入「可重複驗收」段落：
1. 收斂 P0 合約驗收（同 run 閉環能力）
2. 完成上線前測試（staging / live-health dry run）
3. 固定成每次可重現的交付流程

## Owner 分工
- **大餅（daping）**：
  - 每日更新進度摘要與阻塞判定
  - 每晚確認是否需升級/下調風險優先順序
- **姨太（yitai）**：
  - 保障同 run 驗收命令與輸出結果可重複
  - 維運/健康檢查（DQ/freshness/divergence）流程自動化

## 這週可交付（Done Definition）
- [ ] `npm run test:p0-cut`（repo-level）：兩階段截測（dispatcher + bundle）全部綠
- [ ] `npm run test:latest-ngi-cut`：latest_ngi runtime 契約 100% 綠
- [ ] `npm run check:ops-health-live`：輸出可讀健康快照 + 阻塞原因明確
- [ ] 撰寫/更新「同 run 重現命令」與「上線測試步驟」到專案文檔

## 本週已做（已完成）
- 已執行 `npm run test:p0-cut`，通過：`28 + 11` 件測試
- 已執行 `npm run test:latest-ngi-cut`，通過：`6` 件測試
- 已執行 `npm run check:ops-health-live`：
  - 第一次：`latest_ngi_age_hours=42.80`（過舊）阻塞
  - 已補執行 `npm run refresh:latest-ngi-live`
  - 第二次：`latest_ngi_age_hours≈0`，且 `dq_status=pass`
  - 仍阻塞原因：`market_closed=true`、`market_accepting_orders=false`、`divergence_pp>15`

## 本週上線測試結論
- **代碼面：PASS（可進行上線流程）**
- **環境/市場面：BLOCK（市場狀態與 divergence）**
- **建議**：
  - 本週完成「開發段落」
  - 將上線標記為「待市場狀態放行」，暫不視為產品發佈完成
  - 先在內部維持預發行可驗收狀態，待阻塞條件解除後直接切換為正式上線
