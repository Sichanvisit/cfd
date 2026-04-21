# Barrier Bias Correction Checklist v1

## 목적

이 문서는 `Barrier coverage engineering` 다음 단계에서 무엇을 교정해야 하는지
실무 관점으로 고정하는 체크리스트다.

핵심 목표는 `usable coverage`를 무작정 더 늘리는 것이 아니다.
이미 살아난 coverage가 아래 축으로 과하게 기울어지는 편향을 줄이는 것이다.

- `avoided_loss` 편중
- `missed_profit / overblock / correct_wait / relief` 축 저활성
- `loss_avoided_r` 우위 cost bias
- `observe_only` 버킷 과대 정규화

즉 이 문서는 threshold를 느슨하게 만드는 문서가 아니라,
`label distribution + cost balance + drift resolution + unresolved skip policy`
를 정밀하게 다루는 문서다.

## 적용 전제

이 체크리스트는 아래가 이미 닫힌 뒤에 적용한다.

- `BR0~BR6` owner promotion complete
- `BCE0~BCE7` coverage / audit / wiring / readiness complete
- runtime/detail/live-row observability available
- barrier readiness blocker가 더 이상 wiring crash가 아님

현재 barrier 해석은 아래처럼 읽는다.

- `strict_rows`: compare/gate에 바로 사용할 수 있는 `high / medium` row
- `usable_rows`: baseline/diagnostic에는 쓰되 hard gate에는 바로 넣지 않는 `weak_usable` row
- `semantic_skip_share_ex_pre_context`: `max_positions` 같은 상위 policy skip을 뺀 뒤에도 남아 있는 unresolved share
- `pre_context_skip:max_positions_reached`: barrier 품질이 아니라 capacity policy 영역

## 운영 원칙

### 1. threshold를 먼저 낮추지 않는다

Barrier readiness가 `blocked_coverage`라고 해서 threshold를 먼저 낮추지 않는다.
먼저 확인해야 하는 것은 아래다.

- 왜 `avoided_loss`가 과대표집되는가
- 왜 `missed_profit / overblock / correct_wait / relief`가 약한가
- 왜 drift가 특정 action pair로 몰리는가

### 2. weak row를 gate에 바로 섞지 않는다

이 원칙은 유지한다.

- compare / gate = `strict_only`
- baseline = `strict + usable`
- diagnostics = `all rows with skip visibility`

Bias correction 과정에서 `weak_usable`이 늘어나도 hard gate를 오염시키지 않는다.

### 3. bias는 세 갈래로 분리해서 본다

- `label bias`
  - 특정 label만 과도하게 많이 찍히는가
- `cost bias`
  - `loss_avoided_r`가 `profit_missed_r`보다 구조적으로 더 크게 잡히는가
- `action normalization bias`
  - drift가 실제 철학 충돌이 아니라 coarse bucket 때문인가

## 변수 / 용어 설명

### `loss_avoided_r`

Barrier가 막았기 때문에 피했다고 해석되는 downside를 `R` 단위로 환산한 값이다.
값이 클수록 “막아서 손실을 많이 줄였다” 쪽이다.

### `profit_missed_r`

Barrier가 wait/block 쪽으로 작동했기 때문에 놓친 upside를 `R` 단위로 환산한 값이다.
값이 클수록 “기회를 많이 놓쳤다” 쪽이다.

### `wait_value_r`

즉시 진입보다 조금 기다렸을 때 개선된 entry timing의 가치를 `R` 단위로 본 값이다.
`correct_wait` 또는 `weak missed_profit` 판정 보조에 쓴다.

### `strict_rows`

`high / medium` confidence row 수다.
candidate compare / gate 같은 승격 판단에 바로 쓸 수 있는 row다.

### `usable_rows`

`weak_usable` row 수다.
baseline / diagnostics에는 쓰되 compare hard blocker에는 기본적으로 직접 섞지 않는다.

### `semantic_skip_share_ex_pre_context`

`max_positions_reached` 같은 pre-context skip을 뺀 뒤,
여전히 barrier가 설명하지 못한 unresolved row의 비율이다.

### `observe_only`

현재 barrier recommended action을 정규화할 때 쓰는 넓은 버킷이다.
이 안에 `soft wait`, `light block`, `neutral observe`가 같이 들어가면 drift 해석이 흐려진다.

## 1. Label Bias 점검

### 1-1. `avoided_loss` 점검

확인 항목:

- `avoided_loss` strict/usable 비율
- `counterfactual_cost_delta_r <= 0`인데 `avoided_loss`로 찍힌 row 수
- 작은 adverse move만 있었는데 `avoided_loss`로 흡수된 row 수
- `release_window_not_mature` 또는 low-magnitude 경계 row가 strict avoided로 승격되는 비율

조정 원칙:

- 작은 adverse 회피는 `strict avoided_loss`가 아니라 `weak_usable avoided_loss`
- `ambiguous_cost_balance` 경계 row는 strict avoided로 승격하지 않음
- timing improvement 중심이면 `correct_wait` 후보를 우선 검토

### 1-2. `missed_profit` 점검

Barrier bias 교정의 최우선 항목이다.

확인 항목:

- `missed_profit_strict_candidate_count`
- `missed_profit_weak_candidate_count`
- favorable move는 컸지만 ambiguous 또는 skip으로 남은 row 수
- partial horizon에서는 missed인데 full horizon 부족으로 strict에서 탈락한 row 수

운영 원칙:

- `missed_profit_strict`
- `missed_profit_weak`

로 반드시 분리한다.

활용:

- strict = compare/gate 가능
- weak = baseline/diagnostics 전용

### 1-3. `overblock` 점검

`overblock`은 단순 missed profit의 하위개념이 아니다.
핵심은 “차단 강도가 과했다”는 판단이다.

확인 항목:

- `overblock` strict/usable row 수
- favorable move 충분 + adverse 낮음 + strong barrier block이 있었던 row 수
- `missed_profit`와 `overblock` 경계 row 수

추천 보조 필드:

- `block_intensity_score`
- `overblock_margin_r`
- `barrier_release_delay_bars`

### 1-4. `correct_wait` 점검

Barrier가 모두 `avoided_loss`로만 읽히면 `correct_wait`가 사라진다.

확인 항목:

- `correct_wait` strict/usable 비율
- relief / re-entry가 실제 생긴 row 중 `correct_wait`로 간 비율
- timing improvement만 있었는데 avoided로 찍힌 row 수

### 1-5. `relief_success / relief_failure` 점검

Barrier가 진짜 동적 owner가 되려면 relief 축이 살아 있어야 한다.

확인 항목:

- relief strict/usable row 수
- `release_window_not_mature` 비율
- relief row 중 `observe_only`로 평평하게 정규화된 비율

## 2. Cost Bias 점검

### 2-1. `loss_avoided_r` vs `profit_missed_r`

확인 항목:

- mean/median `loss_avoided_r`
- mean/median `profit_missed_r`
- non-zero share
- strict vs usable 분포

조정 원칙:

- `profit_missed_r_partial` 검토
- short/mid horizon favorable move를 partial missed cost로 인정
- non-entry missed move와 delayed-entry missed move를 분리

### 2-2. `wait_value_r`

`wait_value_r`는 편향 완충 장치다.

확인 항목:

- high `wait_value_r` row의 strict/usable/skip 분포
- high `wait_value_r`인데 unresolved로 남은 비율
- `wait_value_r`와 `counterfactual_cost_delta_r` 상관

## 3. Drift / Action Normalization 점검

### 3-1. `observe_only` 버킷 분해

추천 세분화:

- `observe_only_soft`
- `wait_bias_soft`
- `block_bias_soft`
- `relief_watch`
- `relief_release_bias`

### 3-2. drift pair 재정의

추가로 봐야 할 pair:

- `wait_or_block -> wait_bias_soft`
- `wait_or_block -> block_bias_soft`
- `wait_or_block -> relief_watch`
- `observe_only -> wait_bias_soft`
- `observe_only -> block_bias_soft`

### 3-3. negative mismatch 분해

`negative_mismatch_rate`를 아래로 나눈다.

- `harmful_barrier_mismatch`
- `neutral_bucketization_mismatch`
- `insufficient_evidence_mismatch`

## 4. Wait-Family Overlay

Barrier bias correction 단계에서는 `correct_wait`를 억지로 넓히지 않고, `wait-family` 설명 계층을 함께 운영한다.

핵심 원칙:

- Barrier main label은 유지한다.
- `wait_outcome_family / wait_outcome_subtype`는 진단용 상위 버킷이다.
- 초기에는 `diagnostic/usable` 중심으로만 사용한다.

v1 초기 매핑:

- `missed_profit_leaning` -> `failed_wait / wait_but_missed_move`
- `zero_entry_gain_no_continuation` -> `failed_wait / wait_without_timing_edge`
- `small_continuation_avoided_loss` -> `neutral_wait / small_value_wait`

즉 wait-family는 `correct_wait` 대체품이 아니라, BCE 후반부의 bias 교정과 분포 해석을 위한 overlay로 본다.

참조:

- [current_wait_family_label_structure_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_wait_family_label_structure_v1_ko.md)

## 4-A. Manual Good-Wait Teacher Truth

`correct_wait`를 heuristic만으로 억지 확대하지 않고, 사람이 차트에서 직접 표기한 good-wait truth를 별도 기준으로 운영한다.

초기 공식 라벨:

- `good_wait_better_entry`
- `good_wait_protective_exit`
- `good_wait_reversal_escape`
- `neutral_wait_small_value`
- `bad_wait_missed_move`
- `bad_wait_no_timing_edge`

운영 원칙:

- 초기 truth는 박스장 표본부터 시작
- Barrier main label을 덮어쓰지 않음
- compare/gate에는 바로 넣지 않음
- heuristic barrier/wait-family와 manual truth 차이를 bias 교정 기준으로 삼음

참고:

- [current_manual_wait_teacher_truth_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_wait_teacher_truth_spec_v1_ko.md)
- [current_manual_trade_episode_truth_model_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_model_v1_ko.md)
- [current_manual_trade_episode_truth_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_trade_episode_truth_implementation_roadmap_ko.md)

## 4. Skip / Unresolved 교정

### 4-1. reducible skip

이건 줄여야 한다.

- parsing / schema mismatch
- future bar stale
- anchor price missing
- reference unit missing
- known replay reconstruction failure

### 4-2. irreducible skip

이건 억지로 0으로 만들지 않는다.

- true `insufficient_future_bars`
- true `release_window_not_mature`
- true `side_conflict_unresolved`
- true `ambiguous_cost_balance`
- very low magnitude

### 4-3. pre-context policy skip

`pre_context_skip:max_positions_reached`는 barrier semantic quality가 아니라
capacity policy 영역으로 본다.

이 항목은 barrier 분모에서 계속 제외한다.
다만 이 축은 나중에 전체 `07` 정리 때 별도 policy audit으로 포함한다.

## 5. 리포트 표면 체크리스트

- label distribution report
- cost balance report
- weak conversion report
- drift decomposition report
- unresolved skip report
- readiness sensitivity report

## 6. 실행 순서

1. `missed_profit_strict / missed_profit_weak` 분리
2. `observe_only` 버킷 분해
3. ambiguous-cost weak 승격 가능 row 추출
4. `reducible / irreducible skip` 리포트 추가
5. action-family refinement 후 drift 재산출
6. bias correction 후 label distribution / cost balance / readiness 재평가
7. threshold sensitivity는 마지막에만 검토

## 참조 문서

- [current_barrier_owner_promotion_spec_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_owner_promotion_spec_v1_ko.md)
- [current_barrier_coverage_engineering_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_design_ko.md)
- [current_barrier_coverage_engineering_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_coverage_engineering_implementation_roadmap_ko.md)
- [current_barrier_bias_correction_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_barrier_bias_correction_implementation_roadmap_ko.md)
- [current_manual_vs_heuristic_comparison_report_template_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_manual_vs_heuristic_comparison_report_template_v1_ko.md)

## Manual Answer-Key Usage Addendum

The current `manual_wait_teacher` corpus should be treated as an answer key above the
heuristic barrier / wait-family layer.

Use it first for:

- calibration
- bias-correction review
- mismatch casebook building

Do not use it first for:

- mandatory replay matching
- direct baseline/candidate learning ingestion

Required next artifact:

- a `manual vs heuristic comparison report`
