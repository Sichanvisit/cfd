# R2 Hot Detail Propagation Audit

## 1. 목적

이 문서는 R2 `Step 4. Hot / Detail Propagation Audit` 전용 메모다.

핵심 질문은 아래다.

- 어떤 필드가 hot CSV에 compact 형태로 남는가
- 어떤 필드가 detail sidecar에 full payload로 남는가
- export parquet는 어떤 필드를 그대로 가져가고, 어떤 nested payload는 derived scalar로만 유지하는가
- replay intermediate는 hot row에 detail sidecar를 어떻게 다시 합치는가
- semantic dataset는 결국 어떤 축만 downstream feature/label로 남기는가


## 2. 기준 구현 경로

핵심 owner는 아래다.

- hot/detail 생성:
  - [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- export parquet:
  - [export_entry_decisions_ml.py](c:\Users\bhs33\Desktop\project\cfd\scripts\export_entry_decisions_ml.py)
- replay intermediate:
  - [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)
- semantic dataset:
  - [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

핵심 원칙은 이렇다.

- hot row는 compact trace 중심
- detail sidecar는 full forensic payload 중심
- replay intermediate는 hot + detail merge 결과를 `decision_row`에 담음
- semantic dataset는 replay의 nested payload를 직접 쓰지 않고, export parquet의 slim column을 중심으로 쓴다


## 3. 전달 단계 요약

```text
full runtime payload
-> hot CSV row (compact trace)
-> detail JSONL row (full payload)
-> export parquet (selected slim columns)
-> replay intermediate (hot + detail merge, nested decision_row 보존)
-> semantic dataset (export slim columns + replay labels join)
```


## 4. 필드군별 propagation 표

| 필드군 | hot CSV | detail sidecar | export parquet | replay intermediate | semantic dataset |
| --- | --- | --- | --- | --- | --- |
| `observe_reason`, `blocked_by`, `action_none_reason` | scalar로 유지 | full payload에도 유지 | scalar column으로 유지 | top-level이 아니라 `decision_row` 안에 유지 | scalar column으로 유지 |
| `entry_probe_plan_v1`, `probe_candidate_v1` | compact JSON string으로 유지 | full mapping 유지 | nested payload 자체는 미포함, 대신 probe derived scalar 유지 | `decision_row` 안에 full/merged payload 유지 | nested payload 미포함, probe derived scalar만 유지 |
| `entry_decision_context_v1`, `entry_decision_result_v1` | compact JSON string으로 유지 | full mapping 유지 | nested payload 자체는 미포함, 대신 entry/wait/consumer derived scalar 유지 | `decision_row` 안에 full/merged payload 유지 | nested payload 미포함, derived scalar만 유지 |
| `semantic_shadow_*`, `semantic_live_*` | scalar로 유지 | full payload에도 유지 | scalar column으로 유지 | `decision_row` 안에 유지 | scalar column으로 유지 |


## 5. 필드군별 상세 해석

### 5-1. reason triplet

`observe_reason`, `blocked_by`, `action_none_reason`는
hot row 단계에서 이미 scalar로 노출된다.

근거:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L0840)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L0875)

의미:

- 차트/분포/수출(export) 단계에서 바로 읽을 수 있는 이유 필드
- replay intermediate에서는 top-level field로 다시 펼치지 않고
  `decision_row` 안에서 유지된다


### 5-2. probe / decision nested payload

`entry_probe_plan_v1`, `probe_candidate_v1`,
`entry_decision_context_v1`, `entry_decision_result_v1`는
hot CSV에 아예 빠지는 것이 아니라 compact JSON 형태로 남는다.

근거:

- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L0961)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py#L0973)

하지만 export parquet는 nested payload를 직접 실어 나르지 않는다.
대신 아래 같은 scalar를 유지한다.

- `probe_candidate_active`
- `probe_direction`
- `probe_scene_id`
- `probe_candidate_support`
- `probe_pair_gap`
- `probe_plan_active`
- `probe_plan_ready`
- `probe_plan_reason`
- `probe_plan_scene`
- `probe_promotion_bias`
- `quick_trace_state`
- `quick_trace_reason`

즉 export 이후 downstream에서 nested JSON contract 자체를 기대하면 안 되고,
probe/decision은 이미 compact scalar 형태로 보는 게 기준이다.


### 5-3. semantic shadow / live scalar

`semantic_shadow_*`, `semantic_live_*`는 처음부터 slim scalar field로 다뤄진다.

근거:

- [export_entry_decisions_ml.py](c:\Users\bhs33\Desktop\project\cfd\scripts\export_entry_decisions_ml.py#L0073)

이 필드군은

- hot CSV에 scalar로 유지
- export parquet에 그대로 유지
- semantic dataset에도 실제 feature column으로 유지

즉 semantic runtime activation / threshold 상태는
R2 이후 dataset 단계에서도 직접 추적 가능한 필드군이다.


## 6. replay intermediate에서의 복원 규칙

replay intermediate는 hot row만 그대로 쓰지 않는다.
먼저 detail sidecar를 병합한 뒤 `decision_row` nested payload로 넣는다.

핵심 위치:

- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L0475)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py#L0644)

병합 순서:

1. `detail_row_key`
2. `decision_row_key`
3. `replay_row_key`
4. `resolve_replay_dataset_row_key(merged)`

의미:

- hot CSV가 slim이어도 replay intermediate는 detail sidecar가 있으면 full payload에 가깝게 복원된다
- R2에서 detail sidecar 용량 최적화보다 join 안정성을 우선하는 이유가 바로 여기에 있다


## 7. semantic dataset 단계의 진짜 기준

semantic dataset builder는 replay intermediate의 nested `decision_row`를
그대로 feature column으로 펼치지 않는다.

실제 기준은:

- feature source:
  - export parquet slim column
- label source:
  - replay intermediate row / label bundle

근거:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L0946)
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L0948)

즉 downstream compatibility를 볼 때는
“replay row에 nested payload가 있느냐”보다
“export slim column에 필요한 derived scalar가 남아 있느냐”가 더 중요하다.


## 8. 실제 샘플 기준 확인

### wait / non-entry sample

사용 파일:

- [entry_decisions.r2_audit.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit.replay.parquet)
- [replay_dataset_rows_r2_audit.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate\replay_dataset_rows_r2_audit.jsonl)
- [semantic_v1_dataset_join_health_20260326_135404_051547.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_join_health_20260326_135404_051547.json)

확인 포인트:

- `observe_reason`, `blocked_by`, `action_none_reason`는 export에 있다
- replay에서는 같은 값이 `decision_row` 안에 있다
- semantic dataset에는 다시 scalar column으로 있다
- `trade_link_key`는 비어 있지만 wait row에서는 정상이다

### entered / execution sample

사용 파일:

- [entry_decisions.r2_audit_entered.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.r2_audit_entered.replay.parquet)
- [replay_dataset_rows_r2_audit_entered.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate\replay_dataset_rows_r2_audit_entered.jsonl)

확인 포인트:

- entered row에서는 `trade_link_key`가 export와 replay 모두에 유지된다
- historical duplicate `decision_row_key`가 남아 있어도 `trade_link_key`는 실제 execution linkage를 유지한다


## 9. 현재 판정

현재 propagation audit 판정은 아래와 같다.

### 통과

- reason triplet은 hot -> export -> replay decision_row -> semantic dataset으로 이어진다
- probe/decision nested payload는 hot compact + detail full + replay merge 구조로 이어진다
- semantic shadow/live scalar는 dataset까지 유지된다
- replay intermediate는 detail sidecar를 이용해 full payload를 복원할 수 있다

### 주의

- nested contract payload를 semantic dataset에서 직접 기대하면 안 된다
- semantic dataset는 export slim column 기준으로 읽는다고 봐야 한다
- historical duplicate `decision_row_key`는 propagation 문제가 아니라 uniqueness 문제다


## 10. 다음 액션

R2에서 다음으로 남은 핵심은 아래다.

1. semantic dataset builder compatibility memo 작성
2. historical duplicate row 처리 정책 정리
3. R2 전체 종료 판단

