# NGI Signal Map Prototype v0

目的：把「我們要找的資訊落差訊號」和「實際能接入的資料來源」拆開，避免系統只會收資料、不會找 alpha。

## Layer A: Signal Thesis Buckets

### 1. 區域微觀消費與活動
- 核心問題：政經樞紐周邊是否出現異常加班、聚集、外送、住宿、叫車壓力。
- 為何有 alpha：危機前夕的集體加班與臨時動員，很難完全隱藏。

### 2. 實體後勤與異常位移
- 核心問題：軍機、船運、港口、補給、政府高層位移是否出現不尋常節奏。
- 為何有 alpha：人和物資的移動成本高，會在官方說法之前留下痕跡。

### 3. 枯燥採購與招募激增
- 核心問題：是否出現急單採購、特定設備/藥品/通訊需求暴增，或異常招募裁撤。
- 為何有 alpha：預算與人力調動反映真實戰略方向，但通常沒人看。

### 4. 數位基礎設施暗流
- 核心問題：是否出現 BGP、斷網、區域延遲、服務異常、底層流量變形。
- 為何有 alpha：衝突、封鎖、網戰部署常先反映在基礎設施層。

### 5. 邊緣衍生品與聰明錢
- 核心問題：冷門商品、prompt spread、options skew、鏈上巨鯨是否先動。
- 為何有 alpha：真正有資訊優勢的資金，常先進外圍、不顯眼的市場。

### 6. 決策圈數位排泄物
- 核心問題：高層與幕僚是否出現刪文、靜默、追蹤關係變動、行為節奏異常。
- 為何有 alpha：壓力下的清理和沉默，是比公關稿更真實的行為副產物。

## Layer B: Source / Ingestion Buckets

### 1. Channel Post
- 來源例子：Telegram channels, X lists, forum accounts
- 現況：已接 Gooaye

### 2. Stream Event
- 來源例子：Firehose, event stream, alert feeds
- 現況：NGI 舊系統有，lobster 尚未插件化

### 3. Market Feed
- 來源例子：Polymarket, futures, spreads, options proxies
- 現況：已有，但分散

### 4. Mobility / Physical OSINT Feed
- 來源例子：ADS-B, shipping, port data, routing anomalies
- 現況：已有，但主要在 NGI runtime

### 5. Linked Content
- 來源例子：YouTube, article pages, transcripts, linked news
- 現況：半成品

### 6. Visual Evidence
- 來源例子：screenshots, charts, OCR tables, maps
- 現況：半成品，queue 已有

### 7. Document Corpus
- 來源例子：PDF, reports, transcripts, procurement docs
- 現況：幾乎空

## Mapping Prototype

| Signal Thesis | Primary Source Buckets | Current Status |
|---|---|---|
| 區域微觀消費與活動 | Channel Post, Linked Content, Visual Evidence | 幾乎空 |
| 實體後勤與異常位移 | Mobility Feed, Stream Event, Visual Evidence | 部分可用 |
| 枯燥採購與招募激增 | Document Corpus, Linked Content, Stream Event | 幾乎空 |
| 數位基礎設施暗流 | Stream Event, Linked Content, Document Corpus | 幾乎空 |
| 邊緣衍生品與聰明錢 | Market Feed, Channel Post, Visual Evidence | 部分可用 |
| 決策圈數位排泄物 | Channel Post, Linked Content, Stream Event | 幾乎空 |

## Concrete Current Examples

### Gooaye #6060
- Signal thesis: 邊緣衍生品與聰明錢
- Source bucket: Channel Post + Visual Evidence
- Extracted signal: WTI +8.10%, Brent +8.14%, Heating Oil +9.00%, Gasoline +4.91%, Natural Gas +1.81%, Murban -1.47%
- Current handling: 已手動寫入 `first_principles_snapshots` 作為 energy signal

### ADS-B / Iran conflict proxy
- Signal thesis: 實體後勤與異常位移
- Source bucket: Mobility Feed
- Current handling: 已在 NGI runtime 使用

### Polymarket escalation / peace market
- Signal thesis: 邊緣衍生品與聰明錢
- Source bucket: Market Feed
- Current handling: 已在 NGI runtime 使用

## Immediate Gaps

1. Linked Content 還不能穩定抽正文
2. Visual Evidence 還沒有完整 OCR → structured evidence → runtime 回填
3. Document Corpus 幾乎沒有 ingest path
4. 每個 source 還沒有明確標注自己支援哪個 signal thesis

## Next Prototype Step

用 5 個真來源做手動 prototype：
1. Gooaye（Channel Post）
2. Firehose conflict stream（Stream Event）
3. Polymarket / crude proxy（Market Feed）
4. Linked article / YouTube transcript（Linked Content）
5. 圖片表格 / screenshot（Visual Evidence）

目標不是全接，而是先驗證：
- 哪些 source 真的能產生 information gap signal
- 哪些只是噪音搬運
- 哪些值得正式 skill 化與 cron 化
