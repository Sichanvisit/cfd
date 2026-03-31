# R3 Step 5 Preview / Evaluate Reconfirm Memo

## 1. 목적

이 문서는 `R3 Step 5. entry_quality target refinement` 이후
preview / evaluate 재확인 결과를 남기는 memo다.

## 2. 비교 기준

이번 비교는 Step 4 때 사용한 explicit legacy baseline pair를 그대로 유지했다.

- feature source:
  [entry_decisions.legacy_20260311_175516.replay.parquet](c:\Users\bhs33\Desktop\project\cfd\data\datasets\ml_exports\replay\entry_decisions.legacy_20260311_175516.replay.parquet)
- replay source:
  [replay_dataset_rows_20260321_150851.jsonl](c:\Users\bhs33\Desktop\project\cfd\data\datasets\replay_intermediate_legacy_20260311_175516_mt5\replay_dataset_rows_20260321_150851.jsonl)

새 산출물:

- dataset build manifest:
  [semantic_v1_dataset_build_20260326_161420_566613.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\export\semantic_v1_dataset_build_20260326_161420_566613.json)
- model metrics:
  [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_step5_20260326\metrics.json)
- preview audit:
  [semantic_preview_audit_20260326_161519.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_161519.json)
- latest audit:
  [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

## 3. entry_quality 결과

Step 4 대비 Step 5 결과는 아래와 같다.

- rows: `1507 -> 1507`
- accuracy: `0.444592 -> 0.444592`
- auc: `0.598303 -> 0.598303`
- brier_score: `0.493039 -> 0.493039`
- calibration_error: `0.497162 -> 0.497162`
- split_health_status: `warning -> warning`
- warning issues:
  - `preflight_regime:failing_slices=1/2`

즉 current legacy preview 기준으로 entry_quality numeric change는 없다.

## 4. 왜 숫자가 안 바뀌었는가

이번 Step 5는 아래 safety를 넣었다.

- hold-best conflict veto
- fallback-heavy veto
- reason-based ambiguity handling

하지만 current legacy baseline entry_quality dataset은:

- `compatibility_mode`가 사실상 비어 있고
- `management_hold_favor_positive_count > management_exit_favor_positive_count` 케이스가 실질적으로 없고
- selected feature set 기준 fallback-heavy signal도 살아 있지 않다

그래서 이번 1차 refinement는 current legacy preview row들을 다시 분류하지 않았고,
대신 mixed/modern row에서 future ambiguity handling을 위한 계약만 추가한 상태다.

## 5. 다른 target 영향

이번 rebuild에서 다른 target은 그대로 유지됐다.

- timing auc: `0.633218`
- exit_management auc: `0.876899`
- promotion gate:
  - `status = pass`
  - `shadow_compare_ready = true`
  - warnings:
    - `entry_quality:split_health_warning`
    - `exit_management:split_health_warning`

즉 Step 5는 current preview baseline을 깨지 않았다.

## 6. 현재 판단

이번 Step 5는 `성능 개선형 변화`라기보다 `target contract 정리형 변화`에 가깝다.

정확한 해석은 이렇다.

- current legacy baseline 기준:
  - no-regression
  - no-metric-shift
- mixed/modern future row 기준:
  - ambiguous / hold-conflict / fallback-heavy를 설명 가능하게 만듦

따라서 Step 5는 current baseline 기준으로 닫아도 되고,
다음 active step은 `Step 6 legacy feature tier refinement`가 맞다.
