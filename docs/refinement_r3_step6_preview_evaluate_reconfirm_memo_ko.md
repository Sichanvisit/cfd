# R3 Step 6 Preview / Evaluate Reconfirm Memo

## 1. 목적

이 문서는 `R3 Step 6. legacy feature tier refinement` 이후
preview / evaluate 재확인 결과를 남기는 memo다.

## 2. 비교 기준

이번 비교도 이전 Step과 동일하게
explicit legacy baseline pair를 그대로 유지했다.

- feature source:
  [entry_decisions.legacy_20260311_175516.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.legacy_20260311_175516.replay.parquet)
- replay source:
  [replay_dataset_rows_20260321_150851.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_legacy_20260311_175516_mt5\replay_dataset_rows_20260321_150851.jsonl)

새 산출물:

- dataset build manifest:
  [semantic_v1_dataset_build_20260326_163015_945811.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_163015_945811.json)
- model metrics:
  [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_step6_20260326\metrics.json)
- preview audit:
  [semantic_preview_audit_20260326_163125.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_163125.json)
- latest audit:
  [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

## 3. preview 결과

Step 5 대비 Step 6 결과는 모두 동일했다.

### timing

- rows: `2351 -> 2351`
- auc: `0.633218 -> 0.633218`
- split_health: `healthy -> healthy`

### entry_quality

- rows: `1507 -> 1507`
- auc: `0.598303 -> 0.598303`
- split_health: `warning -> warning`

### exit_management

- rows: `785 -> 785`
- auc: `0.876899 -> 0.876899`
- split_health: `warning -> warning`

promotion gate도 그대로 유지됐다.

- `status = pass`
- `shadow_compare_ready = true`
- warnings:
  - `entry_quality:split_health_warning`
  - `exit_management:split_health_warning`

## 4. 왜 수치가 안 바뀌었는가

이번 Step 6의 핵심은
`current legacy baseline 성능 개선`이 아니라
`feature tier 해석을 안전하게 만들고 visibility를 높이는 것`이었다.

그리고 현재 explicit preview pair는
이미 `source_generation = legacy`였다.

즉:

- legacy는 원래도 `trace_quality_pack = observed_only`
- 이번 변경의 핵심인 mixed safer policy는 current preview pair에 직접 영향을 주지 않음
- 따라서 numeric metrics는 그대로 유지되는 것이 정상

## 5. Step 6에서 실제로 달라진 것

numeric metric은 그대로지만,
summary와 metrics에서 아래 정보가 더 잘 보인다.

- `feature_tier_summary`
- `observed_only_dropped_feature_columns`

실제 Step 6 legacy summary 기준:

- `trace_quality_pack.mode = observed_only`
- `trace_quality_pack.candidate_count = 37`
- `trace_quality_pack.retained_count = 4`
- `trace_quality_pack.dropped_count = 33`
- `trace_quality_pack.observed_only_dropped_count = 33`

즉 이제는
"legacy라서 trace-quality가 비어 있다"가
숫자와 컬럼 리스트로 직접 보이게 됐다.

## 6. 현재 판단

이번 Step 6은 current preview를 깨지 않으면서 아래를 달성했다.

- mixed source를 safer observed-only로 내렸다
- feature tier surface를 summary/metrics에 추가했다
- old dataset summary도 backward compatible하게 읽힌다

따라서 Step 6은 current baseline 기준으로 닫아도 되고,
다음 active step은 `Step 7 preview / audit refinement`가 맞다.
