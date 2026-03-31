# R3 Step 4 Split Health Reconfirm Memo

## 1. 목적

이 문서는 `R3 Step 4 split health refinement` 구현 후

- 무엇을 코드로 바꿨는지
- split health가 실제 preview 산출물에서 어떻게 보이는지
- 다음 active step을 왜 `Step 5 entry_quality target refinement`로 넘겨도 되는지

를 정리한 메모다.

## 2. 이번 Step 4에서 반영한 것

적용 파일:

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)

핵심 변경:

1. `split_health` payload를 [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py) owner로 끌어올렸다.
2. 기존 `overall_status / bucket_health / slice_health`만 있던 구조에 아래를 추가했다.
   - `bucket_coverage`
   - `holdout_health`
   - `class_imbalance_ratio`
   - `time_split_strategy`
3. [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)는 이 payload를 그대로 metrics에 담도록 정리했다.

## 3. 이번 Step 4에서 읽을 수 있게 된 것

이제 target별 `split_health`에서 최소 아래를 바로 읽을 수 있다.

- train / validation / test의 시계열 범위
- split별 symbol 분포
- split별 regime 분포
- split별 label imbalance 정도
- symbol holdout / regime holdout이 실제로 비어 있는지
- warning이 bucket 문제인지 slice 문제인지

즉 이전처럼 `healthy / warning / fail`만 보는 게 아니라,
왜 warning인지 한 단계 더 설명 가능한 구조가 됐다.

## 4. 검증

단위 테스트:

- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_promotion_guard.py)
- [test_semantic_v1_runtime_adapter.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_runtime_adapter.py)
- [test_semantic_v1_shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_shadow_compare.py)
- [test_check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_check_semantic_canary_rollout.py)
- [test_promote_semantic_preview_to_shadow.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_promote_semantic_preview_to_shadow.py)

결과:

- semantic 관련 묶음 `30 passed`

## 5. Preview Reconfirm

이번 Step 4 기준 preview metrics는 새 output으로 다시 만들었다.

metrics:

- [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_step4_20260326\metrics.json)

preview audit:

- [semantic_preview_audit_20260326_155706.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_155706.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

promotion gate summary:

- `shadow_compare_ready = true`
- `status = pass`
- warning:
  - `entry_quality:split_health_warning`
  - `exit_management:split_health_warning`

## 6. 현재 해석

### timing

- `split_health = healthy`
- 기존 Step 3 timing 개선은 유지된다.
- train / validation / test coverage를 더 자세히 읽을 수 있게 됐지만,
  현재 기준으로 promotion을 막는 split issue는 없다.

### entry_quality

- `split_health = warning`
- warning source는 `preflight_regime` slice weakness다.
- 즉 target 자체보다 split slice coverage가 약한 부분이 드러난 상태다.

### exit_management

- `split_health = warning`
- warning source는 `symbol`과 `setup_id` slice weakness다.
- 즉 exit_management는 성능 수치가 좋아도 split 해석은 아직 보수적으로 읽어야 한다.

### holdout health

- 현재 preview dataset에서는 `symbol_holdout_bucket`, `regime_holdout_bucket`이 실질적으로 비어 있어
  `holdout_health`에 `empty_holdout_bucket` warning이 같이 surface된다.
- 이건 지금 바로 failure로 보진 않지만,
  다음 gate에서 holdout 운용을 더 분명히 봐야 한다는 뜻이다.

## 7. Step 4 완료 판단

이번 기준으로 Step 4는 닫아도 된다.

이유:

- split health가 이전보다 설명 가능해졌다.
- preview 산출물에 새 split payload가 실제로 들어갔다.
- warning/failure의 source를 row/slice 기준으로 더 분리해 읽을 수 있다.
- 다음 Step 5에서 target refinement를 하더라도 split 해석 기준이 먼저 흔들리지 않는다.

## 8. 다음 단계

다음 active step은 `Step 5 entry_quality target refinement`다.

Step 5에서는:

- 좋은 진입 / 애매한 진입 / hold가 더 나았던 진입의 정의
- timing과 entry_quality의 경계
- leakage 없이 설명 가능한 positive / negative / ambiguous 규칙

을 다시 고정하면 된다.
