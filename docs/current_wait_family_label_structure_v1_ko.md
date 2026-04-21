# Wait-Family Label Structure v1

## 목적

이 문서는 `Barrier main label`을 유지한 채, `wait-family`라는 설명 계층을 추가하는 v1 구조를 정리한다.

핵심 원칙은 아래와 같다.

- `correct_wait`를 억지로 넓히지 않는다.
- Barrier의 핵심 라벨은 그대로 둔다.
- 그 위에 `wait_outcome_family / wait_outcome_subtype`를 추가해서 기다림의 성격을 별도로 쌓는다.
- v1에서는 `compare/gate`가 아니라 `diagnostic/usable` 중심으로 운영한다.

## Barrier main label과의 관계

Barrier main label은 핵심 판정이다.

- `avoided_loss`
- `missed_profit`
- `correct_wait`
- `overblock`
- `relief_success`
- `relief_failure`

wait-family는 이 메인 판정을 대체하지 않는다.

- Barrier main label = 핵심 outcome 판정
- wait-family = 기다림의 성격 설명

즉 같은 row에서

- `barrier_outcome_label = avoided_loss`
- `wait_outcome_family = neutral_wait`
- `wait_outcome_subtype = small_value_wait`

처럼 함께 붙을 수 있다.

## 필드

v1 필드는 아래를 사용한다.

- `wait_outcome_family`
- `wait_outcome_subtype`
- `wait_outcome_confidence`
- `wait_outcome_usage_bucket`
- `wait_outcome_reason_summary`
- `wait_outcome_supporting_metrics`
- `wait_outcome_revisit_flag`
- `wait_outcome_v1`

`wait_outcome_v1`는 nested 원본 payload이고, 나머지는 운영 관측용 flat field다.

## Family 구조

### 1. `timing_improvement`

기다림이 더 좋은 진입 위치나 타이밍 개선을 만든 경우다.

대표 subtype:

- `correct_wait_strict`
- `better_entry_after_wait`

### 2. `protective_exit`

기다림 뒤 continuation이 있었고, 이후 보호적 exit/reduce가 유효했던 경우다.

대표 subtype:

- `profitable_wait_then_exit`
- `wait_then_reduce_to_protect`

### 3. `reversal_escape`

기다림 중 반대 힘이 커졌고, wait 이후 탈출이 유효했던 경우다.

대표 subtype:

- `wait_then_escape_on_reversal`
- `thesis_break_escape_after_wait`
- `barrier_relief_fail_escape`

### 4. `neutral_wait`

기다림이 아주 큰 개선은 아니었지만 그렇다고 명백한 손해도 아니었던 경우다.

대표 subtype:

- `no_clear_edge_wait`
- `small_value_wait`

### 5. `failed_wait`

기다렸지만 timing edge를 만들지 못했거나 기회를 놓친 경우다.

대표 subtype:

- `wait_but_missed_move`
- `wait_without_timing_edge`

## v1 초기 군집 매핑

현재 BCE에서 확인된 대표 군집은 아래처럼 매핑한다.

### `missed_profit_leaning`

- Barrier main label: `missed_profit`
- wait-family:
  - `wait_outcome_family = failed_wait`
  - `wait_outcome_subtype = wait_but_missed_move`
  - `wait_outcome_usage_bucket = usable`

### `zero_entry_gain_no_continuation`

- Barrier main label: 유지
- wait-family:
  - `wait_outcome_family = failed_wait`
  - `wait_outcome_subtype = wait_without_timing_edge`
  - `wait_outcome_usage_bucket = diagnostic`

### `small_continuation_avoided_loss`

- Barrier main label: `avoided_loss` 유지
- wait-family:
  - `wait_outcome_family = neutral_wait`
  - `wait_outcome_subtype = small_value_wait`
  - `wait_outcome_usage_bucket = diagnostic`

초기 v1에서는 이 군집을 `protective_exit`로 올리지 않는다. `better_entry_gain_6 = 0`이고, continuation/wait value는 작으며, `loss_avoided_r`가 더 크게 우세한 패턴이기 때문이다.

## usage bucket 원칙

v1에서는 아래 원칙으로 쓴다.

- `timing_improvement > correct_wait_strict` -> `strict`
- `failed_wait > wait_but_missed_move` -> `usable`
- `failed_wait > wait_without_timing_edge` -> `diagnostic`
- `neutral_wait > small_value_wait` -> `diagnostic`
- `protective_exit / reversal_escape`는 초기엔 `usable` 또는 `diagnostic`

즉 wait-family는 초기에 `compare/gate`보다는 `diagnostic/usable` 중심으로 운영한다.

## supporting metrics

`wait_outcome_supporting_metrics`에는 아래 값을 남긴다.

- `better_entry_gain_6`
- `later_continuation_f_6`
- `loss_avoided_r`
- `profit_missed_r`
- `wait_value_r`
- `release_f_6`
- `release_a_6`
- `counterfactual_cost_delta_r`

이 값들은 wait-family subtype이 어떤 이유로 붙었는지 replay/report에서 다시 읽기 위한 표면이다.

## v1 운영 해석

현재 wait-family는 `Barrier bias correction`의 후속 진단 계층이다.

- `correct_wait`는 계속 좁고 엄격하게 유지한다.
- 대신 `wait-family`로 missed / no-edge / small-value wait를 분리한다.
- 이 구조로 표본을 쌓은 뒤에, 나중에 `protective_exit`나 `reversal_escape`를 별도 auxiliary surface로 승격할지 검토한다.

## Manual Teacher Truth Layer

wait-family 위에는 `manual wait teacher truth`를 별도 계층으로 둘 수 있다.

이 truth layer는 사람이 차트에서 직접 표시한:

- 옳은 진입
- 옳은 청산
- 기다림의 성격

을 기반으로 한다.

초기 수동 teacher label은 아래를 사용한다.

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

이 수동 truth는 heuristic barrier label을 덮어쓰지 않고, 나중에 bias correction 비교 기준으로 사용한다.

## 참조

- [current_barrier_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_owner_promotion_spec_v1_ko.md)
- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_bias_correction_checklist_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_checklist_v1_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)
- [current_manual_wait_teacher_truth_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_wait_teacher_truth_spec_v1_ko.md)
- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)

## Episode-First Placement

wait-family and manual wait truth should now be placed inside a larger `trade episode` truth model.

Adopted rule:

- wait-family = heuristic diagnostic layer
- manual wait teacher = first operational manual truth channel
- episode = shared container for entry / wait / exit truth

This keeps wait-first operations stable while allowing entry/exit truth to grow later.

## Manual Answer-Key And Comparison Placement

The current `manual_wait_teacher` corpus should be read as an answer key above the
heuristic wait-family layer.

Operational interpretation:

- wait-family = heuristic interpretation
- manual wait teacher = human truth / standalone teacher corpus
- manual-vs-heuristic comparison report = calibration and correction surface

This means the next primary artifact is not a replay matcher.
It is a `manual vs heuristic comparison report` that asks:

- where did wait-family agree with manual truth?
- where did it over-neutralize a good wait?
- where did it miss a better-entry wait?
- where did it misread protective-exit or reversal-escape intent?

Reference:

- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)
