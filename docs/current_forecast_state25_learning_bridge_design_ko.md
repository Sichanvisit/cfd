# Forecast-State25 Learning Bridge Design

## 2026-04-04 Reinforcement

### Coverage Engineering Clarification

Forecast rollout is currently blocked less by architecture and more by outcome coverage.
The bridge/report layer should explicitly track:

- `full_outcome_eligible_rows`
- `partial_outcome_eligible_rows`
- `insufficient_future_bars_rows`
- transition-valid vs management-valid split
- top skip / censor reasons

Rule of thumb:

- `full_outcome_eligible`: usable for strict evaluation
- `partial_outcome_eligible`: usable for diagnostics and weak auxiliary analysis
- `insufficient_future_bars`: not yet decision-grade, but must stay visible in coverage dashboards

### Transition First Principle

When forecast coverage is sparse, `transition` should be stabilized before `management`.
`management` may remain shadow/diagnostic longer if transition coverage matures first.

### Dual Surface Rule

- flat fields: operational observability and dashboard filtering
- nested bridge payload: replay reconstruction and future schema-safe detail

Flat forecast surfaces should remain deterministic summaries derived from the nested bridge payload.

### Rollout End-State

The intended promotion chain is:

`runtime -> replay -> seed -> baseline -> candidate -> log_only -> canary -> bounded_live`

`log_only` is therefore an evaluation milestone, not the final operational destination.

### Coverage Dashboard Requirement

Forecast should now be read through a coverage dashboard, not only a bridge report.

Minimum required surfaces:

- `total_anchor_rows`
- `full_outcome_eligible_rows`
- `partial_outcome_eligible_rows`
- `insufficient_future_bars_rows`
- `transition_valid_rows`
- `management_valid_rows`
- top skip / censor reasons

### Partial Outcome Usage Rule

`partial_outcome_eligible` is not a failed row.
It is a weaker row with narrower usage.

- strict evaluation: `full_outcome_eligible`
- weak auxiliary / diagnostics: `partial_outcome_eligible`
- visibility only: `insufficient_future_bars`

### Counterfactual Overlay Audit

`forecast_state25` log-only overlay should later be audited against actual execution.

Minimum counterfactual questions:

- forecast said `wait_bias`, actual engine entered: what changed in adverse/favorable path?
- forecast said `management_bias`, actual engine held: was giveback improved or worsened?

## FSB0 Scope Freeze

- `state25`는 scene owner로 유지한다.
- `forecast`는 branch owner로 유지한다.
- `wait_quality / economic_target`은 outcome owner로 유지한다.
- runtime direct-use field는 `state25_runtime_hint_v1`, `forecast_runtime_summary_v1`, `entry_wait_exit_bridge_v1`로 고정한다.
- replay/learning-only field는 closed-history teacher final label, future outcome label, wait-quality/economic target final label로 고정한다.
- no-leakage 원칙: closed-history final label과 future outcome label은 runtime feature로 직접 쓰지 않는다.

작성일: 2026-04-03 (KST)

## 1. 목적

이 문서는 현재 `forecast` 층과 `state25` 학습 루프를 직접 연결하기 위한 상세 설계다.

지금 구조는 크게 두 갈래로 나뉘어 있다.

- runtime 판단축
  - `position / response / state / evidence / belief / barrier`
  - `forecast_features_v1`
  - `transition_forecast_v1`
  - `trade_management_forecast_v1`
  - `forecast_gap_metrics_v1`
  - `observe / confirm / action / consumer`
- learning 판단축
  - `teacher_pattern_*`
  - `state25`
  - `wait_quality`
  - `economic_target`
  - `candidate retrain / compare / promote`

지금까지는 두 축이 나란히 존재했지만, `forecast`가 `state25`를 직접 학습 재료로 쓰거나 `state25`가 `forecast`의 품질을 직접 재평가하는 구조는 아니다.

이 브리지는 그 사이를 잇는다.

한 줄 목적:

`state25를 장면 해석 owner로, forecast를 미래 전개 owner로, wait/economic outcome을 결과 owner로 묶어서 더 좋은 진입/기다림/청산을 계속 학습하는 공통 기반을 만든다.`

## 2. 왜 지금 필요한가

사용자 의도는 이미 분명하다.

- 진입은 단순 score 누적이 아니라 `position / energy / state / forecast`로 본다.
- 기다림은 단순 hold가 아니라 `좋은 기다림 / 나쁜 기다림`으로 구분하고 싶다.
- 청산도 `계속 들고 가는 게 맞았는지 / 빨리 잘라야 했는지 / 다시 들어가는 게 맞았는지`를 더 잘 배우고 싶다.

그런데 현재는 다음 gap이 남아 있다.

1. `forecast`는 runtime에서 쓰이지만 `state25` 학습 루프와 직접 연결되지 않는다.
2. `state25`는 학습 루프를 갖고 있지만 `forecast transition/management` 품질을 직접 보조하지 않는다.
3. `wait_quality`와 `economic_target`은 생겼지만 `forecast-state25 scene` 단위로 묶인 재평가 owner가 없다.

즉 현재 구조는 `잘 보는 층`과 `잘 배우는 층`이 분리되어 있다.

이번 브리지의 목적은 `runtime에서 본 scene -> forecast가 말한 미래 -> 실제 결과 -> 다음 학습 seed`를 하나의 체인으로 고정하는 것이다.

## 3. 현재 구조 요약

### 3-1. forecast 쪽

생성 경로:

- [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)
- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)
- [observe_confirm_router.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/observe_confirm_router.py)

현재 역할:

- `forecast_features_v1`: semantic input bundle
- `transition_forecast_v1`: confirm / reversal / continuation / false break
- `trade_management_forecast_v1`: continue / fail / tp1 / recover / reentry
- `forecast_gap_metrics_v1`: branch 간 차이 요약
- `forecast_effective_policy_v1`: downstream assist wrapper

### 3-2. state25 쪽

학습 경로:

- [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py)
- [teacher_pattern_experiment_seed.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_experiment_seed.py)
- [teacher_pattern_pilot_baseline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_pilot_baseline.py)
- [teacher_pattern_candidate_pipeline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_candidate_pipeline.py)

현재 역할:

- `teacher_pattern_id / group / secondary`
- `entry / wait / exit bias`
- `transition risk`
- `wait_quality`
- `economic_target`
- `candidate retrain / compare / gate`

### 3-3. 지금 없는 것

- `forecast`와 `state25`를 같은 row owner로 묶는 bridge
- `forecast가 맞았는지`를 `state25 scene` 단위로 다시 평가하는 bridge
- `forecast-state25 joint seed`를 baseline/candidate에 올리는 bridge

## 4. 설계 원칙

### 4-1. 역할 분리 유지

- `state25`는 scene 해석 owner
- `forecast`는 미래 전개 owner
- `wait_quality / economic_target`은 사후 결과 owner

이 브리지는 역할을 섞는 것이 아니라 연결만 한다.

### 4-2. leakage 금지

가장 중요하다.

runtime에서 바로 쓸 수 있는 것은:

- 현재 시점의 semantic fields
- 현재 시점에서 계산 가능한 compact scene hint
- 현재 시점에서 계산 가능한 forecast

runtime에서 바로 쓰면 안 되는 것은:

- closed-history teacher label 결과값 자체
- 미래 bar를 보고 만든 outcome label
- 다음 trade 결과를 보고 만든 wait/economic label

즉 `teacher_pattern_id`의 closed-history 확정값을 runtime input feature로 바로 쓰면 안 된다.

허용되는 형태는 아래 둘 중 하나다.

1. 현재 시점에서도 계산 가능한 `state25_runtime_hint_v1`
2. 나중에 충분한 seed가 쌓여서 만든 `state25 predictor output`

### 4-3. dual-write 우선

처음부터 live policy를 바꾸지 않는다.

순서:

1. runtime bridge 기록
2. replay / outcome bridge
3. seed enrichment
4. baseline auxiliary task
5. candidate compare
6. log_only live overlay

### 4-4. entry / wait / exit를 함께 본다

forecast를 진입 전용으로만 쓰지 않는다.

- entry: 지금 들어가도 되는가
- wait: 지금 기다리는 게 유리한가
- exit/management: 계속 들고 가는 게 유리한가

를 함께 묶는다.

## 5. 목표 구조

```text
semantic runtime inputs
-> forecast_features_v1
-> forecast_state25_runtime_bridge_v1
-> transition_forecast_v1 / trade_management_forecast_v1 / forecast_gap_metrics_v1
-> observe / confirm / action / consumer
-> replay / outcome / wait_quality / economic_target
-> forecast_state25_learning_seed_v1
-> baseline / candidate / compare / gate
-> execution log_only / canary / bounded_live
```

핵심은 새로 추가될 두 개의 bridge다.

- `forecast_state25_runtime_bridge_v1`
- `forecast_state25_learning_seed_v1`

## 6. 새 contract 설계

### 6-1. `forecast_state25_runtime_bridge_v1`

역할:

- runtime row에서 `state25 scene 해석`과 `forecast branch 해석`을 같이 담는 중간 contract

권장 필드:

- `contract_version`
- `scene_source`
- `state25_runtime_hint_v1`
- `forecast_runtime_summary_v1`
- `entry_wait_exit_bridge_v1`
- `log_only_overlay_candidates_v1`

#### `state25_runtime_hint_v1`

closed-history 확정 label이 아니라 현재 시점에 계산 가능한 hint만 담는다.

권장 필드:

- `scene_family`
- `scene_group_hint`
- `candidate_pattern_ids`
- `entry_bias_hint`
- `wait_bias_hint`
- `exit_bias_hint`
- `transition_risk_hint`
- `confidence`
- `reason_summary`

#### `forecast_runtime_summary_v1`

현재 runtime forecast를 downstream이 다시 읽기 쉽게 요약한다.

권장 필드:

- `confirm_side`
- `confirm_score`
- `false_break_score`
- `continuation_score`
- `fail_now_score`
- `wait_confirm_gap`
- `hold_exit_gap`
- `same_side_flip_gap`
- `belief_barrier_tension_gap`
- `decision_hint`

#### `entry_wait_exit_bridge_v1`

실무 질문을 직접 담는 요약층이다.

- `entry_quality_hint`
- `wait_quality_hint`
- `management_quality_hint`
- `prefer_entry_now`
- `prefer_wait_now`
- `prefer_hold_if_entered`
- `prefer_fast_cut_if_entered`

### 6-2. `forecast_state25_outcome_bridge_v1`

역할:

- runtime에서 기록된 bridge를 replay / outcome 결과와 묶는 사후 평가 contract

권장 필드:

- `runtime_scene_key`
- `state25_runtime_hint_v1`
- `transition_outcome_labels_v1`
- `trade_management_outcome_labels_v1`
- `entry_wait_quality_label`
- `economic_target_summary`
- `bridge_quality_status`

### 6-3. `forecast_state25_learning_seed_v1`

역할:

- baseline/candidate 학습용 seed contract

권장 필드:

- `state25_scene_family`
- `state25_group_hint`
- `state25_candidate_pattern_ids`
- `forecast_confirm_side`
- `forecast_decision_hint`
- `forecast_wait_confirm_gap`
- `forecast_hold_exit_gap`
- `forecast_same_side_flip_gap`
- `forecast_belief_barrier_tension_gap`
- `transition_label_bundle`
- `management_label_bundle`
- `wait_quality_label`
- `economic_total_label`
- `economic_score`

## 7. 어떤 값이 runtime에서 직접 쓰여야 하나

runtime direct-use 대상:

- `state25_runtime_hint_v1`
- `forecast_runtime_summary_v1`
- `entry_wait_exit_bridge_v1`

runtime direct-use 금지:

- `teacher_pattern_id` closed-history final label
- `transition_outcome_labels_v1`
- `trade_management_outcome_labels_v1`
- `entry_wait_quality_label`
- `economic_total_label`

즉 runtime은 `hint`, learning은 `outcome`을 쓴다.

## 8. 학습 측 연결 방식

### 8-1. baseline auxiliary target

`pattern/group`만 학습하지 말고 아래 보조 과제를 붙인다.

- `forecast_transition_task`
- `forecast_management_task`
- `forecast_wait_quality_task`
- `forecast_economic_task`

### 8-2. compare 지표

후보 compare에서 아래를 같이 본다.

- pattern/group macro F1
- transition auxiliary quality
- management auxiliary quality
- wait-quality consistency
- economic utility delta
- symbol별 skew / regression

### 8-3. execution 연결

처음에는 `log_only`만 허용한다.

- threshold relief / raise
- size multiplier hint
- wait bias release / lock
- hold vs fast-cut hint

이 값은 실제 live 적용 전에 trace로만 남긴다.

## 9. 왜 이게 더 좋은 진입/기다림/청산의 기반이 되나

### 더 좋은 진입

- 지금 장면이 어떤 state25 family인지 본다
- 그 장면에서 confirm vs false break vs continuation을 본다
- 이후 실제 결과와 비교해 어떤 장면에서 진입이 좋았는지 다시 배운다

### 더 좋은 기다림

- wait가 단순 hold가 아니라
  - 좋은 재진입 대기였는지
  - 손실 회피 대기였는지
  - 기회를 놓친 나쁜 대기였는지
를 state25 scene과 함께 기록한다

### 더 좋은 청산

- continue / fail / recover / reentry 쪽 예측을 실제 결과와 economic target으로 다시 평가한다

즉 이 브리지는 entry/wait/exit를 따로 보지 않고 같은 scene 체인으로 묶는다.

## 10. 구현 우선순위

1. `runtime bridge`부터 붙인다
2. `replay/outcome bridge`를 붙인다
3. `closed-history enrichment`로 seed에 올린다
4. `baseline auxiliary task`로 학습에 연결한다
5. `candidate compare`에 넣는다
6. `log_only live overlay`를 연다

## 11. 완료 기준

아래가 보이면 이 브리지 축이 기본 완성이다.

- runtime status / decision row에 `forecast_state25_runtime_bridge_v1`가 기록됨
- replay report에 `forecast_state25_outcome_bridge_v1`가 기록됨
- experiment seed에 `forecast_state25_learning_seed_v1` 계열 필드가 붙음
- baseline report에 forecast-state25 auxiliary task가 보임
- candidate compare에서 이 축 regression / gain이 따로 보임
- live는 `log_only`에서만 시작함

## 12. 이번 설계의 결론

이번 브리지는 `forecast를 state25 안에 넣는 것`이 아니다.

정확히는:

- `state25`는 장면 해석
- `forecast`는 미래 전개
- `wait/economic outcome`은 결과 평가

이 세 축을 같은 seed 체인으로 묶는 설계다.

그래야 지금 만든 state25가 단순 라벨러가 아니라, `계속 더 나은 진입/기다림/청산을 학습하는 기반 엔진`으로 올라갈 수 있다.
