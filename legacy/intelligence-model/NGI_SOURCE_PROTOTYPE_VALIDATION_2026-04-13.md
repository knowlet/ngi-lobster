# NGI Source Prototype Validation (2026-04-13)

目的：先用真資料驗證 5 類 source bucket，確認哪些真的能形成 information-gap signal，哪些目前只是噪音搬運。

## 1. Channel Post — Gooaye #6060
- Source bucket: Channel Post
- Signal thesis: 邊緣衍生品與聰明錢
- Raw input: Telegram post + commodity board image
- Extracted facts:
  - WTI `+8.10%`
  - Brent `+8.14%`
  - Heating Oil `+9.00%`
  - Gasoline `+4.91%`
  - Natural Gas `+1.81%`
  - Murban `-1.47%`
- Verdict: **PASS**
- Why it matters: 這種貼文不是正式報告，但能比主流敘事更早把能源微結構壓力丟進系統。
- Current system state: 已手動寫入 `first_principles_snapshots`，topic=`iran_conflict`，signal_type=`energy`

## 2. Stream Event — Firehose recent conflict stream
- Source bucket: Stream Event
- Signal thesis: 數位基礎設施暗流 / 決策圈數位排泄物（弱）
- Recent examples:
  - `kinetic-redsea` → "The Islamabad Shadow and the Ghost of a Grand Bargain"
  - `kinetic-isr-ira` → aggregator / portal junk
  - `kinetic-isr-ira` → Taipanpublishinggroup article
- Verdict: **MIXED / NOISY**
- Why it matters: 事件流能很早，但目前 mixed quality 很高，雜訊不少。
- Current system state: 有進 NGI 舊系統，但缺 source-level filtering / ranking。

## 3. Market Feed — Polymarket active target
- Source bucket: Market Feed
- Signal thesis: 邊緣衍生品與聰明錢
- Current live target:
  - market id: `1517836`
  - market: `Trump announces end of military operations against Iran by June 30th`
  - market yes probability: `0.805`
  - interpreted market escalation probability: `0.195`
- First-principles escalation probability: `0.2267`
- NGI gap: `3.17pp`
- Verdict: **PASS**
- Why it matters: 市場仍是核心定價參考，但必須跟 first-principles proxy 對照才有 alpha。
- Current system state: 已在 NGI runtime 內部使用

## 4. Linked Content — Gooaye #6057 YouTube link
- Source bucket: Linked Content
- Signal thesis: 決策圈數位排泄物 / 外部敘事補證
- Raw input:
  - YouTube title: `Vice President JD Vance Delivers Remarks in Islamabad, Pakistan`
- What we actually have:
  - only preview metadata
  - no transcript
  - no body extraction
- Verdict: **FAIL (for now)**
- Why it matters: 這類來源理論上很重要，但目前只有 title，還不夠形成強訊號。
- Current system state: metadata only, no stable全文抽取

## 5. Visual Evidence — Gooaye #6059 comparison chart
- Source bucket: Visual Evidence
- Signal thesis: 邊緣衍生品與聰明錢 / 補充監管背景
- Raw input:
  - image-only comparison chart
  - main columns: `Feature / FSD US / FSD Europe (Netherlands)`
- What we actually have:
  - image identified
  - chart topic identified
  - but stable OCR -> structured evidence loop not complete
- Verdict: **PARTIAL PASS**
- Why it matters: 圖裡其實有內容，但如果沒有穩定 OCR 證據鏈，就容易滑向腦補。
- Current system state: queue exists, one-off extraction possible, product loop incomplete

## Prototype verdict summary

| Source bucket | Example | Verdict | Product readiness |
|---|---|---|---|
| Channel Post | Gooaye #6060 | PASS | usable with manual review |
| Stream Event | Firehose conflict stream | MIXED | usable only with filtering |
| Market Feed | Polymarket 1517836 | PASS | core runtime input |
| Linked Content | Gooaye #6057 YouTube | FAIL | missing extraction layer |
| Visual Evidence | Gooaye #6059 chart | PARTIAL PASS | queue exists, loop incomplete |

## Main insight
目前最能直接產生 information-gap signal 的是：
1. **Channel Post + manual/vision enrichment**
2. **Market Feed + first-principles comparison**

目前最拖後腿的是：
1. **Linked Content extraction**
2. **Visual Evidence end-to-end OCR回填**
3. **Firehose quality filtering**

## Product implication
下一個產品化優先序應該是：
1. 補 `Linked Content` 抽正文 / transcript
2. 補 `Visual Evidence` 的 OCR -> structured evidence -> runtime 回填
3. 為 `Stream Event` 加 ranking / junk suppression

這三件補上之後，系統才會從「會收訊號」變成「會穩定產生可操作 insight」。
