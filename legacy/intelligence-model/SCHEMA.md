# Intelligence Data Schema

目標：把目前分散的情資、預測市場、第一性資料與報告產物，收進同一套可擴充 schema。

## 設計原則

1. **原始資料與衍生資料分開**
   - raw payload 原封不動保存
   - 派生欄位另外存，方便查詢與回測

2. **source-first**
   - 每一筆資料都帶 `source_type` / `source_name` / `collected_at_utc`
   - 避免之後不知道數字是從哪裡來的

3. **事件流 vs 狀態快照分開**
   - Firehose / 官方聲明 / SEC filing → event tables
   - 指數 / 油價 / Polymarket / NGI → snapshot tables

4. **主題實體化**
   - 用 `topics` 管理像 `us_iran_ceasefire`, `crude_oil_100_march`, `ai_bigtech` 這種追蹤主題
   - 各資料表都能掛到 topic

5. **報告與判斷可追溯**
   - 晨報 / 晚報 / agent 分析結果要能回溯到當時採用的資料

---

## 核心表

### 1. `topics`
追蹤主題 / 市場 / 風險題材。

### 2. `sources`
資料來源定義。
例如：Polymarket, OpenSky, Firehose, Yahoo Finance, Reuters, SEC, local-agent。

### 3. `market_snapshots`
市場主數據快照。
例如：S&P 500, Nasdaq, VIX, Brent, WTI, US10Y, NVDA, AAPL。

### 4. `prediction_market_snapshots`
預測市場快照。
例如：Polymarket 的 yes/no 機率、volume、OI、24h 變化。

### 5. `first_principles_snapshots`
第一性來源整理後快照。
例如：ADS-B count、航運異常、油輪數量、官方聲明分數。

### 6. `firehose_events`
Firehose 事件流原始落盤。
保 tag / priority / title / url / snippet / raw_json。

### 7. `official_statements`
官方發言 / 記者會 / 聲明。
可放國防部、總統、部長、企業高管等。

### 8. `ngi_runs`
NGI 計算結果。
目前已存在；保留並視作衍生層。

### 9. `report_runs`
晨報 / 晚報 / intelligence note 的產物與狀態。

### 10. `report_data_links`
報告引用了哪些資料點 / topic，方便事後審計。

---

## 典型查詢

### 查某個主題最近 24h 的全貌
- 先查 `topics`
- 再 join：
  - `prediction_market_snapshots`
  - `first_principles_snapshots`
  - `firehose_events`
  - `ngi_runs`

### 查晚報為什麼寫出某個結論
- 查 `report_runs`
- join `report_data_links`
- 回看當時引用的 snapshot / event

### 查市場與第一性是否持續背離
- `prediction_market_snapshots` vs `ngi_runs`
- 按 topic 與時間序列比對

---

## 最低落地順序

1. 先把 **NGI / Polymarket / 市場行情 / 第一性快照 / Firehose** 收進庫
2. 再讓 **晨報 / 晚報** 寫入 `report_runs`
3. 最後補 `report_data_links` 做資料血緣

---

## 備註

- SQLite 可先當 ingestion buffer / local analytics store
- 未來若要升級到 Postgres / Supabase，schema 幾乎可原樣搬過去
- 原則上不要只存最後結論，一定要存 raw payload 與 collected_at
