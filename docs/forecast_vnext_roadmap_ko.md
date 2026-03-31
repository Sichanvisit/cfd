# Forecast vNext Roadmap

## 1. 왜 지금 Forecast 로드맵이 필요한가

지금 upstream는 많이 정리됐다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

여기까지는 semantic owner가 꽤 선명해졌다.

이제 문제는 그 다음이다.

```text
semantic layers
-> forecast features
-> transition forecast / trade management forecast / gap metrics
-> effective wrapper
-> observe / confirm / action / consumer
-> offline replay / dataset / calibration
```

즉 지금부터는 `Forecast`가 단순한 보조 출력이 아니라,
이미 만든 semantic 구조를 실제 실행과 나중 ML calibration까지 이어주는
중간 허리 역할을 더 잘 해야 한다.

---

## 2. 현재 구조 한 줄 요약

현재 Forecast는 이미 아래 구조로 존재한다.

```text
forecast_features_v1
-> transition_forecast_v1
-> trade_management_forecast_v1
-> forecast_gap_metrics_v1
-> forecast_effective_policy_v1
```

즉 지금 필요한 것은 `Forecast를 새로 발명하는 것`이 아니라:

- 잘 쓰는 것을 더 잘 쓰게 만들고
- 있는데 잘 못 쓰는 것을 실제로 활용하게 만들고
- 있으면 더 좋은 것을 최소 침습으로 추가해
- downstream와 자연스럽게 맞물리게 만드는 것이다

---

## 3. 큰 방향

Forecast 로드맵의 원칙은 이 세 가지다.

### 3-1. 구조를 뒤엎지 않는다

- `forecast_features_v1`
- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`
- `forecast_effective_policy_v1`

이 구조는 유지한다.

### 3-2. 역할을 더 선명하게 한다

- `transition` = 반응의 다음 전개
- `trade_management` = 들고 갈지/자를지/다시 탈지
- `gap_metrics` = 두 갈래 차이 요약
- `effective_wrapper` = downstream에 넘기는 정책 포장층

### 3-3. downstream 활용 강도를 높인다

지금 문제는 대체로 `Forecast가 없어서`가 아니라:

- execution이 충분히 안 씀
- gap metrics를 덜 씀
- effective wrapper가 아직 bridge 성격이 큼

이 세 가지다.

---

## 4. 현재 상태를 분류하면

### 4-1. 이미 잘 쓰는 것

#### A. 입력 번들

- `forecast_features_v1`
- `Position / Response / State / Evidence / Belief / Barrier`를 잘 묶는다

#### B. transition branch

- confirm / reversal / continuation / false break를 나눈다

#### C. trade management branch

- continue / fail / tp1 / reentry / recover를 나눈다

#### D. gap metrics

- 두 forecast 결과 차이를 비교용 숫자로 압축한다

#### E. runtime 노출

- `ContextClassifier` runtime metadata에 남는다
- downstream 서비스가 읽을 수 있다

### 4-2. 있는데 잘 못 쓰는 것

#### A. rich state 활용

아래는 upstream엔 있지만 forecast 수학에 아직 약하게만 쓰이거나 거의 안 쓰인다.

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `spread_stress_state`
- `volume_participation_state`
- `execution_friction_state`
- `event_risk_state`

#### B. belief 확장값 활용

- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`
- `flip_readiness`
- `belief_instability`

#### C. barrier 확장값 활용

- `edge_turn_relief_v1`
- `breakout_fade_barrier_v1`
- `middle_chop_barrier_v2`
- `execution_friction_barrier_score`
- `event_risk_barrier_score`
- `session_open_shock_barrier_v1`
- `duplicate_edge_barrier_v1`
- `micro_trap_barrier_v1`
- `vp_collision_barrier_v1`
- `post_event_cooldown_barrier_v1`

#### D. effective wrapper 활용

- `forecast_effective_policy_v1`는 아직 bridge 성격이 강하다
- 실제 policy/utility assist는 약하다

### 4-3. 있으면 더 좋은 것

#### transition 쪽

- `edge_turn_success`
- `failed_breakdown_reclaim_success`
- `failed_breakout_flush_success`
- `continuation_exhaustion_risk`

#### management 쪽

- `hold_through_noise_score`
- `premature_exit_risk`
- `edge_to_edge_completion_prob`
- `flip_after_exit_quality`
- `stop_then_recover_risk`

#### gap 쪽

- `wait_confirm_gap`
- `hold_exit_gap`
- `same_side_flip_gap`
- `belief_barrier_tension_gap`

#### effective wrapper 쪽

- `policy_overlay_applied = true`가 실제 의미를 갖는 단계
- `utility_overlay_applied`
- `consumer_hint_weighting`

---

## 5. 목표 상태

Forecast가 잘 정리되면 downstream는 이렇게 흘러가야 한다.

```text
Market Data
-> Position / Response / State / Evidence / Belief / Barrier
-> forecast_features_v1
-> transition_forecast_v1 / trade_management_forecast_v1 / forecast_gap_metrics_v1
-> forecast_effective_policy_v1
-> Observe / Confirm / Action / Consumer
-> Offline snapshots / OutcomeLabeler / replay / dataset / calibration
```

그리고 각 층의 역할은 다음처럼 고정된다.

- `TransitionForecast`
  - 다음 방향 전개를 읽는다
- `TradeManagementForecast`
  - 들고 갈지, 자를지, 다시 탈지를 읽는다
- `GapMetrics`
  - 두 forecast 차이를 execution이 읽기 쉽게 해준다
- `EffectiveWrapper`
  - downstream 정책/모드에 맞게 전달한다

---

## 6. Phase 로드맵

---

## Phase FR0. Freeze

### 목표

Forecast의 3갈래 역할을 더 이상 흔들지 않는다.

### 고정 문장

`Forecast는 semantic owner를 새로 만드는 레이어가 아니라, 이미 만들어진 semantic outputs를 다음 전개와 관리 관점에서 해석하는 branch layer다.`

### owner 경계

- `Position`의 위치 owner를 뺏지 않음
- `Response`의 사건 owner를 뺏지 않음
- `State`의 장 성격 owner를 뺏지 않음
- `Evidence`의 순간 근거 owner를 뺏지 않음
- `Belief`의 지속성 owner를 뺏지 않음
- `Barrier`의 차단 owner를 뺏지 않음

### 완료 기준

- Forecast는 side creator가 아니라 forecast layer로만 정의됨
- branch 역할 충돌 없음

---

## Phase FR1. Existing input harvest

### 목표

이미 upstream에 있는 rich semantic 값을 Forecast 3갈래가 더 직접 활용하게 만든다.

### 1차 대상

#### State harvest

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `spread_stress_state`
- `volume_participation_state`
- `execution_friction_state`
- `event_risk_state`

#### Belief harvest

- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`
- `flip_readiness`
- `belief_instability`

#### Barrier harvest

- `edge_turn_relief_v1`
- `breakout_fade_barrier_v1`
- `middle_chop_barrier_v2`
- `session_open_shock_barrier_v1`
- `duplicate_edge_barrier_v1`
- `micro_trap_barrier_v1`
- `post_event_cooldown_barrier_v1`

### 2차 대상

- `advanced_input_activation_state`
- `tick_flow_state`
- `order_book_state`
- `source_current_rsi`
- `source_current_adx`
- `source_current_plus_di`
- `source_current_minus_di`
- `source_recent_range_mean`
- `source_recent_body_mean`
- `source_sr_level_rank`
- `source_sr_touch_count`

### 완료 기준

- `forecast_features_v1.metadata.semantic_forecast_inputs_v2` 생성
- runtime에서 harvest된 값 확인 가능
- branch 수학에서 실제 사용 여부를 분리 기록 가능

---

## Phase FR2. Transition branch refinement

### 목표

`transition_forecast_v1`가 장면별 전개를 더 잘 읽게 만든다.

### 핵심 장면

#### A. Edge turn

예:

- 하단 반등 초입
- 상단 거절 초입

추가 반영할 것:

- `session_regime_state = SESSION_EDGE_ROTATION`
- `topdown_confluence_state = WEAK_CONFLUENCE / TOPDOWN_CONFLICT`
- `edge_turn_relief_v1`
- `flip_readiness`

의도:

- edge reversal이 continuation/fake로 과하게 눌리지 않게

#### B. Breakout continuation

예:

- 상단 돌파 후 continuation
- 하단 붕괴 후 continuation

추가 반영할 것:

- `session_expansion_state`
- `topdown_slope_state`
- `topdown_confluence_state`
- `breakout_fade_barrier_v1`

의도:

- 진짜 continuation과 premature fade를 더 잘 분리

#### C. Failed break reclaim / flush

예:

- failed breakdown -> squeeze up
- failed breakout -> flush down

추가 반영할 것:

- `flip_readiness`
- `belief_instability`
- `duplicate_edge_barrier_v1`
- `micro_trap_barrier_v1`

의도:

- break 실패가 reversal thesis로 바뀌는 순간을 더 잘 읽기

### 추천 신규 출력

- `p_edge_turn_success`
- `p_failed_breakdown_reclaim`
- `p_failed_breakout_flush`
- `p_continuation_exhaustion`

### 완료 기준

- `transition_forecast_v1.metadata.scene_transition_support_v1` 생성
- edge / continuation / failed-break 장면 지원값 확인 가능

---

## Phase FR3. Trade management branch refinement

### 목표

`trade_management_forecast_v1`가 네가 말한

- 좋은 진입 후 방관
- 중간 흔들림에 덜 털림
- 반대 edge까지 가져감
- 잘라야 할 때만 자름

을 더 잘 반영하게 만든다.

### 핵심 장면

#### A. Good entry hold

예:

- 하단 좋은 BUY 후 중간 흔들림
- 상단 좋은 SELL 후 중간 흔들림

추가 반영할 것:

- `buy_persistence / sell_persistence`
- `buy_streak / sell_streak`
- `hold_patience_gain`
- `fast_exit_risk_penalty`

의도:

- 좋은 진입 후 성급한 청산 감소

#### B. Premature exit risk

예:

- 아직 thesis는 안 깨졌는데 중간 파동에 겁먹고 자름

추가 반영할 것:

- `belief_spread`
- `dominant_side`
- `middle_chop_barrier_v2`
- `execution_friction_state`

의도:

- 단순 흔들림과 진짜 실패를 분리

#### C. Reentry / flip after cut

예:

- 잘랐는데 다시 타야 하는가
- 반대 thesis로 갈아타야 하는가

추가 반영할 것:

- `flip_readiness`
- `opposite belief rise`
- `duplicate_edge_barrier_v1`
- `post_event_cooldown_barrier_v1`

의도:

- 무의미한 재진입보다 의미 있는 재진입을 선별

### 추천 신규 출력

- `p_hold_through_noise`
- `p_premature_exit_risk`
- `p_edge_to_edge_completion`
- `p_flip_after_exit_quality`
- `p_stop_then_recover_risk`

### 완료 기준

- `trade_management_forecast_v1.metadata.management_scene_support_v1` 생성
- hold / cut / reentry 장면별 설명 가능

---

## Phase FR4. Gap metrics promotion

### 목표

`forecast_gap_metrics_v1`를 단순 로그가 아니라 execution assist에 더 쓸 수 있게 만든다.

### 현재 유지할 핵심 gap

- `transition_side_separation`
- `transition_confirm_fake_gap`
- `transition_reversal_continuation_gap`
- `management_continue_fail_gap`
- `management_recover_reentry_gap`

### 추가 추천 gap

- `wait_confirm_gap`
- `hold_exit_gap`
- `same_side_flip_gap`
- `belief_barrier_tension_gap`

### 의도

- execution이 지금 무엇이 더 선명한지 빠르게 읽게
- 한 branch 값 하나보다, 갈래 차이를 더 잘 이용하게

### 완료 기준

- `forecast_gap_metrics_v2` 또는 metadata promotion
- runtime에서 gap 기반 explainability 강화

---

## Phase FR5. Effective wrapper actualization

### 목표

`forecast_effective_policy_v1`를 단순 bridge에서 실제 assist wrapper로 키운다.

### 현재 문제

- `policy_overlay_applied = false`
- `effective_equals_raw = true`

가 많아서, 실제 effective layer 의미가 약하다.

### 바꾸고 싶은 방향

- Layer Mode에 따라 branch 영향 강도 조절
- `shadow / assist / enforce`에 따라 consumer hint 강도 차등
- utility overlay가 `wait/confirm/hold/exit` 해석에 미세 보정

### 예시

- `assist` 모드
  - `transition`과 `management`를 hint로만 강화
- `enforce` 모드
  - barrier나 friction이 높은 경우 execution 쪽 veto 강화

### 완료 기준

- `forecast_effective_policy_v1.metadata.policy_overlay_applied = true`
- `forecast_effective_policy_v1.metadata.utility_overlay_applied = true`
- raw와 effective 차이를 설명 가능

---

## Phase FR6. Observe / Confirm / Action integration

### 목표

Forecast 3갈래가 실행층에서 더 직접적으로 읽히게 만든다.

### 1차 연결 대상

- `ObserveConfirm`
- `EntryService`

### 의도

- `transition_forecast_v1`
  - 지금 observe인지 confirm인지
- `trade_management_forecast_v1`
  - 지금 과감히 들어가도 되는지
- `gap_metrics`
  - wait vs confirm이 얼마나 선명한지

를 실제 진입 판단에 더 직접 반영

### 핵심 규칙

- `confirm_fake_gap`이 크면 confirm 쪽 가산
- `wait_confirm_gap`이 작으면 observe 유지
- `continue_fail_gap`이 작으면 무리 진입 자제

### 완료 기준

- `observe_confirm_v2.metadata.forecast_assist_v1` 생성
- `entry_decision_result_v1`에서 forecast assist 흔적 확인 가능

---

## Phase FR7. Energy helper / Consumer hint integration

### 목표

Forecast 3갈래와 gap을 `Energy` 및 `Consumer`가 더 잘 쓰게 만든다.

### 대상

- `energy_helper_v2`
- `consumer hint usage`

### 의도

- 단순 evidence/belief/barrier 조합을 넘어서
- forecast branch 차이까지 helper가 읽게

### 강화할 것

- `transition_confirm_fake_gap`
- `management_continue_fail_gap`
- `management_recover_reentry_gap`
- future `hold_exit_gap`
- future `same_side_flip_gap`

### 완료 기준

- `energy_helper_v2.metadata.forecast_gap_usage_v1`
- consumer hint가 branch별로 설명 가능

---

## Phase FR8. Offline path integration

### 목표

Forecast 3갈래를 replay / validation / dataset / calibration 경로에서 더 잘 쓰게 만든다.

### 대상

- semantic + forecast snapshots
- `OutcomeLabeler`
- validation
- replay
- dataset
- calibration

### 의도

- 나중에 ML이 붙을 때
  - transition branch
  - management branch
  - gap metrics
가 각각 어떤 장면에서 잘/못 맞았는지
깨끗하게 평가 가능하게 함

### 추가하면 좋은 것

- branch별 hit/miss label
- `transition_forecast_vs_outcome`
- `management_forecast_vs_outcome`
- `gap_signal_quality`

### 완료 기준

- offline artifacts에서 3갈래 성능을 분리 분석 가능

---

## Phase FR9. Runtime acceptance

### 목표

실제 차트 사례에서 Forecast 3갈래 해석이 체감과 맞는지 본다.

### 확인할 것

#### 케이스 1. 하단 edge 반등

기대:

- `transition`은 reversal 성공 쪽
- `management`는 hold favor 쪽
- `gap`은 confirm 우위 쪽

#### 케이스 2. 상단 edge 거절

기대:

- 진짜 거절은 `transition sell-side reversal` 쪽으로
- continuation이면 fade 억제

#### 케이스 3. middle chop

기대:

- `transition`이 과감한 confirm을 내지 않음
- `management`도 fail/reentry를 과하게 밀지 않음

#### 케이스 4. high friction / event risk

기대:

- 좋아 보여도 execution 환경이 나쁘면 forecast effective 쪽이 보수적이어야 함

### 완료 기준

- 차트 기준으로 “왜 transition은 이렇게 봤는지”
- “왜 management는 hold/cut로 봤는지”
- “gap은 왜 이 정도였는지”

설명 가능

---

## Phase FR10. Pre-ML readiness

### 목표

나중에 ML calibration이 붙을 때 Forecast 3갈래를 feature로 안전하게 쓸 수 있게 한다.

### 필수 출력

#### Transition

- `p_buy_confirm`
- `p_sell_confirm`
- `p_reversal_success`
- `p_continuation`
- `p_false_break`

#### Trade management

- `p_continue_favor`
- `p_fail_now`
- `p_reach_tp1`
- `p_better_reentry_if_cut`
- `p_recover_after_pullback`

#### Gap metrics

- `transition_side_separation`
- `transition_confirm_fake_gap`
- `transition_reversal_continuation_gap`
- `management_continue_fail_gap`
- `management_recover_reentry_gap`

### 추천 출력

- `edge_turn_success`
- `premature_exit_risk`
- `hold_exit_gap`
- `same_side_flip_gap`

### 완료 기준

- ML 없이도 의미 설명 가능
- ML이 붙어도 Forecast가 semantic owner를 뺏지 않음

---

## 7. 구현 우선순위

지금 시점에서 가장 현실적인 순서는 이렇다.

1. `FR0 Freeze`
2. `FR1 Existing input harvest`
3. `FR2 Transition branch refinement`
4. `FR3 Trade management refinement`
5. `FR4 Gap metrics promotion`
6. `FR6 Observe / Confirm / Action integration`
7. `FR5 Effective wrapper actualization`
8. `FR7 Energy helper / Consumer hint integration`
9. `FR8 Offline path integration`
10. `FR9 Runtime acceptance`
11. `FR10 Pre-ML readiness`

중요한 점:

- 실행에 바로 체감이 오는 건 `FR2`, `FR3`, `FR4`, `FR6`
- 구조 완성도에 중요한 건 `FR0`, `FR1`, `FR5`
- 나중 ML과 리플레이에 중요한 건 `FR8`, `FR10`

---

## 8. 지금 바로 제일 중요한 것

이 문서 기준으로 지금 제일 중요한 것은 다음 네 가지다.

### 1. Forecast 입력 harvest

이미 있는 rich `State / Belief / Barrier`를 3갈래가 더 직접 먹게

### 2. Transition 장면 강화

edge turn / continuation / failed break 장면을 더 잘 읽게

### 3. Management 장면 강화

좋은 진입 후 hold, premature exit, reentry/flip을 더 잘 읽게

### 4. Gap metrics 승격

execution이 `무엇이 더 선명한지`를 숫자로 더 잘 읽게

---

## 9. 한 줄 결론

`Forecast vNext의 핵심은 새 branch를 더 만드는 것이 아니라, 이미 있는 transition / trade management / gap metrics 3갈래가 upstream semantic 구조를 더 깊게 받아서 execution, consumer, offline calibration까지 자연스럽게 이어지게 만드는 것이다.`

