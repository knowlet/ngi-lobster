# PLUGIN_CONTRACT

目的：定義 Lobster Intel 可開源、可安裝 plugin 的最小契約。

## Product boundary

第一版 plugin 應是 **stateless data provider**。

它負責：
- 擷取特定來源
- 解析原始資料
- 轉成標準化 artifact

它不負責：
- 直接訊息推播
- 自帶排程器
- 自管長期 state database
- 繞過 runtime / delivery gate

## Required manifest fields

每個 plugin 都需要 `plugin.json`，最少包含：

- `id`
- `name`
- `version`
- `type`
- `entrypoints.ingest`
- `produces`

可選：

- `entrypoints.compile`
- `entrypoints.evaluate`
- `capabilities`
- `tracker`
- `required_env`
- `notes`

## Capability split

- `capabilities`: external dependency or execution hints such as `web_fetch`, `ocr`, `image_understanding`
- `tracker`: Lobster-owned source contract describing replayability, source family, state persistence mode, and runtime follow-up queues

`capabilities` stays intentionally flat because it tells the host what the plugin depends on. `tracker` is the machine-readable contract that downstream runtime and operator tooling can trust without re-implementing plugin-specific rules.

## Entrypoint contracts

### ingest

```python
ingest(ctx) -> list[EvidenceRecord] | dict
```

用途：抓來源、標準化、輸出 evidence。

### compile (optional)

```python
compile(ctx, evidence) -> list[CompiledPage] | dict
```

用途：把 evidence 轉成較穩定的 derived artifact。

### evaluate (optional)

```python
evaluate(ctx, evidence, compiled) -> RuntimeSnapshot | AlertRecord | dict
```

用途：把 evidence / compiled 推進 runtime 判斷。

## Output rules

- plugin 必須產出 schema-valid artifacts
- plugin 不可直接做 delivery
- delivery 只能由主系統下游處理
- 背景任務若需要 user-visible output，必須走 gate
- 若 plugin 宣告 `runtime.*_queue` 輸出，必須同步宣告 `tracker.follow_up_queues`

## Tracker contract

`tracker` 欄位用來描述 source plugin 的 runtime-owned behavior：

- `source_family`: 上游來源家族，例如 `telegram_channel`、`rss_feed`、`prediction_market`
- `default_source_type`: plugin 沒有額外 config override 時預設產出的 `source_type`
- `replayable`: 是否能從 runtime artifacts 重播 / 重建
- `state_mode`: runtime 如何保存來源狀態，MVP 預設為 `cursor_json`
- `follow_up_queues`: plugin 可能送入 runtime 的後續處理佇列名稱，不含 `runtime.` 前綴

Gooaye tracker 是目前的參考 manifest：它宣告 `tracker.source_family=telegram_channel`，並把 `linked_content_queue` / `image_analysis_queue` 明確列在 `tracker.follow_up_queues`，讓 linked-content 與 image follow-up 保持在 runtime 真相層，而不是靠 ad hoc manifest 判斷。

## Minimal artifact flow

```text
source -> ingest -> evidence
                 -> optional compile -> compiled
                 -> optional evaluate -> runtime
delivery layer reads runtime, not plugin internals
```

## Installation principle

要能開源出去的 plugin，至少要做到：

1. manifest 清楚
2. entrypoint 可載入
3. 不依賴私有聊天輸出流程
4. 不把本地環境細節硬編進核心契約
