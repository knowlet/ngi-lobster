# Focused review request for 姨太

## Cut
PR #26 `fix: project runtime latest_ngi explain contract`

## Why this review now
目前最小可 upstream 的 runtime explain-contract cut 已經在 `codex/pr21-recut-dispatcher-receipt-guard` 並開成 PR #26，但 remote 還卡在兩個點：
1. `mergeStateStatus = DIRTY`
2. `CommitCheck = PENDING`

產品角度上，這一刀已把 PO 缺的 live `latest_ngi.json` explain contract 往前推到可 review 狀態；現在需要你集中確認 fail-closed 邏輯與欄位契約是否足以直接 recut / rebase 後送 merge，而不是再擴 scope。

## Please review exactly this
1. `runtime: fail closed when alert target id is missing` 這個 guard，是否就是目前最薄且正確的 fail-closed seam？
2. live `latest_ngi.json` 上的 `alert_disposition` / `alert_target_id` / `target_contract_match` / `contract_version` / `e2e_run_id`，哪些已可視為這一刀的 required contract？
3. 若要解 PR #26 的 DIRTY 狀態，你建議直接 rebase recut，還是先補一個更小的 conflict-only cut？
4. `lobster-intel/tests/test_runtime_spine_dispatcher_path.py` 現有 coverage，是否已足夠守住 suppressed path 的 target-lineage fail-closed 行為？

## Evidence checked
- branch: `codex/pr21-recut-dispatcher-receipt-guard`
- HEAD: `ad70eab11148540ea2b748857a020919ae43b24f`
- PR: `https://github.com/knowlet/ngi-lobster/pull/26`
- latest commits in cut:
  - `ad70eab` runtime: fail closed when alert target id is missing
  - `689f5b4` docs: add live latest ngi review brief
  - `5c5fec9` runtime: stamp live alert disposition e2e run id
  - `ab4208c` runtime: project dispatcher disposition onto runtime snapshot
- repo state at request prep time: working tree clean, branch synced with origin, PR open but blocked on `DIRTY` + pending `CommitCheck`

## Proposed next cut after review
若你認可這個切法，下一刀就只做「解 DIRTY 並重送可 merge 的最小 recut」，不再擴產品欄位範圍。