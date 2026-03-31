# Barrier vNext Roadmap

## 1. 목적

이 문서는 `Barrier`를 다시 발명하려는 문서가 아니다.

목적은 딱 3가지다.

1. 지금 `Barrier`가 꼭 써야 하는 핵심 입력이 무엇인지 고정한다.
2. 이미 계산되고 있는데 `Barrier`가 아직 안 먹는 입력을 분리한다.
3. 아직 없어서 나중에 추가해야 하는 입력을 따로 분리한다.

즉 이 문서는 `Barrier`를 더 크게 만들기 위한 문서가 아니라,
`Barrier`를 더 정확하고 덜 바보같게 만들기 위한 실행 로드맵이다.

---

## 2. Barrier의 한 줄 정의

`Barrier는 좋아 보이는 진입이라도 지금은 막아야 하는지 판단하는 차단 레이어다.`

더 짧게 쓰면:

`Barrier = 차단 레이어`

중요한 점:

- `Barrier`는 진입을 찾는 레이어가 아니다.
- `Barrier`는 방향을 새로 만드는 레이어가 아니다.
- `Barrier`는 `Position`, `Response`, `State`, `Evidence`, `Belief`가 만든 후보를 보고
  `지금은 막아야 하는가`만 판단해야 한다.

즉 `Barrier`가 하면 안 되는 일은 이거다.

- 새로운 `BUY`를 발명하기
- 새로운 `SELL`을 발명하기
- `Position` 대신 위치를 해석하기
- `Response` 대신 사건을 해석하기

---

## 3. 현재 Barrier의 현실 진단

현재 실제 구현은 주로 아래 파일에 있다.

- `backend/trading/engine/core/barrier_engine.py`
- `backend/trading/engine/core/models.py`

현재 `Barrier`는 생각보다 나쁘지 않다.
이미 다음 같은 핵심 차단은 하고 있다.

- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`
- 최종 `buy_barrier`
- 최종 `sell_barrier`

즉 뼈대는 있다.

문제는 다음이다.

1. `Barrier`가 새 `State v2`의 고급 라벨을 거의 못 먹는다.
2. `Barrier`가 장면별 차단을 더 세밀하게 못 한다.
3. 이미 있는 입력 중 놀고 있는 것이 많다.

---

## 4. 구분표

### 4-1. 꼭 사용되어야 하는 Core

이건 지금도 쓰고 있고, 앞으로도 `Barrier`의 중심으로 남아야 하는 것들이다.

| 분야 | 변수 | 의미 | 현재 상태 |
|---|---|---|---|
| Position conflict | `primary_label` | 현재 위치 구조가 conflict인지 aligned인지 | 사용 중 |
| Position conflict | `position_conflict_score` | 위치 충돌 강도 | 사용 중 |
| Middle chop | `middle_neutrality` | middle에서 애매하게 줄타는 정도 | 사용 중 |
| Policy | `source_direction_policy` | BUY_ONLY / SELL_ONLY / BOTH 같은 정책 | 사용 중 |
| State penalty | `countertrend_penalty` | 역추세 페널티 | 사용 중 |
| State penalty | `liquidity_penalty` | 유동성 부족 페널티 | 사용 중 |
| State penalty | `volatility_penalty` | 변동성 과대/과소 페널티 | 사용 중 |
| Evidence | `buy_total_evidence` | 현재 BUY 근거 총합 | 사용 중 |
| Evidence | `sell_total_evidence` | 현재 SELL 근거 총합 | 사용 중 |
| Belief | `buy_belief` | BUY thesis 누적 확신 | 사용 중 |
| Belief | `sell_belief` | SELL thesis 누적 확신 | 사용 중 |
| Belief | `buy_persistence` | BUY 지속성 | 사용 중 |
| Belief | `sell_persistence` | SELL 지속성 | 사용 중 |
| Belief | `belief_spread` | BUY/SELL belief 격차 | 사용 중 |

이것들은 `Barrier`의 core다.

즉 앞으로 뭘 추가하더라도, 이 core를 밀어내면 안 된다.

---

### 4-2. 이미 있는데 Barrier가 안 쓰는 친구들

이건 가장 먼저 harvest해야 하는 묶음이다.

특징:

- 이미 `State v2`에서 계산된다.
- 이미 runtime에도 찍힌다.
- 다른 레이어에서는 일부 쓰기도 한다.
- 그런데 `Barrier`는 거의 안 먹는다.

#### A. Session state idle inputs

| 변수 | 의미 | Barrier에서 왜 필요한가 |
|---|---|---|
| `session_regime_state` | 현재 세션이 edge rotation인지 balanced인지 expansion인지 | edge play를 너무 일찍 막지 않기 위해 |
| `session_expansion_state` | 세션 박스 안/밖, expansion 진행 상태 | breakout 초입을 막을지 말지 결정하기 위해 |
| `session_exhaustion_state` | 세션 확장이 이미 많이 진행됐는지 | 늦은 추격 진입을 막기 위해 |

#### B. Topdown idle inputs

| 변수 | 의미 | Barrier에서 왜 필요한가 |
|---|---|---|
| `topdown_spacing_state` | 상위 MA 간격이 넓은지, 촘촘한지 | 추세가 깔끔한지, 애매한지 판단하기 위해 |
| `topdown_slope_state` | 큰지도 기울기 정렬 상태 | 역추세 진입을 얼마나 세게 막을지 결정하기 위해 |
| `topdown_confluence_state` | 큰지도 confluence/conflict 상태 | 반대방향 시도 차단 강도를 정하기 위해 |

#### C. Execution stress idle inputs

| 변수 | 의미 | Barrier에서 왜 필요한가 |
|---|---|---|
| `spread_stress_state` | 스프레드가 빡센지 | 진입을 막아야 할 execution 환경인지 판단 |
| `volume_participation_state` | 참여도가 얇은지 | 허공 진입을 막기 위해 |
| `execution_friction_state` | 실제 체결 난이도 | 진입 타이밍을 더 보수적으로 막기 위해 |
| `event_risk_state` | 이벤트 리스크 상태 | 뉴스/특이 리스크 상황 차단에 필요 |

#### D. Advanced idle inputs

| 변수 | 의미 | Barrier에서 왜 필요한가 |
|---|---|---|
| `advanced_input_activation_state` | 고급 입력이 실제 켜졌는지 | 없는 데이터를 있는 것처럼 쓰지 않기 위해 |
| `tick_flow_state` | tick 흐름 bias/burst | micro trap 차단에 필요 |
| `order_book_state` | order book imbalance/thinness | 유동성 함정 차단에 필요 |

#### E. State raw 중 Barrier로 아직 안 올라온 품질 보조값

이 값들은 `State` 안에서는 이미 quality 계산에 쓰이지만,
Barrier가 직접 읽지는 않는다.

| 변수 | 의미 | Barrier 활용 후보 |
|---|---|---|
| `source_current_rsi` | 현재 RSI | 극단 구간에서 역행 진입 차단 강도 보조 |
| `source_current_adx` | 현재 ADX | 추세장/비추세장 차단 강도 보조 |
| `source_current_plus_di` | +DI | 방향성 strength 보조 |
| `source_current_minus_di` | -DI | 방향성 strength 보조 |
| `source_recent_range_mean` | 최근 range 평균 | 너무 얇은 장에서 가짜 신호 차단 |
| `source_recent_body_mean` | 최근 body 평균 | candle conviction 부족 차단 |
| `source_sr_level_rank` | 현재 S/R level rank | 하찮은 레벨인지 중요한 레벨인지 구분 |
| `source_sr_touch_count` | S/R touch count | 반복 터치 레벨 신뢰도 보조 |

이 묶음은 `Barrier core`는 아니지만, `quality-aware barrier`를 만들 때 중요하다.

---

### 4-3. 필요한데 아직 없는 친구들

이건 지금 당장 코드에 거의 없거나, semantic barrier 입력으로 없어서 나중에 추가해야 하는 것들이다.

#### A. VP / micro inventory barrier

| 후보 | 의미 | 왜 필요한가 |
|---|---|---|
| `vp_collision_barrier` | 1분봉 매물대 충돌 차단 | 눈에 보이는 미세 매물대 저항/지지를 semantic barrier로 쓰기 위해 |
| `micro_inventory_thin_barrier` | 위아래 매물 공백 구간 차단 | 갑작스런 미끄럼 실행을 막기 위해 |

#### B. Session open shock barrier

| 후보 | 의미 | 왜 필요한가 |
|---|---|---|
| `session_open_shock_barrier` | 장 시작 직후 충격성 움직임 차단 | 장 시작 직후 과민 진입을 막기 위해 |

#### C. Duplicate edge / trap barrier

| 후보 | 의미 | 왜 필요한가 |
|---|---|---|
| `duplicate_edge_barrier` | 같은 edge에서 반복 재진입 차단 | 같은 자리에서 계속 털리는 걸 막기 위해 |
| `micro_trap_barrier` | wick trap / false turn 차단 | 한 봉 함정 진입을 막기 위해 |

#### D. Event risk detail refinement

| 후보 | 의미 | 왜 필요한가 |
|---|---|---|
| `pre_event_barrier` | 이벤트 직전 차단 | 큰 숫자 발표 직전 진입 막기 위해 |
| `post_event_cooldown_barrier` | 이벤트 직후 냉각 | whipsaw 구간 차단 |

---

## 5. Barrier vNext 목표

Barrier vNext의 목표는 단순하다.

### 목표 1
`State v2`에 이미 있는 정보를 Barrier가 실제로 먹게 만든다.

### 목표 2
`Barrier`가 애매한 진입은 더 잘 막고,
정작 edge에서 먹어야 하는 진입은 덜 막게 만든다.

### 목표 3
고급 입력은 항상 켜는 게 아니라, 필요한 경우에만 차단 보조로 쓴다.

---

## 6. 패치 우선순위

핵심 원칙:

`새로운 입력을 발명하기 전에, 이미 있는 입력부터 Barrier에 먹인다.`

이 순서가 중요한 이유:

- 가장 안전하다
- 회귀 위험이 적다
- 디버그가 쉽다
- 진짜로 필요한 missing input이 뭔지 더 선명해진다

추천 순서는 다음과 같다.

1. `idle existing inputs harvest`
2. `edge / breakout / range 장면별 barrier refinement`
3. `missing input additions`
4. `runtime acceptance`
5. `pre-ML readiness`

---

## 7. 상세 로드맵

### Phase BR0. Freeze

목표:

- `Barrier`의 역할을 더 이상 흔들지 않는다.

고정 문장:

`Barrier는 진입을 찾는 레이어가 아니라, 지금은 막아야 하는지를 판단하는 차단 레이어다.`

완료 기준:

- Position / Response / State / Evidence / Belief와 owner 충돌 없음
- Barrier가 side creator처럼 행동하지 않음

---

### Phase BR1. Existing input harvest

목표:

- 이미 `State v2`에 있는 라벨을 `Barrier`에 연결한다.

1차 대상:

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

2차 대상:

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

완료 기준:

- `barrier_state_v1.metadata.semantic_barrier_inputs_v2` 생성
- runtime에서 새 state harvest 값 직접 확인 가능
- 기존 core barrier 값과 새 harvest 값이 분리 기록됨

---

### Phase BR2. Scene-aware barrier refinement

목표:

- 같은 barrier가 모든 장면에 똑같이 작동하지 않게 만든다.

핵심 장면:

#### A. Edge turn

예:

- 하단에서 반등 초입
- 상단에서 거절 초입

필요한 방향:

- `session_regime_state = SESSION_EDGE_ROTATION`
- `topdown_confluence_state = WEAK_CONFLUENCE or TOPDOWN_CONFLICT`
- `middle_chop_barrier`가 너무 과하게 작동하지 않도록 완화

의도:

- edge에서 먹어야 하는 reversal을 Barrier가 과하게 막지 않게

#### B. Breakout continuation

예:

- 상단 돌파 후 continuation
- 하단 붕괴 후 continuation

필요한 방향:

- `session_expansion_state`
- `topdown_slope_state`
- `topdown_confluence_state`

의도:

- continuation 장면에서 역추세 fade 진입을 Barrier가 더 세게 막게

#### C. Middle chop

예:

- 가운데에서 위도 아래도 아닌 애매한 구간

필요한 방향:

- `middle_neutrality`
- `belief_spread deadband`
- `execution_friction_state`
- `volume_participation_state`

의도:

- middle 줄타기 구간에서 괜한 진입을 더 잘 차단

완료 기준:

- `edge_turn_relief_v1`
- `breakout_fade_barrier_v1`
- `middle_chop_barrier_v2`
같은 세부 메타가 남음

---

### Phase BR3. Advanced input gating

목표:

- 고급 입력을 항상 쓰지 말고, 필요한 경우에만 Barrier에 태운다.

대상:

- `advanced_input_activation_state`
- `tick_flow_state`
- `order_book_state`
- `event_risk_state`

원칙:

- unavailable이면 중립
- partial이면 약한 보조
- active이면 barrier 강화 가능

완료 기준:

- 없는 데이터를 잘못된 차단 근거로 쓰지 않음
- advanced input이 실제 활성화된 경우에만 barrier 영향 증가

---

### Phase BR4. Missing barrier inputs 추가

목표:

- 지금 없는 semantic barrier를 추가한다.

우선순위:

1. `session_open_shock_barrier`
2. `duplicate_edge_barrier`
3. `micro_trap_barrier`
4. `vp_collision_barrier`
5. `post_event_cooldown_barrier`

왜 이 순서인가:

- `session open`과 `duplicate edge`는 영향이 크고 비교적 단순하다.
- `VP`는 좋지만 계산량과 데이터 의존성이 더 크다.

완료 기준:

- new barrier는 각각 명확한 역할과 차단 이유를 가짐
- 기존 barrier와 의미 중복이 적음

---

### Phase BR5. Runtime acceptance

목표:

- 실제 차트 사례에서 Barrier가 자연스럽게 작동하는지 본다.

확인할 것:

#### 케이스 1. 하단 edge 반등

기대:

- `Barrier`가 하단 반등 진입을 과하게 막지 않음

#### 케이스 2. 상단 edge 거절

기대:

- 진짜 거절은 안 막고
- continuation이면 역추세 SELL을 막음

#### 케이스 3. middle chop

기대:

- middle 진입은 더 잘 막음

#### 케이스 4. high friction / event risk

기대:

- 좋아 보여도 execution 환경이 나쁘면 차단 강화

완료 기준:

- `blocked_by` 이유가 체감과 맞음
- 차트 기준으로 “왜 막았는지” 설명 가능

---

### Phase BR6. Pre-ML readiness

목표:

- 나중에 ML calibration이 붙을 때 Barrier를 feature로 안전하게 쓸 수 있게 한다.

필수 출력:

- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

추천 출력:

- `edge_turn_relief_score`
- `breakout_fade_barrier_score`
- `execution_friction_barrier_score`
- `event_risk_barrier_score`

완료 기준:

- ML 없이도 의미 설명 가능
- ML이 붙어도 `Barrier`가 semantic owner를 뺏기지 않음

---

## 8. 실행 순서 요약

진짜 작업 순서는 이렇게 가는 게 가장 좋다.

1. `BR0 Freeze`
2. `BR1 Existing input harvest`
3. `BR2 Scene-aware refinement`
4. `BR3 Advanced input gating`
5. `BR4 Missing barrier inputs 추가`
6. `BR5 Runtime acceptance`
7. `BR6 Pre-ML readiness`

---

## 9. 지금 바로 제일 먼저 할 일

현재 기준으로 제일 먼저 해야 하는 건 이것이다.

### 1순위

`State v2 idle inputs를 Barrier에 harvest`

왜:

- 이미 계산되고 있다
- 회귀 위험이 적다
- 효과가 빠르게 보인다

### 2순위

`edge / breakout / middle 장면별 barrier refinement`

왜:

- 지금 네가 답답해하는 건 대부분 “막아야 할 때와 막지 말아야 할 때”의 구분 문제이기 때문이다

### 3순위

`missing inputs 추가`

왜:

- 새 기능 추가는 그 다음이어야 의미 중복이 적다

---

## 10. 한 줄 결론

`Barrier vNext의 핵심은 새 차단 규칙을 마구 늘리는 것이 아니라, 이미 있는 State v2 입력을 실제로 먹이고, edge / breakout / middle 장면별로 "막아야 할 때와 막지 말아야 할 때"를 더 정교하게 나누는 것이다.`
