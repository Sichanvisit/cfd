# State Strength / Local Structure 해석 축 상세 계획

## 1. 문서 목적

이 문서는 단순히 기능 하나를 추가하자는 계획서가 아니다.

지금까지 왜 시스템이 이 지점까지 흘러왔는지,
현재 무엇이 이미 구축되어 있는지,
로그와 스크린샷 대조를 통해 어떤 결론에 도달했는지,
그리고 다음 구현 축이 왜 `state strength + local structure` 쪽이어야 하는지를
조언 요청용 기준 문서로 정리한다.

즉 이 문서의 목적은 다음 네 가지다.

1. 현재 문제를 "못 본다"가 아니라 "보지만 해석 우세가 어긋난다"로 재정의한다.
2. 이미 구축된 R0~R6-A, CA2, canonical surface, should-have-done, session split을 한 번에 묶는다.
3. 로그와 스크린샷 대조 결과를 근거로 다음 구현 축을 `state dominance`와 `few-candle local structure`로 고정한다.
4. 이후 외부 조언이나 내부 구현 판단이 추상론으로 흐르지 않게 기준 언어를 만든다.

## 2. 왜 여기까지 흘러왔는가

초기 해석 축은 아래와 같은 위치 기반 판단에 크게 의존했다.

- `box_state`
- `bb_state`
- 상단/하단 위치
- 상단 reject / 하단 rebound

이 구조는 조용한 장, 박스 회귀가 잘 먹히는 장, 상단/하단 의미가 비교적 단순한 구간에서는 꽤 잘 맞았다.

하지만 최근 로그와 스크린샷을 함께 보면 문제의 중심은 다음으로 이동했다.

1. 같은 `UPPER`, 같은 `UPPER_EDGE`라도 실제 의미가 다르다.
   - 진짜 상단 되밀림일 수 있다.
   - 강한 breakout hold일 수 있다.
   - 유동성 주도 continuation일 수 있다.
2. 시스템은 방향을 못 보는 게 아니라, 방향을 본 뒤 최종적으로 `wait/reduce/block` 쪽으로 소비하는 경우가 많다.
3. 세션 차이는 분명 참고가 되지만, 실제 체감 오판의 핵심은 세션 자체보다 "최근 몇 개 캔들이 어떤 구조를 만들고 있었는가"에 더 가깝다.
4. state, forecast, belief, barrier, state25가 이미 많이 붙어 있는데도, 이들이 아직 방향 우세를 선언하기보다 caution/wait 층으로 더 많이 작동한다.

즉 지금 문제는 입력 재료 부족이 아니라 **강세/약세 상태의 세기를 분해하고, 최근 몇 개 캔들의 구조와 결합해 우세 해석을 정하는 공용 해석층이 부족한 것**이다.

## 3. 현재까지 구축된 상태

관련 기준 문서:

- [current_session_aware_direction_continuation_learning_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_session_aware_direction_continuation_learning_detailed_plan_ko.md)
- [current_session_aware_direction_continuation_learning_execution_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_session_aware_direction_continuation_learning_execution_roadmap_ko.md)
- [current_r0_ca2_stability_maintenance_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r0_ca2_stability_maintenance_detailed_plan_ko.md)
- [current_r1_ca2_session_split_readonly_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r1_ca2_session_split_readonly_detailed_plan_ko.md)
- [current_r2_minimum_annotation_contract_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r2_minimum_annotation_contract_detailed_plan_ko.md)
- [current_r3_should_have_done_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r3_should_have_done_detailed_plan_ko.md)
- [current_r4_canonical_surface_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r4_canonical_surface_detailed_plan_ko.md)
- [current_r5_session_aware_annotation_accuracy_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r5_session_aware_annotation_accuracy_detailed_plan_ko.md)
- [current_r6a_session_bias_shadow_only_detailed_plan_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_r6a_session_bias_shadow_only_detailed_plan_ko.md)

현재까지 이미 구축된 것은 아래와 같다.

### 3-1. 배선과 안정성

- `current-cycle overlay -> execution` 배선
- `execution_diff_*` surface
- `row <-> flow history` 동기화 축
- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`

최신 snapshot 기준:

- [runtime_status.detail.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.detail.json)
- `generated_at = 2026-04-15T10:29:39+09:00`
- `execution_diff_surface_count = 3`
- `flow_sync_match_count = 3`
- `primary_correct_rate = 0.5723`
- `ca2_r0_stability_summary_v1.status = HOLD`
- `ca2_r0_stability_summary_v1.status_reasons = primary_measured_flat, resolved_observation_flat`

즉 기본 배선과 surface는 살아 있다.

### 3-2. 세션 분해

- [ca2_session_split_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/ca2_session_split_audit_latest.json)

최신 요약:

- `ASIA = 103 / 0.5437`
- `US = 56 / 0.625`
- `EU = 0`
- `EU_US_OVERLAP = 0`
- `session_difference_significance = NOT_SIGNIFICANT`
- `max_gap_pct_points = 8.13`

즉 세션 차이는 읽히지만, 현재 snapshot만으로는 "세션 bias를 강하게 써도 된다" 수준까지는 아니다.

### 3-3. should-have-done 후보 축

- [should_have_done_candidate_summary_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/should_have_done_candidate_summary_latest.json)

최신 요약:

- `candidate_count = 6`
- `AUTO_HIGH = 1`
- `AUTO_MEDIUM = 5`
- `NAS100 = 1`
- `BTCUSD = 1`
- `XAUUSD = 4`

즉 "이때는 이렇게 했어야 했다"는 review 후보는 실제로 쌓이기 시작했다.

### 3-4. canonical surface

- [canonical_surface_summary_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/canonical_surface_summary_latest.json)

최신 요약:

- runtime surface: `BUY_WATCH = 3`
- execution surface: `WAIT = 1 / BUY_EXECUTION = 1 / SELL_EXECUTION = 1`
- alignment: `MATCH = 1 / DIVERGED = 1 / WAITING = 1`

즉 시스템은 세 심볼 모두 runtime에선 `BUY_WATCH`로 읽는 구간이 있는데, execution은 아직 완전히 따라오지 않는다.

### 3-5. session bias shadow

- [session_bias_shadow_report_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/session_bias_shadow_report_latest.json)

최신 요약:

- `status = READY`
- `mode = shadow_only`
- `candidate_state_count_summary = NO_SESSION_EDGE 3`
- `effect_count_summary = KEEP_NEUTRAL 3`

즉 세션 bias는 아직 observe-only이며, 지금 문제의 중심이 세션 자체는 아니라는 점을 다시 확인시켜 준다.

### 3-6. state25

- [active_candidate_state.json](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/active_candidate_state.json)

현재 상태:

- `current_rollout_phase = log_only`
- `current_binding_mode = log_only`

즉 state25는 여전히 live apply 이전 단계다.

## 4. 로그와 스크린샷을 통해 확인한 사실

## 4-1. NAS 최신 row는 강세를 이미 보고 있다

기준:

- [runtime_status.detail.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.detail.json)

최신 NAS 핵심 값:

- `previous_box_break_state = BREAKOUT_HELD`
- `previous_box_relation = ABOVE`
- `htf_alignment_state = WITH_HTF`
- `directional_continuation_overlay_direction = UP`
- `directional_continuation_overlay_score = 0.8089`
- `canonical_runtime_surface_name_v1 = BUY_WATCH`

즉 NAS는 이미 `상승 지속 우세`를 읽고 있다.

## 4-2. 그런데 execution과 하위 consumer는 여전히 caution/sell 쪽으로 기운다

같은 NAS 최신 row:

- `canonical_execution_surface_name_v1 = WAIT`
- `consumer_check_side = SELL`
- `consumer_check_reason = upper_reject_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `forecast_state25_candidate_wait_bias_action = reinforce_wait_bias`
- `belief_candidate_recommended_family = reduce_alert`
- `barrier_candidate_recommended_family = wait_bias`

이건 아주 중요하다.

문제는 시스템이 강세를 못 보는 게 아니다.

문제는 시스템이 강세를 본 뒤에도

- `upper reject`
- `wait bias`
- `reduce alert`
- `energy soft block`

같은 caution 계층이 더 우세하게 작동한다는 점이다.

즉 현재 병목은 `recognition failure`보다는 **dominance resolution failure**에 가깝다.

## 4-3. 최근 NAS decision 로그도 같은 결론을 지지한다

기준:

- [entry_decisions.detail.jsonl](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.detail.jsonl)

`2026-04-15 10:00:00 ~ 10:30:00 KST` NAS 요약:

- 총 `15건`
- `leg_direction = UP`: `15 / 15`
- `breakout_candidate_direction = UP`: `13 / 15`
- `consumer_check_side = SELL`: `15 / 15`
- `consumer_check_reason = upper_reject_confirm`: `10 / 15`
- `observe_reason = directional_conflict_watch`: `4 / 15`
- `forecast_state25_candidate_wait_bias_action = reinforce_wait_bias`: `15 / 15`
- `belief_candidate_recommended_family = reduce_alert`: `15 / 15`
- `barrier_candidate_recommended_family = relief_watch`: `11 / 15`
- `barrier_candidate_recommended_family = wait_bias`: `2 / 15`

이 분포는 아주 선명하다.

- 구조는 거의 계속 `UP`
- breakout 후보도 대부분 `UP`
- 그런데 하위 consumer는 거의 항상 `SELL`
- state/forecast/belief/barrier는 방향 승격보다 caution/reduce/wait 쪽으로 소비됨

## 4-4. 사용자 스크린샷 대조를 통해 확인한 것

사용자 스크린샷과 timebox review를 통해 반복해서 확인된 사실은 아래와 같다.

1. NAS에서 같은 상승 지속 구조 안에서도 상단에 닿는 순간 `SELL_WATCH`, `SELL_WAIT`, `upper_reject` 계열이 과하게 튄다.
2. XAU에서는 구간에 따라 실제 하락 continuation이 더 우세한데도 BUY continuation과 SELL continuation이 혼합되어 흔들린다.
3. BTC는 조용한 상승/되밀림 구조에서 `WAIT/SELL_PROBE` 쪽으로 오래 끌리다가 진짜 전환 때도 우세 해석이 늦는다.

이 공통점은 세션보다 다음과 더 관련이 있다.

- 최근 3~9개 캔들의 구조
- breakout 유지 여부
- retest 품질
- wick/body drive
- state가 caution으로 소비되는지, direction dominance로 소비되는지

## 5. 우리가 도달한 생각

### 5-1. 세션은 보조 bias이지 핵심 판별자가 아니다

R1이 말해준 것은 세션 차이가 "조금은 있다"는 것이지, 현재 문제의 중심이 세션 그 자체라는 뜻은 아니다.

오히려 최근 NAS 사례는 아래를 보여준다.

- 같은 ASIA 구간 안에서도 local structure에 따라 continuation과 reversal이 갈린다.
- 세션을 `BUY/SELL`로 직접 쓰면 바로 하드코딩으로 망가진다.

### 5-2. 핵심은 local few-candle structure다

판단의 핵심은 날짜나 장명이 아니라 최근 몇 개 캔들의 구조여야 한다.

예:

- higher low 유지 중인가
- lower high가 생겼는가
- breakout hold인가 false break인가
- retest 후 reclaim이 나왔는가
- wick reject가 continuation보다 reversal 쪽 증거인가
- 현재 캔들 body drive가 살아 있는가

### 5-3. state는 이미 있는데, 아직 방향 우세로 쓰이지 않는다

지금 state는 이미 많이 붙어 있다.

- forecast
- belief
- barrier
- state25
- continuation overlay
- HTF / previous box context

그런데 이 state가 현재는 다음처럼 작동한다.

- 방향을 밀어주는 층이라기보다
- wait/reduce/relief/watch 쪽의 caution 층

즉 필요한 것은 "state 추가"가 아니라 **state 내부 세기 분해와 dominance 판단**이다.

## 6. 새로 필요한 구조

## 6-1. state_strength_profile_v1

첫 버전의 핵심은 필드를 많이 늘리는 것이 아니라, **원인 계층과 도출 계층을 분리하는 것**이다.

현재 문제는 `wait_bias`, `reduce_alert`, `soft_block`, `upper_reject_confirm` 같은 caution 성격의 신호가
원인과 결과가 섞인 채 같은 무게로 continuation을 눌러버리는 데 있다.

그래서 첫 버전의 state strength contract는 아래 두 층으로 나눈다.

### 원인 계층

- `trend_pressure`
  - 지금 방향이 실제로 밀고 있는 힘
- `continuation_integrity`
  - 구조적으로 continuation이 유지되고 있는 정도
- `reversal_evidence`
  - 반대 방향 전환의 직접 증거
- `friction`
  - 같은 방향이지만 진입/추격 품질을 떨어뜨리는 마찰
- `exhaustion_risk`
  - 연장 말단이라 추격 품질이 나빠지는 정도
- `ambiguity`
  - continuation과 reversal 신호가 함께 살아 있는 정도

중요:

- **개념 모델은 6축을 유지한다.**
- 다만 **v1 구현 우선순위는 4축**으로 좁힌다.

v1 구현 우선순위:

- `continuation_integrity`
- `reversal_evidence`
- `friction`
- `dominance_gap`

즉 `trend_pressure`, `exhaustion_risk`, `ambiguity`는 문서와 runtime 해석 언어에는 남기되,
첫 구현에서 복잡도를 낮추기 위해 직접적인 계산 중심축에서는 한 단계 뒤로 둔다.

### 도출 계층

- `wait_bias_strength`
  - 위 원인 계층에서 계산되는 도출값
- `dominance_gap`
- `dominant_side`
  - `BULL / BEAR / NONE`
- `dominant_mode`
  - `CONTINUATION`
  - `CONTINUATION_WITH_FRICTION`
  - `BOUNDARY`
  - `REVERSAL_RISK`
- `caution_level`
  - `LOW / MEDIUM / HIGH`

즉 `wait_bias_strength`는 1차 원인 필드가 아니라 결과 필드다.
이렇게 나눠야 "왜 WAIT가 되었는가"와 "무엇이 실제 원인이었는가"를 분리해서 볼 수 있다.

이는 조언에서 제안한 continuation/reversal/wait/dominance 구조를 유지하되,
`wait_bias`를 원인층이 아닌 도출층으로 재배치한 형태다.

## 6-2. local_structure_profile_v1

local structure는 패턴 이름보다 **구조 상태 변화** 중심으로 시작해야 한다.

첫 버전에서 가장 값이 큰 축은 아래 세 가지다.

- `few_candle_higher_low_state / few_candle_lower_high_state`
  - 최근 3~9개 캔들에서 swing 구조가 continuation을 지지하는지
- `breakout_hold_quality`
  - 돌파 후 몇 개 봉이 실제로 유지되었는지
- `body_drive_state`
  - 최근 3봉이 실제 body drive로 방향을 밀고 있는지

이 세 축이 안정된 뒤에만 아래 보조 축을 확장한다.

- `retest_quality_state`
- `wick_rejection_state`
- `few_candle_continuation_hint`
- `few_candle_reversal_hint`

즉 첫 버전은 "최근 몇 봉이 continuation을 강화했는가, 약화했는가"를 우선 본다.

중요:

- 첫 버전은 이 3축을 **상태 등급**으로 surface한다.
- boolean보다는 `FAILED / WEAK / STABLE / STRONG`, `BROKEN / FRAGILE / HELD / CLEAN_HELD` 같은 등급이 우선이다.
- 점수화는 그 다음 단계에서 붙인다.

## 6-3. state_structure_dominance_profile_v1

최종적으로는 아래 세 층을 shadow-only로 먼저 합친다.

- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `session_bucket_v1` (bias only)

여기서 핵심은 단일 라벨이 아니라 **2단 출력**이다.

- `dominant_side`
  - `BULL / BEAR / NONE`
- `dominant_mode`
  - `CONTINUATION`
  - `CONTINUATION_WITH_FRICTION`
  - `BOUNDARY`
  - `REVERSAL_RISK`

이 구조가 있어야

- `BUY 쪽 우세인데 추격은 불편하다`
- `SELL 전환 증거는 아직 약하다`
- `지금 WAIT는 합리적인 boundary다`

를 분리해서 읽을 수 있다.

즉 현재 NAS 같은 장면은 `SELL`이 아니라
`BULL + CONTINUATION_WITH_FRICTION`
으로 읽혀야 한다.

그리고 아래 규칙을 명시적으로 유지한다.

- `friction`은 `dominant_side`를 바꾸지 않는다.
- `friction`은 `dominant_mode`와 `caution_level`만 조정한다.
- `dominant_side` 변경은 `reversal_evidence + structure break` 조합이 일정 수준 이상일 때만 허용한다.

또한 `dominance_gap`은 절대 세기가 아니라 **continuation vs reversal의 상대 우세를 나타내는 중심 필드**다.
즉 해석의 핵심은 "얼마나 강한가"보다 "무엇이 더 우세한가"에 있다.

### v1 dominance_gap 고정 정의

v1에서는 `dominance_gap`을 아래처럼 고정한다.

- `dominance_gap = continuation_integrity - reversal_evidence`

중요:

- `friction`은 `dominance_gap` 계산에 직접 넣지 않는다.
- `trend_pressure`는 side seed 보조 근거로만 사용한다.
- `ambiguity`는 side 경쟁에 직접 참여시키기보다 `BOUNDARY`와 `caution_level` 조정에 우선 사용한다.

즉 v1의 중심 비교는 어디까지나

- continuation 구조가 아직 살아 있는가
- 실제 reversal 증거가 얼마나 강한가

이 두 축의 상대 차이다.

## 6-4. consumer veto tier

현재 문제 중 하나는 `upper_reject_confirm`, `wait_bias`, `reduce_alert`, `soft_block`이 사실상 같은 veto 무게로 continuation을 누른다는 점이다.

이를 줄이기 위해 veto도 계층화해야 한다.

- `FRICTION_ONLY`
  - 같은 방향 continuation은 유지되지만 추격/즉시 진입은 불편한 상태
- `BOUNDARY_WARNING`
  - continuation과 reversal이 함께 살아 있어 경계로 둬야 하는 상태
- `REVERSAL_OVERRIDE`
  - 기존 continuation 우세를 실제로 뒤집을 정도의 전환 증거

중요 원칙:

- `upper_reject_confirm`이 있다고 해서 자동으로 `REVERSAL_OVERRIDE`가 되면 안 된다.
- 많은 경우 이 신호는 `FRICTION_ONLY` 또는 `BOUNDARY_WARNING`에 가까울 수 있다.

`REVERSAL_OVERRIDE`는 매우 비싸야 한다.

- 단일 `upper_reject`
- 단일 `soft_block`
- 단일 `wait_bias`

같은 신호 하나만으로는 override가 되면 안 된다.
최소한 아래와 같은 조합이 필요하다.

- `continuation_integrity` 저하
- `reversal_evidence` 상승
- local structure break
- 반대 방향 drive 확인

## 6-5. local continuation discount

첫 버전에서는 forecast/belief/barrier 내부를 직접 고치지 않는다.
대신 local structure가 continuation을 강하게 지지하면 caution의 실효 강도를 할인하는 proxy를 둔다.

예:

- `higher_low` 유지
- `breakout_hold_quality = HIGH`
- `body_drive_state = STRONG_DRIVE`

가 함께 잡히면

- `friction`
- `wait_bias_strength`

의 실효값을 할인한다.

이렇게 하면 내부 caution 계층을 당장 뜯지 않고도
"continuation을 보는데 caution이 너무 쉽게 이기는 문제"를 완화할 수 있다.

중요:

- 이 discount는 항상 제한적이어야 한다.
- continuation 구조 증거가 여러 개 살아 있고
- `reversal_evidence`가 낮거나 중립일 때만 허용한다.
- ambiguity가 과도하게 높으면 discount를 적용하지 않는다.
- 이 discount는 `friction`과 `wait_bias_strength`의 실효값만 조정할 수 있다.
- 이 discount는 `reversal_evidence` 자체를 상쇄하거나 무효화하는 데 사용하지 않는다.

## 6-6. should-have-done calibration teacher

R3 should-have-done는 단순 review 후보 축이 아니라 dominance calibration teacher로 써야 한다.

각 review 후보에는 아래를 같이 남기는 방향이 맞다.

- 당시 `dominant_side` 추정
- 당시 `dominant_mode` 추정
- 당시 `caution_level`
- 실제 outcome 기준 정답 dominant mode
- 과대작동한 caution field
- 과소평가된 continuation evidence

가능하면 아래도 같이 남긴다.

- `dominance_error_type`
  - `CONTINUATION_UNDERPROMOTED`
  - `REVERSAL_OVERCALLED`
  - `BOUNDARY_STAYED_TOO_LONG`
  - `FRICTION_MISREAD_AS_REVERSAL`
  - `TRUE_REVERSAL_MISSED`

이 축이 붙어야 dominance layer가 설명 필드가 아니라 실제 오판 감소용 calibration surface가 된다.

## 7. 왜 이것이 필요한가

이 구조가 필요한 이유는 아래와 같다.

1. 현재 시스템은 "강하다"를 못 보는 게 아니라, "강하므로 계속 본다"로 승격하는 힘이 약하다.
2. 세션-aware 축만으로는 지금의 체감 오판을 설명할 수 없다.
3. should-have-done과 canonical surface는 이미 있으므로, 다음엔 "왜 이런 should-have-done이 생겼는가"를 설명할 intermediate layer가 필요하다.
4. 하드코딩을 더 늘리지 않고도, `reversal evidence`와 `continuation-under-friction`을 분리해서 읽을 수 있어야 한다.
5. caution 신호를 이진 veto가 아니라 강도와 tier로 읽어야 dominance 재정렬이 가능하다.
6. `dominance_gap`을 중심 필드로 삼아, 해석을 절대값이 아니라 상대 우세 비교에서 도출해야 한다.

## 8. 하지 말아야 할 것

다음은 명시적으로 금지한다.

1. `US면 BUY`, `ASIA면 SELL` 같은 직접 direction 하드코딩
2. `NAS만`, `XAU만` 같은 심볼 전용 dominance 규칙 추가
3. state strength를 바로 execution/state25에 연결
4. local structure 계약 없이 스크린샷 하나 보고 one-off 예외 추가
5. phase가 아직 약한데 CONTINUATION/BOUNDARY/REVERSAL 위에 더 세밀한 live 로직을 올리는 것
6. `upper_reject`, `wait_bias`, `soft_block`를 모두 같은 reversal veto로 취급하는 것
7. threshold 숫자를 고정 진리처럼 취급하는 것

## 9. 현재 단계의 가장 정확한 진단

한 문장으로 정리하면 이렇다.

**현재 시스템은 방향과 구조를 아예 못 보는 단계는 지났지만, 강한 state와 local continuation 구조를 읽고도 그것을 최종적인 우세 해석으로 승격하지 못하고 caution/wait 계층으로 과소 소비하는 단계에 있다.**

즉 다음 구현의 초점은

- 세션 확대가 아니라
- 심볼 예외 추가도 아니라
- `state strength + local structure + dominance resolution`

이어야 한다.

## 10. 외부 조언을 구할 때 핵심 질문

이 문서를 바탕으로 외부 조언을 구한다면 질문은 아래처럼 좁혀야 한다.

1. `state_strength_profile_v1`의 최소 축은 무엇이어야 하는가?
2. 최근 3~9개 캔들 기준 local continuation/reversal 판별에서 가장 값 큰 구조 축은 무엇인가?
3. `강세를 보면서도 caution으로 소비되는 상태`를 dominance 관점에서 어떻게 정리하는 것이 좋은가?
4. `reversal evidence`와 `continuation with friction`을 어떻게 분리하는 것이 좋은가?
5. shadow-only 단계에서 어떤 accuracy/validation을 먼저 붙여야 execution/state25 연결 위험을 줄일 수 있는가?

## 11. threshold 원칙

초기 threshold는 필요하지만, 이는 **초기 calibration 값**일 뿐 고정 진리가 아니다.

예:

- `dominance_gap > +X`
- `dominance_gap < -Y`
- `reversal_evidence > Z`

이런 값은 shadow-only 검증을 통해 조정 가능한 초기값으로 둔다.

즉 문서 원칙은 아래와 같다.

- threshold는 시작점이 될 수 있다
- threshold는 artifact와 hindsight를 통해 재보정된다
- threshold는 심볼/세션 하드코딩이 아니라 검증 기반으로 조정된다

## 12. v1 결정 절차

v1은 아래 순서로 판단한다.

### Step 1. side seed를 먼저 정한다

목적:

- continuation이 무엇을 유지하는지 기준을 만든다.
- reversal이 무엇을 뒤집으려는지 기준을 만든다.

우선순위:

1. `directional_continuation_overlay_direction`
2. `htf_alignment_state`
3. `previous_box_relation`
4. `previous_box_break_state`

출력:

- `side_seed = BULL / BEAR / NONE`
- `side_seed_confidence = LOW / MEDIUM / HIGH`

원칙:

- local structure는 이 단계에서 side를 직접 만들지 않는다.
- local structure는 뒤 단계에서 seed를 강화/약화/반전 검토하는 데 사용한다.

### Step 2. state strength 원인 계층을 계산한다

v1 핵심축:

- `continuation_integrity`
- `reversal_evidence`
- `friction`

보조 개념축:

- `trend_pressure`
- `exhaustion_risk`
- `ambiguity`

원칙:

- `wait_bias_strength`는 아직 계산하지 않는다.
- `friction`은 불편함이지 side 반전이 아니다.

### Step 3. local structure를 surface한다

v1 주축:

- `few_candle_higher_low_state / few_candle_lower_high_state`
- `breakout_hold_quality`
- `body_drive_state`

원칙:

- boolean보다 상태 등급이 우선이다.
- local structure는 seed direction을 지지/혼합/훼손하는 역할을 한다.

### Step 4. dominance_gap과 dominant_side 후보를 계산한다

v1 고정 정의:

- `dominance_gap = continuation_integrity - reversal_evidence`

원칙:

- `friction`은 gap 계산에 직접 넣지 않는다.
- `ambiguity`는 gap 계산의 보조 감쇠보다 `BOUNDARY`와 `caution_level` 판단에 우선 사용한다.
- `dominant_side` 변경은 `reversal_evidence + structure break`가 함께 누적될 때만 허용한다.

### Step 5. dominant_mode를 결정한다

후보:

- `CONTINUATION`
- `CONTINUATION_WITH_FRICTION`
- `BOUNDARY`
- `REVERSAL_RISK`

원칙:

- `friction`은 side를 바꾸지 않고 mode만 조정한다.
- `REVERSAL_RISK`는 `reversal_evidence`가 주도해야 한다.
- `ambiguity`는 `BOUNDARY`의 안전장치로 우선 사용한다.

### Step 6. veto tier와 caution_level을 결정한다

veto tier:

- `FRICTION_ONLY`
- `BOUNDARY_WARNING`
- `REVERSAL_OVERRIDE`

핵심 규칙:

- 단일 `upper_reject`, 단일 `wait_bias`, 단일 `soft_block`, 단일 `reduce_alert`는 기본적으로 `REVERSAL_OVERRIDE`가 아니다.
- `REVERSAL_OVERRIDE`는 continuation 약화 + reversal 증거 + local structure break 조합이 확인될 때만 허용한다.

### Step 7. 제한적 local continuation discount를 적용하고 final surface를 출력한다

discount 적용 조건:

- continuation 구조 증거가 여러 개 살아 있음
- `reversal_evidence`가 낮거나 중립
- ambiguity가 과도하지 않음

discount가 조정할 수 있는 것:

- `friction`
- `wait_bias_strength`

discount가 조정하면 안 되는 것:

- `reversal_evidence`
- structure break 판정
- `REVERSAL_OVERRIDE` 발동 조건

최종 surface 최소 출력:

- `side_seed`
- `continuation_integrity`
- `reversal_evidence`
- `friction`
- `dominance_gap`
- `dominant_side`
- `dominant_mode`
- `veto_tier`
- `caution_level`
- `discount_applied`
- `dominance_explanation_short`
