# R2 Key Contract Snapshot And Join Casebook

## 1. 목적

이 문서는 `R2. 저장 / export / replay 정합성`의 현재 구현 상태를
실제 코드 기준으로 다시 고정하는 스냅샷 문서다.

R2의 핵심은 아래 세 가지다.

- 어떤 key가 어떤 owner에서 만들어지는지
- runtime -> export -> replay -> semantic dataset 경로가 어떤 key로 이어지는지
- 현재 구현이 어떤 join health 산출물로 그 경로를 감시하는지

이 문서는 spec/checklist를 대체하지 않는다.
대신 R2 구현 도중 다시 참조할 수 있는 `key contract + join casebook` 역할을 한다.


## 2. 현재 구현 상태 요약

2026-03-26 기준 R2 1차 구현으로 아래가 이미 들어가 있다.

- export 단계:
  - `*.key_integrity.json` 생성
  - `key_integrity_report_path`를 summary / manifest에 기록
- replay 단계:
  - `replay_dataset_key_integrity_manifest_v1` 생성
  - `key_integrity_manifest_path`를 build manifest와 summary에 기록
  - detail sidecar join 시 `decision_row_key` fallback 추가
- semantic dataset 단계:
  - `semantic_v1_dataset_join_health_v1` 생성
  - `join_health_report_path`를 build manifest와 summary에 기록

즉 지금은 “key / join 상태를 보이지 않게 내부에서만 처리”하는 상태가 아니라,
각 단계가 자기 join health를 산출물로 남기는 상태까지는 도달했다.


## 3. Key Contract Snapshot

| Key | 생성 owner | 주 역할 | 비고 |
| --- | --- | --- | --- |
| `decision_row_key` | `resolve_entry_decision_row_key()` in [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L1193) | reason-bearing runtime row identity | non-action / wait / skipped row uniqueness의 기준축 |
| `runtime_snapshot_key` | `resolve_runtime_signal_row_key()` in [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L1227) | runtime signal linkage key | [trading_application_runner.py](c:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application_runner.py#L607)와 [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py#L1620)에서 주입/전달 |
| `trade_link_key` | `resolve_trade_link_key()` in [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L1239) | execution linkage key | 실제 진입/체결 row와 연결되는 축 |
| `replay_row_key` | `resolve_replay_dataset_row_key()` in [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L196) | replay / dataset join key | replay intermediate와 semantic dataset builder의 기준축 |

핵심 원칙은 이렇다.

- `decision_row_key`는 reason-bearing key다.
- `runtime_snapshot_key`는 signal linkage key다.
- `trade_link_key`는 execution linkage key다.
- `replay_row_key`는 replay/dataset join key다.

즉 네 key는 같은 의미가 아니고, 서로 대체 가능하다고 가정하면 안 된다.


## 4. Join Chain Snapshot

현재 R2에서 보는 기본 join 체인은 아래와 같다.

```text
runtime snapshot row
-> hot entry decision row
-> export parquet
-> replay intermediate row (+ detail sidecar merge)
-> semantic dataset feature/label join
```

각 구간의 주 key는 아래처럼 본다.

| 구간 | primary key | 보조 key / 확인 포인트 |
| --- | --- | --- |
| runtime snapshot -> hot decision | `runtime_snapshot_key`, `decision_row_key` | runtime row identity가 hot compact row로 그대로 내려오는지 |
| hot decision -> export parquet | `decision_row_key`, `runtime_snapshot_key`, `trade_link_key`, `replay_row_key` | export 누락 / key mismatch 여부 |
| hot decision + detail sidecar -> replay intermediate | `detail_row_key` 우선, 없으면 `decision_row_key`, `replay_row_key` fallback | detail join 실패가 silent drop으로 바뀌지 않는지 |
| replay intermediate -> semantic dataset | `replay_row_key` 중심 join | feature-only / label-only orphan key가 생기지 않는지 |


## 5. 현재 산출물 계약

### 5-1. Export Key Integrity Report

생성 위치:

- [export_entry_decisions_ml.py](c:\Users\bhs33\Desktop\project\cfd\scripts\export_entry_decisions_ml.py#L887)

핵심 필드:

- `report_version = entry_decisions_ml_key_integrity_v1`
- `missing_key_rows`
- `duplicate_key_rows`
- `decision_vs_replay_key_mismatch_rows`
- `key_integrity_report_path`

### 5-2. Replay Key Integrity Manifest

생성 위치:

- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L312)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L777)

핵심 필드:

- `manifest_type = replay_dataset_key_integrity_manifest_v1`
- `missing_key_rows`
- `decision_replay_key_mismatch_rows`
- `detail_row_key_present_rows`
- `key_integrity_manifest_path`

### 5-3. Semantic Dataset Join Health Report

생성 위치:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L534)
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L954)

핵심 필드:

- `report_version = semantic_v1_dataset_join_health_v1`
- `feature_only_join_keys_count`
- `label_only_join_keys_count`
- `joined_key_mismatch_rows`
- `join_health_report_path`


## 6. 이번 1차 구현에서 닫힌 케이스

### 6-1. Replay detail sidecar fallback 보강

이번 구현 전에는 replay detail merge가 `detail_row_key`가 비어 있을 때
join miss에 더 취약했다.

지금은 [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L475) 에서
아래 순서로 key를 시도한다.

1. `detail_row_key`
2. `decision_row_key`
3. `replay_row_key`
4. `resolve_replay_dataset_row_key(merged)`

즉 hot row에 explicit `detail_row_key`가 없더라도,
detail sidecar가 `decision_row_key` 기준으로 저장된 케이스는
이제 replay intermediate로 복원 가능하다.

### 6-2. Export / Replay / Dataset health 가시화

이제 각 단계는 단순 성공/실패만 남기는 게 아니라,
`왜 join health가 나쁜지`를 따로 파일로 남긴다.


## 7. 아직 남아 있는 R2 감사 항목

아직 R2 전체가 닫힌 것은 아니다.

남은 핵심은 아래다.

1. live sample 기준 `decision_row_key` uniqueness memo 작성
2. join coverage casebook 작성
3. hot/detail -> export/replay propagation table 작성
4. mixed legacy/latest row 기준 semantic dataset builder compatibility memo 작성


## 8. 관련 테스트 스냅샷

이번 1차 구현 기준 확인된 테스트는 아래다.

- `pytest tests/unit/test_export_entry_decisions_ml.py tests/unit/test_replay_dataset_builder.py tests/unit/test_semantic_v1_dataset_builder.py`
  - `19 passed`
- `pytest tests/unit/test_storage_compaction.py`
  - `11 passed`


## 9. 다음 착수점

R2 다음 착수점은 아래 순서가 가장 자연스럽다.

1. live sample 기준 key uniqueness / join coverage memo 작성
2. hot/detail propagation table 작성
3. semantic dataset builder compatibility memo 작성
4. 그 다음에 `R3. Semantic ML Step 3~7 refinement`

