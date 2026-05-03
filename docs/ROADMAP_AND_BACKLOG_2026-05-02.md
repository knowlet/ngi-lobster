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
   - 2026-05-02 23:03+08:00：已加固 ops-health 的 runtime-source boolean parser，`accepting_orders="unknown"` 這類 ambiguous 字串不再被 Python truthiness 當成 true，也不能在 rollover candidate ranking 裡壓過明確 open successor。
   - 2026-05-03 00:04+08:00：已收緊 ops-health rollover candidate eligibility，只有 runtime source 明確回報 `closed=false` 且 `accepting_orders=true` 的 successor 才會輸出成 machine-readable candidate；只有 ambiguous successor 時會保留 blocked 狀態但不建議切換目標。
   - 2026-05-03 01:03+08:00：已加固 ops-health active-target status guard；當 `target_detail.market_closed` 或 `market_accepting_orders` 明確存在但值為 ambiguous（例如 `"unknown"`）時會 fail closed，要求重新選 active target，不再輸出健康摘要。
   - 2026-05-03 02:03+08:00：已加固 ops-health runtime-source 輸入邊界；operator 明確傳入 polymarket runtime-source 檔案時，缺檔或非 JSON object 會直接 fail closed，不再靜默降級成「沒有 rollover evidence」。
   - 2026-05-03 03:03+08:00：已加固 ops-health runtime-source schema 邊界；明確傳入 tracker payload 時，`evidence.items` 必須是 list，不能用 malformed object 靜默變成 `rollover_candidate=null` 的健康摘要。
   - 2026-05-03 04:03+08:00：已加固 ops-health runtime-source item schema 邊界；`evidence.items` 內每個 item 與其 `metadata` 必須是 JSON object，避免 malformed tracker item 被靜默略過或以不清楚的 AttributeError 中斷。
   - 2026-05-03 05:03+08:00：已加固 ops-health latest NGI schema 邊界；`latest_ngi.market_target` 與 `target_detail` 必須是 JSON object，避免 malformed active-target payload 以 Python AttributeError 中斷。
   - 2026-05-03 06:02+08:00：已加固 ops-health latest NGI top-level schema 邊界；`latest_ngi.json` 本身必須是 JSON object，避免 malformed payload 以 `.get()` AttributeError 中斷。
   - 2026-05-03 07:03+08:00：已加固 ops-health runtime-source nested schema 邊界；tracker item 的 `metadata.source_config` 若存在就必須是 JSON object，避免 rollover candidate projection 以 `.get()` AttributeError 中斷。
   - 2026-05-03 08:04+08:00：已讓 ops-health 與 live progress sync 在 `rollover_candidate=null` 時輸出 machine-readable `rollover_candidate_blocker`，讓 active-target reselection 摘要能明確說明沒有可執行 successor 的原因。
   - 2026-05-03 09:03+08:00：已補齊 live progress sync 的 latest NGI top-level schema guard；`latest_ngi.json` 本身不是 JSON object 時會 fail closed 並輸出明確 schema error，而不是誤報缺少第一個 required key。
   - 2026-05-03 10:02+08:00：已補齊 live progress sync 的 latest NGI nested object schema guard；`market_target`、`target_detail`、`alert_disposition` 若存在但不是 JSON object，會 fail closed 並輸出明確 schema error，而不是誤報 missing 欄位。
   - 2026-05-03 11:03+08:00：已補齊 live progress sync 的 delivery proof schema guard；即使不是 positive delivery，只要 `delivery_proof` 欄位存在就必須是 JSON object，避免 malformed proof 被靜默丟掉。
   - 2026-05-03 19:04+08:00：已加固 ops-health 的 probability schema guard；`first_principles_probability` 與 `target_detail.market_yes_probability` 必須是 0..1 的 JSON number，boolean、字串或超界值會 fail closed，不再被轉型成健康摘要。
   - 2026-05-03 20:03+08:00：已加固 ops-health runtime-source rollover candidate probability schema guard；successor tracker item 若帶 `metadata.yes_probability`，該值必須是 0..1 的 JSON number，避免 malformed candidate probability 被投影給 operator。
   - 2026-05-03 21:04+08:00：已加固 ops-health runtime-source timestamp schema guard；successor tracker item 若帶 `collected_at_utc` 或 `published_at_utc`，該值必須是 ISO-8601 timestamp，避免 malformed timestamp 被投影進 operator rollover guidance。
   - 2026-05-03 22:04+08:00：已加固 ops-health latest NGI timestamp schema guard；`latest_ngi` 的 timestamp 欄位若存在就必須是 ISO-8601 timestamp，避免 malformed timestamp 以底層 parser error 中斷 operator 摘要。
   - 2026-05-03 23:03+08:00：已加固 ops-health SQLite freshness timestamp schema guard；`market_snapshots.snapshot_at_utc` 必須是 ISO-8601 timestamp，避免 malformed store freshness timestamp 以底層 parser error 中斷 operator 摘要。
   - 2026-05-04 01:03+08:00：已加固 ops-health runtime-source rollover candidate identity schema guard；successor tracker item 的 `external_id`、`title`、`url`、`metadata.market_id`、`metadata.slug` 與 `metadata.source_config.label` 若存在就必須是 non-empty string，避免 malformed identity/display 欄位被投影成 operator-facing rollover guidance。
   - 2026-05-04 02:03+08:00：已加固 ops-health runtime-source run timestamp schema guard；tracker payload 的 top-level `ran_at_utc` 若存在就必須是 ISO-8601 timestamp，避免 malformed source run timestamp 被接受進 operator 摘要。
   - 2026-05-04 03:02+08:00：已加固 ops-health latest NGI probability-mode schema guard；`target_detail.probability_mode` 與 top-level `latest_ngi.probability_mode` 若存在就必須是 non-empty string，避免 malformed mode 欄位被投影成 operator-facing 摘要。
   - 2026-05-04 04:03+08:00：已加固 ops-health latest NGI active-target identity schema guard；`market_target.market_id`、`market_target.market_name`、`target_detail.market_id` 與 `target_detail.market_question` 若存在就必須是 non-empty string，避免 malformed target identity/display 欄位被投影進 operator 摘要。
   - 2026-05-04 05:03+08:00：已補齊 ops-health 的 active-target reselection acceptance 摘要；即使 `latest_ngi_stale=true` 且當前 target 已 closed/not accepting orders，blocking JSON 仍會 machine-readable 輸出 `active_target_reselection.runtime_target_id` / `market_question` / `next_contract_action` / `rollover_candidate`，供 P0 reselect cut 驗收。
   - 2026-05-04 06:03+08:00：已把同一份 `active_target_reselection` acceptance object 投影到 live progress sync payload，讓 Paperclip / Albert 顯示模板不必從 `blocking_summary` 與 `active_target` 重新拼接 reselection evidence。

5. **Freshness + DQ 監控門檻固定化**
   - 明確把 `latest_ngi_age_hours > 4` 直接設為硬阻斷。
   - **Owner：姨太**
   - 2026-05-02 21:02+08:00：已加固 live progress sync payload 的 freshness gate，`latest_ngi_age_hours > 4` 時會在輸出 user-facing progress payload 前 fail closed，避免 stale `latest_ngi.json` 被包成可同步摘要。

6. **告警/交付分流策略對齊**
   - 分流策略（send/suppress）只依 contract 狀態，不靠臨時人工解讀。
   - **Owner：姨太**（核心）
   - 2026-05-02 20:04+08:00：已加固 live progress sync 的 positive-delivery 分流邊界，`should_send=true` 或 positive decision 只有在 `target_contract_match` 明確為 true 時才接受 delivery proof；serialized `"false"` 會被視為 contract mismatch 並 fail closed。
   - 2026-05-02 22:04+08:00：已收緊 live progress sync 的 contract-match parser，positive delivery 只接受明確 true/false 等價值；`target_contract_match="unknown"` 這類 ambiguous truthy 字串會 fail closed。
   - 2026-05-03 14:03+08:00：已收緊 live progress sync 的 positive-delivery 偵測；`should_send="true"` 這類 serialized true 值會被視為 positive delivery，必須同時通過 delivery proof 與 active-target contract match gates。
   - 2026-05-03 15:03+08:00：已修正 live progress sync delivery proof identifier fallback；當 `proof_id` 是空白但同份 proof 帶有效 `sink_message_id` 時，仍接受 `sink_message_id` 作為 machine-readable proof id，不再誤擋有效交付證明。
   - 2026-05-03 16:02+08:00：已收緊 live progress sync 的 `should_send` parser；欄位存在但不是明確 true/false 等價值（例如 `"unknown"`）時會 fail closed，不再被當成 non-positive summary 輸出。
   - 2026-05-03 17:02+08:00：已讓 live progress sync 以明確 `should_send=false` 作為 non-positive 分流依據；舊的 positive `decision` 不再覆蓋 machine-readable send flag，也不會誤要求 delivery proof。
   - 2026-05-03 18:03+08:00：已收緊 non-positive live sync delivery proof 欄位驗證；只要 payload 攜帶 `delivery_proof`，其中 `boundary`、`proof_id` 或 `sink_message_id` 若型別 malformed 就會 fail closed，不再把壞 proof 原樣同步出去。
   - 2026-05-04 00:02+08:00：已收緊 live progress sync 的 alert contract envelope；`reason_code`、`contract_version`、`e2e_run_id` 必須是 non-empty string，避免 malformed contract metadata 被投影進 operator sync payload。

### Phase C｜可擴展性與回歸（第 3–4 週）
7. **tracker 插件接線規格化**
   - 任何新 tracker 以同一 artifact 流程接入，不再各自定義。
   - **Owner：姨太**（接口） + **大餅**（驗收案例）

8. **Backlog 自動盤點與審計**
   - 每週固定輸出：進行中、阻塞、待排、已關。
   - **Owner：大餅**（週報） + **大餅、姨太**（狀態更新）

## 四、Backlog（未來排程）

### P0（不解掉不往前）
- active-target reselection + rollover candidate 已升為當前唯一 P0 blocker。
  - Owner：大餅（blocking 摘要欄位與 acceptance 定義）＋姨太（ops-health / live sync 實作與驗收）
  - Expected evidence：同一輪 real-path blocking 摘要必須 machine-readable 輸出 `runtime_target_id` / `market_question`、`next_contract_action=reselect_active_target`，以及唯一 `rollover_candidate`；若無 successor，必須輸出 `rollover_candidate=null` 與明確 `rollover_candidate_blocker`。
  - Deadline：2026-05-04 end of day（GMT+8）
  - 2026-05-04 04:48+08:00：PO 正式將此刀升為唯一 P0 next cut；在 closed target、`market_accepting_orders=false`、`latest_ngi_stale=true` 且 divergence 仍高於 15pp 的情況下，後續 heartbeat / review / upstream 都以這份 reselection acceptance evidence 是否齊備作為唯一先決條件。
  - 2026-05-04 05:03+08:00：ops-health blocking output 已新增 `active_target_reselection` acceptance object，讓 stale/closed/divergent real-path 摘要仍保留可審核的 target id、market question、reselection action 與唯一 rollover candidate。
- 同次證據包重放腳本仍有 stale reuse 風險。
  - 2026-05-02 13:04+08:00：已加固 `write_dispatcher_e2e_bundle` 的 alert artifact 載入邊界，若檔名要求的 run id 與 JSON 內 `run_id` 不一致會 fail closed，避免 standalone E2E bundle 重用 stale alert artifact。
  - 2026-05-02 14:03+08:00：已加固 `write_dispatcher_e2e_bundle` 的 delivery receipt 載入邊界，若檔名要求的 run id 與 receipt JSON 內 `run_id` 不一致會 fail closed，避免 delivery proof 被 stale receipt 汙染。
  - 2026-05-02 18:04+08:00：已加固 `write_dispatcher_e2e_bundle` 的 runtime run 與 compare artifact 載入邊界，若檔名要求的 run id 與 JSON 內 `run_id` 不一致會 fail closed，避免 stale runtime/compare artifact 被投影進同次 E2E bundle。
- 分歧鏈路在 live path 未出示 machine-readable delivery proof。
  - 2026-05-02 15:05+08:00：已加固 `build_live_progress_sync_payload.py` 的 positive delivery 邊界，`alert_disposition.should_send=true` 或 positive decision 沒有 `delivery_proof` 會 fail closed，且 live sync payload 會輸出 machine-readable proof。
- positive delivery 不能繞過 active-target contract match。
  - 2026-05-02 20:04+08:00：已加固 `build_live_progress_sync_payload.py`，positive delivery 必須有 true-equivalent `alert_disposition.target_contract_match` 才能進入 sync payload；`"false"`/`0`/`no`/`off` 這類 serialized false 值會阻斷輸出。
  - 2026-05-02 22:04+08:00：已補上 ambiguous contract-match 邊界，`"unknown"` 或其他非明確 true/false 的值不再被 Python truthiness 接受為 positive delivery contract match。
- active-target contract mismatch 與 outward reason 映射邊界。
  - 2026-05-02 12:04+08:00：已加固 `repair_latest_ngi_contract.py`，避免既有 `target_contract_match="false"` 被 Python truthiness 轉成 `True`，並以 regression test 覆蓋 outward reason mapping 仍保留 internal runtime reason。
- live progress sync 不能輸出 stale `latest_ngi.json` 摘要。
  - 2026-05-02 21:02+08:00：已加固 `build_live_progress_sync_payload.py`，當 ops-health 判定 `latest_ngi_stale=true` 時直接 fail closed，不再回傳 `sync_status=blocking` 的 user-facing payload。

### P1（下一階段）
- plugin 接線標準與測試套件擴充。
- 產品化交付文檔（安裝→run→驗收）一體化。
- 主要告警文案模板以 explain-contract 欄位為唯一真值。
- live progress sync 已輸出 dedicated `active_target_reselection` object，後續 Paperclip / Albert 顯示模板可直接接這份 machine-readable reselection evidence，避免 operator 另查 ops-health JSON。
- tracker runtime source 的 boolean 欄位若非明確 true/false，ops-health 會以 unknown 處理；後續插件接線需維持同一 parser 契約。
- rollover candidate 必須是明確 open 且 accepting-orders 的 tracker item，不能把 ambiguous successor 投影成可執行建議。
- active target 自身若回報 ambiguous closed/accepting-orders 狀態，ops-health 必須視為需要 reselection，不能只因欄位存在就當成健康目標。
- ops-health 若明確收到 runtime-source path，該 payload 必須存在且為 JSON object；缺檔、malformed top-level payload、非 list 的 `evidence.items`、非 object item、非 object `metadata`，或非 object `metadata.source_config` 不能靜默省略 rollover evidence。
- latest NGI 的 payload 必須維持 object schema；top-level、`market_target` 或 `target_detail` 不是 JSON object 時，ops-health 必須 fail closed 並回報明確 schema error。
- live progress sync 也必須沿用 same latest NGI object schema；top-level 或 nested object malformed payload 不能被 required-key fallback 誤報成缺欄位。
- live progress sync 若收到 `alert_disposition.delivery_proof`，該欄位必須是 JSON object；malformed proof 不能被靜默省略，即使該 alert 不是 positive delivery。
- active-target reselection 摘要若 `rollover_candidate=null`，必須同時提供 `rollover_candidate_blocker`，避免 operator 只看到空 candidate 而不知道是缺 runtime source、沒有 successor，或 successor 不符合明確 open/accepting-orders 條件。
- live progress sync 的 positive-delivery 偵測必須接受 explicit serialized booleans；`should_send="true"` 不能被當成 suppressed/non-positive 而繞過 delivery proof 或 contract-match gates。
- live progress sync 的 delivery proof identifier 需支援 `proof_id` 或 `sink_message_id` 任一有效值；空白 `proof_id` 不能遮蔽同份 proof 裡可審計的 `sink_message_id`。
- live progress sync 若收到 `alert_disposition.should_send`，該值必須是明確 boolean-equivalent；ambiguous send flag 不能被當成 suppressed/non-positive payload。
- live progress sync 若收到明確 `alert_disposition.should_send=false`，該 machine-readable send flag 必須優先於舊的 positive `decision`，避免 suppressed/non-positive payload 被誤判成 positive delivery。
- live progress sync 即使是 non-positive payload，只要收到 `delivery_proof`，proof 內 machine-readable 欄位也必須維持字串 schema；malformed proof field 不能被投影到 operator-facing sync payload。
- live progress sync 的 alert contract envelope 必須維持 string schema；`reason_code`、`contract_version`、`e2e_run_id` 不能用 malformed JSON 型別進入 operator-facing sync payload。
- ops-health 的 probability 欄位必須維持 JSON number schema 且落在 0..1；boolean、字串數字或超界值不能被 Python 轉型後繼續輸出健康摘要。
- ops-health runtime-source rollover candidate 的 `metadata.yes_probability` 若存在，也必須維持 0..1 JSON number schema，不能把字串、boolean 或超界值投影到 machine-readable successor 建議。
- ops-health runtime-source rollover candidate 的 `collected_at_utc` / `published_at_utc` 若存在，也必須維持 ISO-8601 timestamp schema，不能把 malformed timestamp 投影到 operator-facing rollover guidance。
- ops-health runtime-source rollover candidate 的 identity/display 欄位若存在，也必須維持 non-empty string schema，不能把 malformed target id、slug、title、url 或 label 投影到 operator-facing rollover guidance。
- ops-health runtime-source payload 的 top-level `ran_at_utc` 若存在，也必須維持 ISO-8601 timestamp schema，不能把 malformed tracker run timestamp 帶進 operator 摘要。
- ops-health latest NGI 的 `probability_mode` 若存在，也必須維持 non-empty string schema，不能把 malformed mode 欄位投影到 operator-facing 摘要。
- ops-health latest NGI 的 active-target identity/display 欄位若存在，也必須維持 non-empty string schema，不能把 malformed `market_target` / `target_detail` target id、name 或 question 投影到 operator-facing 摘要。
- ops-health blocking output 必須提供 dedicated `active_target_reselection` object，讓 stale/closed/divergent target 狀態也能直接供 heartbeat / review / upstream 驗收，不必由 operator 重新拼接零散欄位。
- ops-health 的 latest NGI timestamp 欄位若存在，也必須維持 ISO-8601 schema，不能把 malformed timestamp 洩漏成底層 parser error。
- ops-health 的 SQLite freshness timestamp `market_snapshots.snapshot_at_utc` 也必須維持 ISO-8601 schema，不能把 malformed store timestamp 洩漏成底層 parser error。

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
