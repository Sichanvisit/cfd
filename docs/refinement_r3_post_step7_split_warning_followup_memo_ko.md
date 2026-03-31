# R3 Post-Step7 Split Warning Follow-up Memo

## 1. 목적

R3 Step 7 이후 남아 있던 `entry_quality:split_health_warning`, `exit_management:split_health_warning`를
한 번 더 좁게 다듬으면서,

- 무엇이 split plumbing 문제였는지
- 무엇이 실제 slice 데이터 희소성 문제인지
- 현재 어디까지 해결됐는지

를 짧게 고정하기 위한 메모다.

## 2. 이번 follow-up에서 손댄 것

적용 파일:

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)

핵심 변경:

1. `build_holdout_bucket()`가 더 이상 단순 row-level stable ratio만 보지 않게 했다.
2. multi-group 데이터에서는 최소 1개 그룹이 실제 `holdout`으로 배정되게 했다.
3. `target_col`이 있을 때는 가능한 한 `양쪽 클래스가 모두 있는 그룹`을 holdout 후보로 우선 선택하게 했다.

즉 이전처럼 `BTCUSD/NAS100/XAUUSD`와 `RANGE/TREND/UNKNOWN/...`가 모두 우연히 `train`만 나오는 구조를 막았다.

## 3. 이전 상태

기존 Step 7 / latest preview 기준:

- timing / entry_quality / exit_management 모두
  - `symbol_holdout_bucket = train only`
  - `regime_holdout_bucket = train only`
- 그래서 holdout health에서
  - `empty_holdout_bucket`
  - 또는 holdout-related warning
가 surface 되었다.

## 4. 현재 상태

재생성 dataset:

- [semantic_v1_r3_holdout_20260326](c:\Users\bhs33\Desktop\project\cfd\data\datasets\semantic_v1_r3_holdout_20260326)

재학습 metrics:

- [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_holdout_20260326\metrics.json)

재확인 preview audit:

- [semantic_preview_audit_20260326_205215.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_205215.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)

현재 개선 결과:

### timing

- `symbol_holdout_health = healthy`
- `regime_holdout_health = healthy`
- split health 전체도 그대로 `healthy`

### entry_quality

- `symbol_holdout_health = healthy`
- `regime_holdout_health = healthy`
- 남은 warning은 holdout이 아니라
  - `preflight_regime:failing_slices=1/2`
  - 구체적으로 `TREND` test slice가 `0 only`

즉 남은 warning owner는 holdout plumbing이 아니라 `regime slice label sparsity`다.

### exit_management

- `symbol_holdout_health = healthy`
- `regime_holdout_health`는 `warning`
  - `holdout_minority_below_minimum:2<8`
- 즉 empty holdout은 사라졌고,
  이제는 holdout이 실제로 생겼지만 `UNKNOWN` regime의 positive minority가 너무 적은 상태다.

또한 기존 warning도 남아 있다.

- `symbol:failing_slices=2/3`
  - `NAS100` test slice: `0 only`
  - `XAUUSD` test slice: minority 1
- `setup_id:failing_slices=1/2`
  - `range_upper_reversal_sell`: minority 1

즉 남은 문제는 split 생성 버그보다 `slice label sparsity`다.

## 5. 해석

이번 follow-up으로 확인된 건 다음 두 가지다.

1. `holdout bucket 정책`은 실제로 개선 가치가 있었고,
   개선 후 `empty_holdout_bucket` 계열 문제는 구조적으로 해소됐다.
2. 지금 남아 있는 warning의 주원인은
   - `entry_quality`의 `TREND` slice single-class
   - `exit_management`의 symbol/setup minority 부족
   로, split plumbing보다 dataset/label 분포 자체에 더 가깝다.

## 6. 현재 판단

이제 다음 refinement는 `split plumbing`이 아니라 아래 owner를 보는 쪽이 맞다.

- `entry_quality`
  - target definition / slice policy / ambiguity policy
- `exit_management`
  - symbol/setup slice minimum rule
  - label density / aggregation policy

즉 이 메모 기준으로,
다음 warning 후속은 `holdout bucket 구조 수리`가 아니라
`slice sparsity 대응 정책` 트랙으로 넘어가는 것이 맞다.

## 7. 검증

테스트:

- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)

결과:

- `19 passed`

재학습 / 재감사:

- [metrics.json](c:\Users\bhs33\Desktop\project\cfd\models\semantic_v1_preview_r3_holdout_20260326\metrics.json)
- [semantic_preview_audit_20260326_205215.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_205215.json)

promotion gate:

- `shadow_compare_status = healthy`
- `promotion_gate.status = pass`
- warning은 여전히 남지만 성격이 더 좁혀졌다.
