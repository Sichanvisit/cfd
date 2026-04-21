# Teacher-Label State25 Step 9-E3 Pilot Baseline 상세 기준서

## 목적

Step 9-E3의 목적은 현재 labeled seed로
`실제로 학습이 되는지`를 가장 작고 안전한 baseline으로 확인하는 것이다.

이 단계는 최종 모델 단계가 아니다.

- 라벨 파이프라인이 학습 입력으로 쓸 수 있는지
- 현재 skew된 seed에서도 기본 분류가 가능한지
- 어떤 target은 아직 너무 이른지

를 보는 pilot 단계다.

## baseline 해석 원칙

- 현재 seed는 `25개 전체 완성용`은 아니다.
- 하지만 `pilot baseline`에는 충분하다.
- 따라서 E3에서는 25개 전체를 억지로 다 맞추려 하지 않는다.

이번 baseline은 두 축으로 나눈다.

1. `group_task`
   - target: `teacher_pattern_group`
   - 목적: 현재 seed 수준에서도 A/D/E 같은 큰 그룹 구분이 되는지 확인

2. `pattern_task`
   - target: `teacher_pattern_id`
   - 단, support가 충분한 pattern만 사용
   - 목적: 현재 seed에서 실제로 반복 관찰된 pattern을 구분할 수 있는지 확인

## feature pack 원칙

teacher label 자체는 입력으로 쓰지 않는다.

입력은 compact row의 기존 값 중
entry 시점과 micro/regime state에 해당하는 것만 사용한다.

대표 입력:

- `symbol`, `direction`
- `entry_stage`, `entry_setup_id`, `entry_wait_state`
- `regime_at_entry`, `entry_session_name`, `entry_weekday`, `regime_name`
- `entry_score`, `contra_score_at_entry`
- `entry_h1_context_score`, `entry_m1_trigger_score`
- `entry_topdown_align/conflict/seen_count`
- `entry_atr_ratio`, `entry_atr_threshold_mult`
- indicator/regime 값
- `micro_*` semantic/source 값
- completeness/fallback 관련 compact 품질 값

즉 label 컬럼과 close 이후 결과 컬럼은 제외한다.

## 모델 원칙

pilot baseline은 `sklearn logistic regression + balanced class weight`를 기본으로 한다.

이유:

- 의존성이 이미 존재한다.
- 작고 빠르다.
- 현재 2K 수준 seed에서도 안정적으로 돈다.
- class imbalance 대응이 쉽다.

비교 기준으로는 `DummyClassifier(most_frequent)`를 같이 돌린다.

## split 원칙

pilot 단계는 stratified random split을 쓴다.

- train 70%
- val 15%
- test 15%

단, stratify가 불가능한 경우에는 non-stratified fallback으로 간다.

현재 단계에서는 `rolling window 최종 split`보다
`학습 가능성 sanity check`가 먼저다.

## pattern task support 규칙

현재 seed에서 너무 적은 class까지 억지로 학습하지 않는다.

- `pattern_min_support = 5`
- support가 5 미만인 pattern은 이번 pattern_task에서 제외
- excluded pattern은 리포트에 따로 기록

## 핵심 출력

- seed summary bridge
- baseline ready 여부
- group_task split/metric/support/confusion
- pattern_task split/metric/support/confusion
- dummy baseline 대비 비교
- supported / excluded pattern ids

## 구현 owner

- [teacher_pattern_pilot_baseline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_pilot_baseline.py)
- [teacher_pattern_pilot_baseline_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_pilot_baseline_report.py)
- [test_teacher_pattern_pilot_baseline.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_teacher_pattern_pilot_baseline.py)

## 다음 단계 연결

이 단계가 닫히면 다음은 두 갈래다.

1. pilot baseline 결과로 `E4 top confusion pair tuning` 진입
2. 또는 labeled seed를 더 누적한 뒤 다시 E3 재실행
