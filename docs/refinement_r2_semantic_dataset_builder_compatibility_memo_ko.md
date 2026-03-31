# R2 Semantic Dataset Builder Compatibility Memo

## 1. 목적

이 문서는 `R2. 저장 / export / replay 정합성`의 마지막 audit 산출물로,
`ml/semantic_v1/dataset_builder.py`가 최신 runtime/export/replay row 구조를
실제로 안정적으로 읽고 있는지 코드, 테스트, 샘플 산출물 기준으로 고정한다.

이 문서의 목적은 새 target을 정의하는 것이 아니라,

- 최신 key 계약이 semantic dataset build까지 이어지는지
- legacy / modern / mixed source가 안전하게 처리되는지
- join 누락이 silent drop으로 숨어들지 않는지

를 근거와 함께 설명 가능하게 만드는 것이다.


## 2. 확인 기준

### 코드 기준

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
  - `_resolve_feature_files`: 312
  - `_resolve_replay_files`: 323
  - `_detect_source_generation`: 329
  - `_feature_tier_policy`: 341
  - `_load_feature_frame`: 391
  - `_load_replay_label_frame`: 427
  - `_build_join_health_report`: 534
  - `build_semantic_v1_datasets`: 926

### 테스트 기준

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
  - 기본 dataset build / manifest / join health: 17
  - legacy trace-quality compatibility: 339
  - duplicate join key by occurrence preservation: 590
  - outcome semantics target preference: 748

### 실제 샘플 기준

- [exit_management_dataset.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1\r2_audit\exit_management_dataset.parquet.summary.json)
- [exit_management_dataset.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1\r2_audit\exit_management_dataset.parquet)
- [semantic_v1_dataset_join_health_20260326_135404_051547.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_join_health_20260326_135404_051547.json)


## 3. 현재 compatibility 계약

### 3-1. feature source resolution

- feature source는 기본적으로 `data/datasets/ml_exports/replay/*.parquet`를 읽는다.
- replay compact parquet가 없고 기본 경로를 그대로 쓸 때만
  `data/datasets/ml_exports/forecast/*.parquet`를 fallback으로 쓴다.
- 즉 최신 semantic dataset은 replay compact export를 first-class source로 본다.

### 3-2. replay source resolution

- replay source는 `data/datasets/replay_intermediate/*.jsonl`를 읽는다.
- directory뿐 아니라 개별 파일 경로도 직접 입력할 수 있다.

### 3-3. source generation 해석

- file name에 `legacy`가 모두 있으면 `legacy`
- 일부만 있으면 `mixed`
- 없으면 `modern`
- 없거나 비어 있으면 `unknown`

이 generation은 feature tier policy를 고를 때 직접 사용된다.

### 3-4. feature tier policy

- `legacy`
  - `semantic_input_pack`: `enabled`
  - `trace_quality_pack`: `observed_only`
- `modern` / `mixed`
  - `semantic_input_pack`: `enabled`
  - `trace_quality_pack`: `enabled`

즉 legacy source에서 trace-quality 계열이 전부 비어 있어도
dataset build 자체를 깨지 않고, all-missing column만 드롭하는 방향으로 동작한다.

### 3-5. join contract

- feature frame의 primary join key는 `replay_row_key`, 없으면 `decision_row_key`
- replay label frame의 primary join key도 `replay_row_key`, 없으면 `decision_row_key`
- 양쪽 모두 `join_key` 기준으로 `join_ordinal`을 부여해 중복 key를 occurrence 순서대로 보존한다.
- 최종 base join은 `join_key + join_ordinal` inner join이다.

즉 `decision_row_key` 중복이 과거 데이터에 남아 있어도,
동일 순서의 row끼리 매칭될 수 있게 설계돼 있다.

### 3-6. failure surface

- feature source가 없으면 즉시 `FileNotFoundError`
- replay source가 없으면 즉시 `FileNotFoundError`
- join 결과가 0 rows면 즉시 `ValueError`
- join mismatch / orphan는 `join_health_report`로 드러난다.

즉 builder는 key 문제를 조용히 숨기지 않고,
`fail fast` 또는 `health report` 형태로 surface한다.


## 4. 테스트로 확인된 보장

### 4-1. 기본 build 보장

[test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py):17 기준으로,

- timing / entry_quality / exit_management 3종 dataset이 모두 생성되고
- manifest와 join health report가 같이 기록되며
- `decision_row_key`, `runtime_snapshot_key`, `trade_link_key`, `replay_row_key`가 dataset에 남는다.

### 4-2. legacy compatibility 보장

[test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py):339 기준으로,

- legacy row에서 trace-quality 계열이 전부 비어 있어도 build는 실패하지 않고
- `observed_only` policy에 따라 all-missing column만 드롭되며
- summary / manifest에 dropped feature 이유가 기록된다.

### 4-3. duplicate join key 보장

[test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py):590 기준으로,

- 동일 `decision_row_key` / `replay_row_key`가 반복되는 경우에도
- `join_ordinal` 덕분에 occurrence 순서대로 join이 유지된다.

이건 R2 uniqueness audit에서 확인한 historical duplicate가
semantic dataset build를 즉시 깨뜨리지 않는 이유이기도 하다.

### 4-4. semantic target source 보장

[test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py):748 기준으로,

- replay row의 `outcome_labels_v1` 기반 semantic target feature가
  label summary보다 우선 반영될 수 있다.

이건 compatibility 관점에서 중요한데,
최신 replay 구조가 builder에서 실제로 읽히고 있다는 뜻이기 때문이다.


## 5. 실제 r2_audit 샘플로 확인된 보장

### 5-1. generation과 join health

[semantic_v1_dataset_join_health_20260326_135404_051547.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_join_health_20260326_135404_051547.json) 기준:

- `joined_rows = 300`
- `feature_only_join_keys_count = 700`
- `label_only_join_keys_count = 0`
- `joined_key_mismatch_rows.runtime_snapshot_key = 0`

여기서 `feature_only_join_keys_count = 700`은 join bug가 아니라,
감사 샘플에서 feature export를 1000 rows, replay label을 300 rows로 잘라 쓴 데서 온 크기 차이였다.
즉 label 쪽 orphan나 mismatch 문제는 아니었다.

또 [exit_management_dataset.parquet.summary.json](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1\r2_audit\exit_management_dataset.parquet.summary.json) 기준:

- `source_generation = modern`

즉 최신 compact / replay 산출물 조합은 modern 경로로 안정적으로 처리되고 있다.

### 5-2. latest row scalar survival

실제 summary와 parquet 컬럼을 확인한 결과, semantic dataset에는 아래 축이 유지된다.

- key columns
  - `decision_row_key`
  - `runtime_snapshot_key`
  - `trade_link_key`
  - `replay_row_key`
- reason triplet
  - `observe_reason`
  - `blocked_by`
  - `action_none_reason`
- trace scalar
  - `quick_trace_state`
  - `quick_trace_reason`
- semantic scalar
  - `semantic_shadow_*`
  - `semantic_live_*`
  - `semantic_target_source`

즉 최신 hot/export slim scalar는 dataset builder를 지나도 그대로 남는다.


## 6. 무엇이 직접 안 넘어가고, 무엇이 호환으로 간주되는가

### 직접 dataset column으로 안 넘어가는 것

- `entry_probe_plan_v1`
- `probe_candidate_v1`
- `entry_decision_context_v1`
- `entry_decision_result_v1`

이 payload들은 replay intermediate의 `decision_row` 안에는 merge되어 남을 수 있지만,
semantic dataset에서는 nested JSON 자체가 아니라 derived scalar feature만 살아남는다.

이건 compatibility failure가 아니라 현재 설계다.

### 호환으로 간주되는 조건

- nested payload가 dataset column으로 직접 남지 않아도 된다.
- 대신 그 payload에서 파생된 slim scalar가 export와 dataset에 유지되면 된다.
- key, reason, quick trace, semantic scalar가 유지되고 join health가 깨지지 않으면
  R2 Step 5 기준으로는 호환으로 본다.


## 7. 현재 남는 주의점

### 7-1. historical duplicate는 upstream 정리 대상이다

R2 uniqueness audit에서 본 historical duplicate `decision_row_key`는
builder의 `join_ordinal` 덕분에 당장 build를 깨뜨리진 않는다.
하지만 source CSV 안에 과거 중복이 남아 있다는 사실 자체는
upstream data hygiene 이슈로 계속 추적해야 한다.

future write-path fix는 이미 [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)에 반영돼 있다.

### 7-2. label sparsity는 compatibility failure가 아니다

`feature_only_join_keys_count`가 남거나 일부 target이 unknown-heavy인 건
R2 compatibility 실패라기보다 R3 target/split 품질 쪽 이슈다.

즉 R2는 “join과 latest row compatibility”를 닫는 단계이고,
label density나 promotion suitability는 다음 단계 owner다.


## 8. 결론

현재 기준으로 `semantic dataset builder latest-row compatibility`는
R2 범위 안에서 닫혔다고 볼 수 있다.

근거는 아래 세 가지다.

- 코드상으로 latest key / source_generation / feature tier / join health contract가 명시돼 있다.
- 테스트상으로 legacy compatibility, duplicate join preservation, latest semantic target source 반영이 잠겨 있다.
- 실제 `r2_audit` 샘플에서도 key, reason, quick trace, semantic scalar가 dataset까지 살아 있고
  join mismatch가 0으로 확인된다.

따라서 R2의 다음 착수점은 더 이상 dataset builder compatibility가 아니라,
`R3. Semantic ML Step 3~7 refinement`로 넘어가는 쪽이 맞다.
