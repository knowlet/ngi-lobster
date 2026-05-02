# NGI Lobster 專案 Roadmap & Backlog（與大餅、姨太對齊版）

日期：2026-05-02（GMT+8）

## 一、專案目標
- 目標不是補昨天的 blocker；目標是把 **v0 product path** 變成可重複、可審計、可上線的常態流程。
- 以 `docs/PRODUCT_CUT_V0.md` 為唯一產品契約，所有工作只服務該契約。
- 達到任一里程碑後才往下一階段，不以「有問題才補」為節奏。

## 二、角色分工（持續）
- **大餅（daping）**：市場/內容/產品判讀、報告與指標解讀、決策紀錄、Backlog 餵養與優先序建議。
- **姨太（yitai）**：Runtime、delivery、runtime-contract、腳本、測試、CI/驗收門檻實作。

## 三、Roadmap（4 週循環）

### Phase A｜Product Cut v0 收斂（本週到下週）
1. **同次 E2E 證據包落地（blocking）**
   - 同一 run 必須同時拿到：suppressed + delivered 的 `reason_code / runtime_target_id / alert_target_id / target_contract_match / contract_version / e2e_run_id`。
   - 產生可被 PO 一次審核的機器可讀證據。
   - **Owner：姨太**
   - **交付**：`npm run test:p0-cut` 通過（同一 `e2e_run_id`）。

2. **同 run 重現命令標準化（blocking）**
   - 明確一個「重跑同一路徑」的操作流程（含輸入、輸出、輸出路徑、失敗原因）。
   - **Owner：姨太**（撰寫）+ **大餅**（驗收確認描述完整）
   - **交付**：README/操作清單更新，含範例與失敗對應。
   - 2026-05-02 16:02+08:00：已把 canonical same-run real-path recut checklist 補到根 README、安裝文件與 reporting operator docs，明確規定 fresh suppressed/positive run ids、target audit、單一 bundle id、positive delivery proof 與 bundle/live contract verifier 順序。

3. **Delivery/Renderer 真徑驗證加固（high）**
   - 確保任何 consumer 都不能繞過 explain-contract。
   - **Owner：姨太**
   - **交付**：對應整合測試 + 無例外路徑。
   - 2026-05-02 17:03+08:00：已把 dispatcher artifact renderer 的直接寫入路徑接上 `build_alert_contract_view`，缺少 explain-contract 必填欄位（例如 shared `e2e_run_id`）時會在寫檔前 fail closed，避免 consumer 繞過 bundle verifier 才發現不合約。

### Phase B｜產品體驗固定化（第 2 週）
4. **每日/每次 run 的可讀摘要體系**
   - 讓 operator 一眼看出：最新 runtime timestamp、freshness、divergence、blocker 狀態。
   - **Owner：大餅**（內容與欄位定義）+ **姨太**（實作）
   - 2026-05-02 19:04+08:00：已讓 live progress sync payload 可選擇接入 polymarket runtime source，並在 `active_target` 區塊輸出 closed/accepting-orders/reselection/rollover-candidate 狀態，讓 operator 在同一份同步 payload 看到是否必須換 active target。

5. **Freshness + DQ 監控門檻固定化**
   - 明確把 `latest_ngi_age_hours > 4` 直接設為硬阻斷。
   - **Owner：姨太**
   - 2026-05-02 21:02+08:00：已加固 live progress sync payload 的 freshness gate，`latest_ngi_age_hours > 4` 時會在輸出 user-facing progress payload 前 fail closed，避免 stale `latest_ngi.json` 被包成可同步摘要。

6. **告警/交付分流策略對齊**
   - 分流策略（send/suppress）只依 contract 狀態，不靠臨時人工解讀。
   - **Owner：姨太**（核心）
   - 2026-05-02 20:04+08:00：已加固 live progress sync 的 positive-delivery 分流邊界，`should_send=true` 或 positive decision 只有在 `target_contract_match` 明確為 true 時才接受 delivery proof；serialized `"false"` 會被視為 contract mismatch 並 fail closed。

### Phase C｜可擴展性與回歸（第 3–4 週）
7. **tracker 插件接線規格化**
   - 任何新 tracker 以同一 artifact 流程接入，不再各自定義。
   - **Owner：姨太**（接口） + **大餅**（驗收案例）

8. **Backlog 自動盤點與審計**
   - 每週固定輸出：進行中、阻塞、待排、已關。
   - **Owner：大餅**（週報） + **大餅、姨太**（狀態更新）

## 四、Backlog（未來排程）

### P0（不解掉不往前）
- 同次證據包重放腳本仍有 stale reuse 風險。
  - 2026-05-02 13:04+08:00：已加固 `write_dispatcher_e2e_bundle` 的 alert artifact 載入邊界，若檔名要求的 run id 與 JSON 內 `run_id` 不一致會 fail closed，避免 standalone E2E bundle 重用 stale alert artifact。
  - 2026-05-02 14:03+08:00：已加固 `write_dispatcher_e2e_bundle` 的 delivery receipt 載入邊界，若檔名要求的 run id 與 receipt JSON 內 `run_id` 不一致會 fail closed，避免 delivery proof 被 stale receipt 汙染。
  - 2026-05-02 18:04+08:00：已加固 `write_dispatcher_e2e_bundle` 的 runtime run 與 compare artifact 載入邊界，若檔名要求的 run id 與 JSON 內 `run_id` 不一致會 fail closed，避免 stale runtime/compare artifact 被投影進同次 E2E bundle。
- 分歧鏈路在 live path 未出示 machine-readable delivery proof。
  - 2026-05-02 15:05+08:00：已加固 `build_live_progress_sync_payload.py` 的 positive delivery 邊界，`alert_disposition.should_send=true` 或 positive decision 沒有 `delivery_proof` 會 fail closed，且 live sync payload 會輸出 machine-readable proof。
- positive delivery 不能繞過 active-target contract match。
  - 2026-05-02 20:04+08:00：已加固 `build_live_progress_sync_payload.py`，positive delivery 必須有 true-equivalent `alert_disposition.target_contract_match` 才能進入 sync payload；`"false"`/`0`/`no`/`off` 這類 serialized false 值會阻斷輸出。
- active-target contract mismatch 與 outward reason 映射邊界。
  - 2026-05-02 12:04+08:00：已加固 `repair_latest_ngi_contract.py`，避免既有 `target_contract_match="false"` 被 Python truthiness 轉成 `True`，並以 regression test 覆蓋 outward reason mapping 仍保留 internal runtime reason。
- live progress sync 不能輸出 stale `latest_ngi.json` 摘要。
  - 2026-05-02 21:02+08:00：已加固 `build_live_progress_sync_payload.py`，當 ops-health 判定 `latest_ngi_stale=true` 時直接 fail closed，不再回傳 `sync_status=blocking` 的 user-facing payload。

### P1（下一階段）
- plugin 接線標準與測試套件擴充。
- 產品化交付文檔（安裝→run→驗收）一體化。
- 主要告警文案模板以 explain-contract 欄位為唯一真值。
- live progress sync 的 active-target rollover 欄位後續可接 Paperclip / Albert 顯示模板，避免 operator 另查 ops-health JSON。

### P2（改善與擴充）
- 進一步自動化資料源補全與 source 風險檢測。
- NGI/Polymarket 對比視覺化儀表。
- 多專案/多市場的 target contract 抽象。

## 五、每週固定節奏（防止只在遇到 blocker 才動作）
- **一週一次**：大餅 + 姨太固定同步（30 分鐘）
  - 決定本週 Top-3、更新阻塞條件。
- **日常節奏**：只更新三件事
  1. 本日進度 1~2 行
  2. 新 blocker 是否「真 blocker」（是否阻塞下一里程碑）
  3. 明日唯一預定投入的 1 個具體項目
- **每月一次**：回看 roadmap 是否偏離產品順序，必要時改版。

## 六、已知 blocker（截至最近一次 review）
- 以 `REVIEW_REQUEST_20260501_YITAI_REAL_PATH_BUNDLE.md` 為界，核心阻塞是 **real dispatcher 同 run 實證證據鏈**。
- 先解完 P0 再展開 Phase B/C，避免邊補邊漂。

## 七、版本控制
- 這份文件為本專案正式版本規劃稿，任何新增 blocker/需求先入 Backlog，再對應 milestone。
- 新 blocker 到位時，新增條目到 P0 並標明 `owner + expected evidence + deadline`，不以聊天訊息臨時塞。
