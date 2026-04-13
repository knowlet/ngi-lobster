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
- `required_env`
- `notes`

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

