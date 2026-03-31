# CFD 프로젝트 구조 설명서

## 문서 목적

이 문서는 다른 언어모델이나 다른 작업 스레드가 이 프로젝트를 빠르게 이해할 수 있도록, 현재 시스템이 어떤 구조로 되어 있는지 실제 코드 기준으로 설명하는 handoff 문서다.

이 프로젝트는 단순한 "볼린저밴드 + 박스 + 캔들 조건" 전략 봇이 아니다. 현재 구조는 다음 세 가지를 함께 가진다.

1. 기존 rule-based scorer / preflight 기반 진입 판단 계층
2. 그 위에 얹힌 semantic foundation 기반 의미 해석 엔진
3. semantic snapshot을 이용한 offline replay / validation / shadow-ML 계층

즉, 이 시스템은 단일 규칙 전략 코드라기보다, 시장 상태를 여러 단계의 의미 레이어로 분해한 뒤, 그 결과를 라이브 엔트리/청산과 오프라인 평가 양쪽에 재사용하는 구조다.

---

## 한 줄 요약

이 프로젝트는 CFD/선물형 시장 데이터를 입력받아,

- 가격이 구조적으로 어디에 있는지(`Position`)
- 그 위치에서 어떤 반응이 일어나는지(`Response`)
- 그 반응을 얼마나 신뢰해야 하는지(`State`)
- 지금 당장 어느 방향 증거가 강한지(`Evidence`)
- 그 증거가 시간축에서 유지되는지(`Belief`)
- 지금 행동을 막는 구조적 마찰이 있는지(`Barrier`)

를 순서대로 계산한 뒤,

- 가까운 전이 가능성(`TransitionForecast`)
- 포지션 관리 가능성(`TradeManagementForecast`)
- 실제 observe / confirm / wait / no-trade 형태의 라이브 handoff(`ObserveConfirmSnapshot`)

로 연결하는 의미 기반 트레이딩 엔진이다.

동시에 이 semantic snapshot들은 replay dataset, outcome labeler, validation report, shadow model 비교에도 사용된다.

---

## 프로젝트를 이해할 때 가장 중요한 관점

이 시스템은 "한 번에 BUY/SELL을 찍는 전략"으로 이해하면 안 된다.

핵심은 다음과 같다.

1. 의미 레이어와 실행 레이어가 분리되어 있다.
2. 라이브 경로와 오프라인 평가 경로가 분리되어 있다.
3. semantic foundation은 앞으로도 유지될 feature layer로 취급된다.
4. setup naming, entry gating, wait handling, exit policy는 semantic owner가 아니라 consumer layer다.
5. ML은 semantic foundation을 대체하는 주체가 아니라, 현재로서는 shadow compare 및 rollout 대상이다.

---

## 최상위 구조

현재 프로젝트의 큰 흐름은 아래처럼 보면 된다.

```text
Market Data
-> legacy scorer / preflight
-> ContextClassifier
-> EngineContext normalization
-> Position
-> Response Raw / Response Vector V2
-> State Raw / State Vector V2
-> Evidence
-> Belief
-> Barrier
-> ForecastFeatures
-> TransitionForecast / TradeManagementForecast
-> ObserveConfirm
-> SetupDetector
-> EntryService / WaitEngine / ExitService

Offline in parallel
semantic + forecast snapshots
-> replay dataset builder
-> outcome labeler
-> validation report
-> semantic shadow model compare / rollout
```

---

## 현재 프로젝트의 성격

이 프로젝트는 실질적으로 세 층으로 나뉜다.

### 1. 기존 rule-based 실행 층

여기에는 과거부터 있던 scorer 기반 점수 시스템이 있다.

- `backend/trading/scorer.py`
- `backend/services/strategy_service.py`
- `backend/app/trading_application_runner.py`

이 레이어는 여전히 앱에서 사용되며, raw score, contra score, threshold, preflight 같은 실행 판단의 기반을 제공한다.

즉, 이 프로젝트는 semantic engine으로 완전히 갈아탄 상태가 아니라, legacy scoring과 semantic interpretation이 공존하는 과도기 구조다.

### 2. semantic foundation 층

이 층이 현재 프로젝트의 핵심이다.

semantic foundation은 아래 6개의 layer로 구성된다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

이들은 직접 주문을 넣지 않는다. 시장을 의미적으로 정리하고, 라이브 실행 consumer가 읽을 수 있는 안정된 feature layer를 만든다.

### 3. offline / ML / shadow 평가 층

semantic 결과를 바로 버리지 않고 저장/재구성해서,

- replay dataset 생성
- outcome labeling
- validation report
- forecast calibration
- semantic shadow model prediction
- live rollout gating

에 재사용한다.

즉 "실시간 판단"과 "나중에 평가/학습"이 같은 semantic substrate를 공유한다.

---

## 앱 레벨 오케스트레이션

앱 레벨에서는 `TradingApplication`이 전체 런타임을 들고 있다.

주요 특징은 다음과 같다.

- MT5 broker adapter, notifier, observability adapter를 붙인다.
- `Scorer`, `StrategyService`, `EntryService`, `ExitService`를 함께 사용한다.
- semantic shadow runtime과 promotion guard를 앱 레벨에 올려둔다.
- runtime status, entry decisions, rollout 상태를 파일로 남긴다.

즉 이 앱은 단순 전략 실행기가 아니라,

- 브로커 연결
- 룰 기반 전략 실행
- semantic 해석
- ML shadow 비교
- observability / logging

을 모두 포함한 통합 트레이딩 런타임이다.

---

## 핵심 진입점: ContextClassifier

현재 semantic engine의 실제 조립기는 `backend/services/context_classifier.py`다.

이 컴포넌트는 이름만 보면 단순 분류기 같지만, 실제 역할은 훨씬 크다.

이 클래스는 입력 시장 데이터를 받아 다음을 만든다.

1. `EngineContext`
2. `PositionSnapshot`
3. `ResponseRawSnapshot`
4. `ResponseVectorV2`
5. `StateRawSnapshot`
6. `StateVectorV2`
7. `EvidenceVector`
8. `BeliefState`
9. `BarrierState`
10. `ForecastFeaturesV1`
11. `TransitionForecast`
12. `TradeManagementForecast`
13. `ObserveConfirmSnapshot`

즉, semantic foundation과 forecast branch와 observe/confirm routing까지 한 번에 이어 붙인다.

다른 모델에게 설명할 때는 `ContextClassifier`를 "semantic live decision bundle builder"로 소개하는 것이 맞다.

---

## EngineContext: raw market input의 정규화 컨테이너

semantic engine의 출발점은 `EngineContext`다.

여기에는 아래 정보가 들어간다.

- symbol
- current price
- market mode
- direction policy
- box state
- bb state
- box high / low
- bb20 / bb44 상중하단
- 이동평균
- support / resistance
- trendline
- volatility scale
- metadata

중요한 점은 `EngineContext`는 해석 결과가 아니라 입력을 정규화해서 semantic layer가 읽기 좋게 만든 컨테이너라는 것이다.

즉, 여기에는 아직 BUY/SELL 의미가 없다.

---

## Semantic Foundation 상세 설명

### 1. Position

`Position`의 역할은 "현재 가격이 구조적으로 어디에 있는가"를 설명하는 것이다.

이 레이어는 다음 축을 사용한다.

- `x_box`
- `x_bb20`
- `x_bb44`
- `x_ma20`
- `x_ma60`
- `x_sr`
- `x_trendline`

핵심 개념은 다음과 같다.

- box / BB / SR / trendline 기준으로 가격 위치를 좌표화한다.
- 단순히 상단/하단만 보는 것이 아니라 zone, alignment, bias, conflict, dominance를 분리한다.
- `Position`은 방향 결정자가 아니라 location describer다.

출력은 다음 세 부분으로 구성된다.

- `PositionVector`
- `PositionInterpretation`
- `PositionEnergySnapshot`

`PositionInterpretation`은 예를 들면 이런 값을 만든다.

- `ALIGNED_LOWER_STRONG`
- `ALIGNED_UPPER_WEAK`
- `LOWER_BIAS`
- `CONFLICT_BOX_UPPER_BB20_LOWER`
- `UNRESOLVED_POSITION`

즉 Position은 "하단 근처인가?" 수준이 아니라,

- 여러 축이 정렬되어 있는지
- 축끼리 충돌하는지
- middle neutrality가 큰지
- 어느 쪽 force가 더 강한지

까지 정리한다.

### 2. Response

`Response`는 그 위치에서 실제로 어떤 반응이 발생하는지를 설명한다.

이 레이어는 여러 raw source를 합친다.

- band response
- candle response
- pattern response
- structure response
- SR response
- trendline response
- micro response

그리고 최종적으로 canonical axes로 축약한다.

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

이 의미는 중요하다.

이 프로젝트에서 pattern name 자체가 최종 decision unit이 아니다.
pattern은 canonical response axis를 증폭하거나 보조하는 재료다.

예를 들어 핵심은 "double bottom이냐"가 아니라,
"지금 lower hold / mid reclaim 쪽 반응이 실제로 발생하고 있느냐"다.

### 3. State

`State`는 현재 반응을 얼마나 신뢰할 수 있는지, 어떤 종류의 전개가 유리한지를 설명한다.

핵심 coefficient는 다음과 같다.

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`
- `wait_patience_gain`
- `confirm_aggression_gain`
- `hold_patience_gain`
- `fast_exit_risk_penalty`

즉 State는 새로운 방향을 만드는 레이어가 아니라,
이미 계산된 response / evidence를 얼마나 세게 또는 약하게 읽어야 하는지 조정하는 layer다.

특히 이 프로젝트의 State는 단순 regime label 수준이 아니라,

- topdown spacing
- topdown slope
- topdown confluence
- spread stress
- volume participation
- execution friction
- session exhaustion
- event risk

같은 실행 현실성까지 metadata로 보존한다.

### 4. Evidence

`Evidence`는 Position + Response + State를 합쳐 "지금 당장 어느 쪽 증거가 강한가"를 만든다.

대표 필드는 다음과 같다.

- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_continuation_evidence`
- `sell_continuation_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

이건 미래 예측이 아니다.
현재 bar / 현재 맥락에서 immediate proof를 요약하는 단계다.

### 5. Belief

`Belief`는 Evidence를 시간축으로 누적한다.

대표 필드는 다음과 같다.

- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `flip_readiness`
- `belief_instability`
- `dominant_side`
- `dominant_mode`
- `buy_streak`
- `sell_streak`
- `transition_age`

즉 Belief는 "한 캔들만 센지"와 "같은 방향 증거가 계속 유지되는지"를 분리한다.

다른 모델에게는 이렇게 설명하면 된다.

"Evidence는 현재 증거, Belief는 그 증거의 시간적 지속성과 전환 준비도다."

### 6. Barrier

`Barrier`는 증거가 있어도 지금 행동하면 안 되는 이유를 설명한다.

대표 필드는 다음과 같다.

- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

그리고 metadata에는 더 세부적인 bar/edge/session/micro trap barrier들이 들어간다.

즉 Barrier는 "지금은 맞아 보여도 실행하지 말아야 하는 구조적 마찰"을 표현한다.

---

## Forecast Layer

semantic foundation 다음에는 forecast branch가 온다.

중요한 점은 forecast가 semantic owner가 아니라는 것이다.
즉 forecast는 Position/Response/State/Evidence/Belief/Barrier를 새로 만들지 않는다.
이미 만들어진 semantic output을 해석해 near-term probability branch로 묶는다.

### ForecastFeaturesV1

이 레이어는 semantic layer를 forecast-friendly input contract로 패키징한다.

포함되는 핵심 입력은 다음과 같다.

- `position_primary_label`
- `position_bias_label`
- `position_secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

즉 forecast는 raw OHLC를 직접 재해석하지 않고 semantic layer만 읽는다.

### TransitionForecast

이 레이어는 near-term transition 가능성을 점수화한다.

대표 필드는 다음과 같다.

- `p_buy_confirm`
- `p_sell_confirm`
- `p_false_break`
- `p_reversal_success`
- `p_continuation_success`

### TradeManagementForecast

이 레이어는 진입 후 관리 가능성을 따로 본다.

대표 필드는 다음과 같다.

- `p_continue_favor`
- `p_fail_now`
- `p_recover_after_pullback`
- `p_reach_tp1`
- `p_opposite_edge_reach`
- `p_better_reentry_if_cut`

이 분리가 중요하다.

이 시스템은 "들어갈지 말지"와 "들어간 뒤 관리가 쉬울지"를 같은 값으로 보지 않는다.

---

## Observe / Confirm / Action Layer

semantic foundation과 forecast branch가 끝나면 `ObserveConfirmSnapshot`으로 이어진다.

이건 live action handoff를 위한 canonical identity layer다.

대표 필드는 다음과 같다.

- `state`
- `action`
- `side`
- `confidence`
- `reason`
- `archetype_id`
- `invalidation_id`
- `management_profile_id`

여기서 중요한 개념은 `archetype_id`다.

현재 시스템의 핵심 archetype은 다음과 같다.

- `lower_hold_buy`
- `lower_break_sell`
- `mid_reclaim_buy`
- `mid_lose_sell`
- `upper_reject_sell`
- `upper_break_buy`

즉 이 시스템은 최종적으로 "그냥 BUY/SELL"이 아니라,
"어떤 archetype에 해당하는 buy/sell인지"를 먼저 만든다.

그리고 invalidation과 management profile도 이 단계에서 같이 handoff된다.

다른 모델에게는 이렇게 설명하면 좋다.

"ObserveConfirm is the canonical live handoff surface. It is already past semantic interpretation and contains the archetype identity that downstream consumers must preserve."

---

## SetupDetector의 역할

`SetupDetector`는 이름만 보면 setup을 탐지하는 것 같지만,
현재 책임은 사실상 "setup naming only"에 가깝다.

이 컴포넌트는 `observe_confirm`에서 넘어온 다음 요소를 읽는다.

- `archetype_id`
- `side`
- `reason`
- `market_mode`

그리고 그것을 `setup_id`로 매핑한다.

예를 들어 다음처럼 매핑된다.

- `lower_hold_buy` + range 맥락 -> `range_lower_reversal_buy`
- `mid_reclaim_buy` + trend 맥락 -> `trend_pullback_buy`
- `upper_reject_sell` + range 맥락 -> `range_upper_reversal_sell`

중요한 점은 SetupDetector가 다시 confirm/wait를 결정하지 않는다는 것이다.

즉 역할은:

- identity 보존
- naming specialization

이지,

- 재판단
- 진입 강도 계산
- semantic 재해석

이 아니다.

---

## EntryService의 역할

`EntryService`는 실제 실행 consumer다.

여기서는 semantic foundation을 직접 owner처럼 재해석하지 않고, handoff surface를 읽어 실행 쪽 결정을 한다.

주요 내부 구성은 다음과 같다.

- `ContextClassifier`
- `SetupDetector`
- `WaitEngine`
- `ShadowEntryPredictor`
- `ShadowWaitPredictor`
- `EntryGuardEngine`
- `EntryThresholdEngine`
- `SessionPolicy`
- `AtrThresholdPolicy`
- `SlippagePolicy`

즉 EntryService는 semantic identity를 만든다기보다,

- setup naming
- wait vs enter 비교
- guard
- threshold 조절
- 세션/ATR/slippage 현실성 반영
- 실행 로깅

을 담당한다.

다른 말로 하면 semantic engine이 "의미"를 만들고,
EntryService가 그 의미를 "실행 가능한 엔트리 프로토콜"로 소비한다.

---

## WaitEngine의 역할

이 프로젝트는 WAIT를 단순한 실패 상태로 보지 않는다.

WAIT는 별도의 소비 경로로 취급된다.

즉 이 시스템은 "BUY/SELL 못하면 NO_TRADE"가 아니라,

- 아직 observe 상태인지
- confirm 전 대기인지
- hard wait인지
- soft wait인지
- wait가 enter보다 EV가 나은지

를 따로 판단한다.

이 때문에 프로젝트 전체가 단일 trigger bot보다 훨씬 상태기계에 가깝다.

---

## ExitService와 ExitProfileRouter

청산도 단순 고정 익절/손절이 아니다.

현재 구조에서는 entry 시점의 archetype과 management profile이 exit 쪽으로 handoff된다.

`ExitProfileRouter`는 다음 같은 management profile을 다룬다.

- `reversal_profile`
- `support_hold_profile`
- `breakout_hold_profile`
- `breakdown_hold_profile`
- `mid_reclaim_fast_exit_profile`
- `mid_lose_fast_exit_profile`

그리고 이를 실제 정책으로 바꾼다.

- `tight_protect`
- `protect_then_hold`
- `hold_then_trail`
- symbol-specific balanced recovery

또한 state / belief / execution friction / session exhaustion / event risk에 따라,

- `max_wait_seconds`
- `be_max_loss_usd`
- `tp1_max_loss_usd`
- `reverse_score_gap`

같은 회복/보호 파라미터를 동적으로 조정한다.

즉 exit는 entry의 부속 if문이 아니라 독립적인 setup-aware recovery system이다.

---

## Legacy scorer 계층과 semantic 계층의 관계

다른 모델이 가장 헷갈릴 수 있는 부분이 이것이다.

이 프로젝트에는 아직 `backend/trading/scorer.py` 기반의 rule scorer가 남아 있다.

이 scorer는 다음 같은 전통적인 요소를 다룬다.

- multi-timeframe context
- H1 structure
- BB touch / retest
- RSI trigger
- level retest hold

즉 옛날 스타일의 score-based entry evaluation을 계속 제공한다.

하지만 현재 프로젝트의 발전 방향은 단순 scorer 확장이 아니라,
semantic foundation을 기준으로 의미를 분해하고 consumer layer가 이를 사용하게 만드는 쪽이다.

따라서 이 시스템은 완전한 새 엔진으로 갈아탄 상태가 아니라,

- legacy score baseline
- semantic meaning layer
- shadow ML compare

가 함께 존재하는 하이브리드 상태다.

---

## Session / ATR / Slippage 현실성 계층

이 프로젝트는 "신호만 맞으면 된다"는 식으로 설계되지 않았다.

`entry_runtime_policy.py`에는 다음이 있다.

### SessionPolicy

- 과거 closed trade history를 읽는다.
- 심볼 + 세션 + 요일별 성과 편차를 본다.
- threshold multiplier를 조정한다.

즉 세션은 단순 라벨이 아니라 실제 threshold tuning factor로 쓰인다.

### AtrThresholdPolicy

- 현재 ATR과 reference ATR의 비율을 계산한다.
- 진입 threshold를 변동성 상태에 맞게 조정한다.

### SlippagePolicy

- 요청 가격과 실제 체결 가격 차이를 추적한다.
- entry slippage points를 남긴다.

즉 이 프로젝트는 "전략 규칙"만이 아니라 execution realism도 모델 내부에 반영하려는 구조다.

---

## Consumer contract와 책임 경계

이 프로젝트는 contract 문서화가 강한 편이다.

중요한 원칙은 아래와 같다.

1. consumer는 semantic vector를 직접 재해석하면 안 된다.
2. consumer는 canonical handoff surface를 읽어야 한다.
3. `observe_confirm_v2`가 공식 identity surface다.
4. `layer_mode_policy_v1`는 identity를 바꾸지 않고 execution suppression/readiness만 조절한다.
5. `energy_helper_v2`는 힌트용이지 identity owner가 아니다.

즉 downstream consumer는 다음을 하면 안 된다.

- semantic vector를 자기 마음대로 다시 읽기
- energy helper를 canonical side처럼 쓰기
- archetype / invalidation / management profile을 임의로 rewrite하기

이 경계는 이 프로젝트를 장기적으로 유지 가능한 구조로 만드는 핵심 규율이다.

---

## Layer mode / Energy helper의 의미

이 프로젝트에는 semantic 결과 위에 얇게 얹히는 overlay 계층도 있다.

대표적으로:

- `layer_mode_policy_v1`
- `energy_helper_v2`

이 둘은 semantic foundation과 다르다.

semantic foundation이 identity를 만들고,
overlay는 execution-friendly hint를 제공한다.

즉 이 계층은 다음 역할만 허용된다.

- readiness modulation
- suppression hint
- priority hint
- confidence adjustment hint

하지만 다음 역할은 금지된다.

- side identity creation
- archetype rewrite
- semantic ownership takeover

---

## Offline 경로

이 프로젝트의 또 하나의 핵심은 live decision path와 별도로 offline evaluation path가 매우 강하게 설계되어 있다는 점이다.

offline 경로에서는 semantic snapshot과 forecast 결과를 그대로 재사용한다.

핵심 구성 요소는 다음과 같다.

- `backend/trading/engine/offline/replay_dataset_builder.py`
- `backend/trading/engine/offline/outcome_labeler.py`
- `backend/trading/engine/offline/outcome_label_validation_report.py`
- `scripts/build_replay_dataset.py`
- `scripts/outcome_label_validation_report.py`
- `scripts/forecast_bucket_validation.py`

### replay dataset builder

이 컴포넌트는 decision log와 replay row를 연결해서 JSONL dataset을 만든다.

여기에는 다음 정보가 들어간다.

- semantic snapshots
- forecast snapshots
- row keys
- label quality summary
- validation report path
- build manifest

즉 단순 CSV dump가 아니라, replay integrity와 label quality까지 추적 가능한 dataset pipeline이다.

### outcome labeler

OutcomeLabeler는 semantic snapshot 이후 실제 결과를 보고,

- reversal 성공 여부
- continuation 성공 여부
- false break 여부
- management outcome

같은 label을 만든다.

이것은 라이브 엔트리 판단 로직이 아니라, 사후 평가/학습을 위한 labeling 시스템이다.

### validation report

forecast calibration, outcome label quality, replay integrity 같은 것들을 따로 보고서로 만든다.

즉 이 프로젝트는 "전략을 짰다" 수준이 아니라,
"전략 판단 흔적을 나중에 재구성하고 평가할 수 있는 데이터 파이프라인"까지 포함한다.

---

## Semantic shadow ML 계층

현재 앱에는 `ml/semantic_v1` shadow runtime도 붙어 있다.

이건 현재 live owner가 아니라 compare / rollout 대상이다.

핵심 개념은 다음과 같다.

1. semantic snapshot에서 ML용 feature row를 만든다.
2. timing / entry_quality / exit_management 모델을 shadow로 돌린다.
3. baseline rule 결과와 semantic model 결과를 비교한다.
4. promotion guard가 rollout mode에 따라 log_only / alert_only / threshold_only / partial_live를 관리한다.

즉 ML은 지금 단계에서 semantic foundation을 대체하지 않는다.
오히려 semantic foundation 위에서 shadow inference를 수행하고,
품질과 rollout 조건이 맞을 때만 제한적으로 live threshold 조정에 사용된다.

---

## 이 프로젝트를 전략적으로 해석하면

전략 아이디어 수준에서 보면 이 프로젝트는 대략 다음 성격을 가진다.

- session/structure-aware box interpretation
- Bollinger-based response interpretation
- candle energy and micro reaction interpretation
- regime-aware evidence accumulation
- setup-specific execution and recovery policy

하지만 실제 구현은 "박스 전략", "볼린저 전략"처럼 단순 분류하기 어렵다.

그 이유는 이 시스템이 이미 다음을 분리했기 때문이다.

- 위치
- 반응
- 상태 신뢰도
- 즉시 증거
- 시간적 누적
- 실행 장벽
- 전이 예측
- 관리 예측
- 라이브 handoff
- setup naming
- entry/wait/exit consumer

즉 이 프로젝트는 단일 전략보다, 의미 계층을 가진 trading decision framework에 가깝다.

---

## 다른 모델에게 꼭 알려줘야 할 오해 방지 포인트

### 1. Position은 진입 신호가 아니다

Position은 현재 위치를 설명한다. BUY/SELL 확정자가 아니다.

### 2. Response는 이벤트 해석이지 최종 액션이 아니다

Response는 lower hold, upper reject 같은 canonical transition 반응을 설명한다.

### 3. State는 방향 생성자가 아니라 해석 강도 조절자다

State는 range/trend/quality/friction을 통해 신뢰도를 조정한다.

### 4. ObserveConfirm이 라이브 canonical identity surface다

downstream는 semantic vectors를 다시 읽지 말고 observe_confirm handoff를 읽어야 한다.

### 5. SetupDetector는 naming only에 가깝다

setup detector가 다시 판단을 하는 구조가 아니다.

### 6. Exit는 entry의 부속이 아니라 독립적인 관리 시스템이다

management profile과 invalidation handoff를 바탕으로 recovery policy를 별도로 구성한다.

### 7. ML은 현재 owner가 아니라 shadow / rollout 계층이다

semantic engine을 교체한 상태가 아니다.

### 8. legacy scorer가 아직 살아 있다

완전한 semantic-only 구조가 아니라 hybrid migration 상태다.

---

## 다른 언어모델에 바로 전달할 수 있는 설명문

아래 문단은 다른 모델에게 그대로 붙여 넣어도 된다.

```text
이 프로젝트는 단순한 규칙형 매매봇이 아니라, CFD/선물형 시장 데이터를 여러 의미 레이어로 분해해서 라이브 의사결정과 오프라인 평가에 동시에 재사용하는 구조다. 현재 구조는 legacy scorer 기반 rule engine과, 그 위에 구축된 semantic foundation이 공존하는 hybrid 상태다.

semantic foundation의 핵심 레이어는 Position, Response, State, Evidence, Belief, Barrier다. Position은 가격이 구조적으로 어디에 있는지 설명하고, Response는 그 위치에서 어떤 canonical transition 반응이 일어나는지 설명한다. State는 그 반응을 얼마나 신뢰해야 하는지와 range/trend/quality/friction 계수를 제공한다. Evidence는 현재 시점의 즉시 증거를, Belief는 그 증거의 시간적 누적과 persistence를, Barrier는 지금 행동을 막는 구조적 마찰을 표현한다.

그 다음 ForecastFeatures가 semantic layer를 묶고, TransitionForecast와 TradeManagementForecast가 near-term 전이 가능성과 진입 후 관리 가능성을 각각 계산한다. 이후 ObserveConfirmSnapshot이 canonical live handoff surface 역할을 하며, 여기에는 state, action, side, confidence, reason, archetype_id, invalidation_id, management_profile_id가 들어간다. downstream consumer는 semantic vectors를 다시 해석하지 않고 이 observe/confirm handoff를 읽는 것이 원칙이다.

SetupDetector는 현재 실질적으로 setup naming only 역할을 하며, observe_confirm의 archetype_id와 market_mode 등을 읽어 range_lower_reversal_buy, trend_pullback_buy 같은 setup_id로 specialization한다. EntryService는 setup naming, wait handling, guards, thresholds, session/ATR/slippage 현실성 반영을 담당하고, ExitService/ExitProfileRouter는 management_profile과 invalidation handoff를 바탕으로 recovery policy와 protection policy를 구성한다.

또한 이 프로젝트는 offline path가 강하다. semantic/forecast snapshot은 replay dataset builder, outcome labeler, validation report, forecast calibration에 재사용된다. 별도로 ml/semantic_v1 shadow runtime이 붙어 있어서 timing/entry_quality/exit_management 모델을 shadow compare 및 rollout 용도로 돌리지만, 현재 ML은 semantic owner가 아니고 baseline rule/semantic engine 위의 보조 비교 계층이다.
```

---

## 다른 모델에게 질문을 맡길 때 추천하는 요청 방식

다른 모델에게는 다음처럼 묻는 게 좋다.

1. "이 구조에서 semantic foundation과 consumer boundary가 잘 분리되어 있는지 봐줘."
2. "ObserveConfirm -> SetupDetector -> EntryService 경계가 적절한지 검토해줘."
3. "legacy scorer와 semantic engine이 공존하는 현재 구조에서 어떤 기술부채가 큰지 봐줘."
4. "Position/Response/State/Evidence/Belief/Barrier의 책임이 겹치는 부분이 있는지 찾아줘."
5. "offline replay/labeler/shadow-ML 경로까지 포함해서 전체 아키텍처 관점에서 리팩터링 우선순위를 제안해줘."

이렇게 물으면 단순 전략 조언보다 훨씬 프로젝트 맞춤형 답을 받을 가능성이 높다.

