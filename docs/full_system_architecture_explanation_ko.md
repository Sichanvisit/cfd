# CFD 전체 시스템 구조 설명서

## 문서 목적
이 문서는 현재 CFD 시스템을 다른 스레드나 다른 사람이 읽었을 때,

- 전체 구조가 어떻게 이어지는지
- 각 레이어가 정확히 무엇을 의미하는지
- 어디까지가 semantic foundation이고
- 어디부터 policy / utility overlay인지
- forecast는 어디에 있고
- observe / confirm / action은 어디서 결정되고
- consumer는 무엇만 해야 하는지
- outcome labeler와 offline path는 왜 필요한지

를 한 번에 이해할 수 있도록 만든 **전체 구조 설명서**입니다.

이 문서는 단순 로드맵이 아니라,  
현재 코드베이스와 계약 문서를 기준으로 한 **개념 설명 + 운영 설명 + 확장 설명** 문서입니다.

---

## 한눈에 보는 전체 구조

```text
Market Data
-> Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier
-> Forecast Features
-> Transition Forecast / Trade Management Forecast
-> Observe / Confirm / Action
-> Consumer

Policy / Utility Overlay
raw semantic outputs
-> Layer Mode
-> effective semantic outputs
-> Energy Helper
-> consumer hint usage

Offline path
semantic + forecast snapshots
-> OutcomeLabeler
-> validation / replay / dataset / calibration
```

이 구조를 정확히 이해하려면 이걸 세 줄기로 나눠서 봐야 합니다.

1. **Semantic Foundation**
- 현재 상황이 무엇인지 설명하는 층

2. **Policy / Utility Overlay**
- semantic 결과의 영향 강도를 조절하고 실행 힌트로 압축하는 층

3. **Offline Evaluation / Learning Path**
- 나중에 봤을 때 예측이 맞았는지 채점하고, replay/validation/dataset을 만드는 층

---

## 1. Market Data

### 역할
모든 해석의 출발점입니다.

여기서 들어오는 것:
- 가격
- box 정보
- bb20 / bb44 정보
- moving average
- support / resistance
- trendline
- 시장 상태에 필요한 기초 입력

### 중요한 점
`Market Data`는 아직 의미 해석 전 상태입니다.

즉 여기에는:
- “상단이다”
- “반전이다”
- “기다려야 한다”

같은 의미가 없습니다.

이건 그냥 원재료입니다.

---

## 2. Semantic Foundation

Semantic Foundation은 아래 6개 레이어를 뜻합니다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

이 6개는 앞으로도 유지되는 **의미 기반 feature layer**입니다.

이 레이어들의 공통 원칙:
- raw 데이터를 의미 있는 상태로 정리한다
- 직접 최종 action을 만들지 않는다
- consumer가 다시 raw처럼 해석하지 않게 한다
- 향후 ML/DL이 들어와도 그대로 feature layer로 유지한다

---

## 2-1. Position

### 역할
현재 가격이 구조적으로 어디에 있는지 설명합니다.

### 대표 출력
- `PositionSnapshot`
- `PositionInterpretation`
- `PositionEnergySnapshot`

### 핵심 의미
- 상단/하단/중앙 어디에 있는가
- 각 위치축이 정렬되어 있는가
- 서로 충돌하는가
- 위치 에너지가 어느 쪽이 우세한가

### Position이 하지 않는 것
- BUY/SELL 결론 생성
- 진입/청산 직접 판단
- response/event 생성

즉 Position은:
**“어디에 있나”**만 말합니다.

---

## 2-2. Response

### 역할
그 위치에서 어떤 전이 반응이 나왔는지 설명합니다.

### 구조
- `ResponseRawSnapshot`
- `ResponseVectorV2`

### canonical response 축
- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

### 의미
- 하단 지지냐
- 하단 실패냐
- 중심 재탈환이냐
- 중심 상실이냐
- 상단 실패냐
- 상단 돌파냐

즉 Response는:
**“어디서 무슨 방향 전이가 일어났나”**를 말합니다.

---

## 2-3. State

### 역할
현재 반응을 얼마나 믿어야 하는지 설명합니다.

### 대표 출력
- `StateRawSnapshot`
- `StateVectorV2`

### canonical 계수
- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`

### 의미
- 지금은 range 쪽이 더 유리한가
- trend continuation 쪽이 더 유리한가
- noise/conflict가 얼마나 해석을 눌러야 하는가
- execution friction이 큰가

즉 State는:
**“이 반응을 얼마나 믿을지”**를 말합니다.

---

## 2-4. Evidence

### 역할
지금 당장 어느 쪽 증거가 더 강한지 정리합니다.

### 대표 출력
- `EvidenceVector`

### canonical 필드
- `buy_reversal_evidence`
- `sell_reversal_evidence`
- `buy_continuation_evidence`
- `sell_continuation_evidence`
- `buy_total_evidence`
- `sell_total_evidence`

### 의미
이건 미래 예측이 아니라,
**현재 시점의 immediate proof** 입니다.

즉 Evidence는:
**“지금 이 순간 어느 쪽 증거가 더 강한가”**를 말합니다.

---

## 2-5. Belief

### 역할
Evidence가 시간 축에서 얼마나 유지되고 있는지를 누적합니다.

### 대표 출력
- `BeliefState`

### canonical 필드
- `buy_belief`
- `sell_belief`
- `buy_persistence`
- `sell_persistence`
- `belief_spread`
- `transition_age`

### 의미
- 1봉짜리 신호인가
- 몇 봉 동안 같은 방향으로 유지되는가
- 현재 dominant transition의 나이가 몇 봉인가

즉 Belief는:
**“증거가 얼마나 누적되고 유지되고 있는가”**를 말합니다.

---

## 2-6. Barrier

### 역할
증거가 있어도 왜 지금 action이 막혀야 하는지 구조 장벽을 설명합니다.

### 대표 출력
- `BarrierState`

### canonical 필드
- `buy_barrier`
- `sell_barrier`
- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`

### 의미
- conflict 때문에 막히는가
- middle chop 때문에 막히는가
- direction policy 때문에 막히는가
- 유동성/변동성 때문에 막히는가

즉 Barrier는:
**“왜 아직 action으로 가면 안 되는가”**를 말합니다.

---

## 3. Forecast

Forecast는 semantic foundation 위에 올라가는 예측층입니다.

### 역할
현재 semantic 상태를 보고,
다음 몇 봉에서 어떤 시나리오가 더 유력한지 점수화합니다.

### 구조
- `ForecastFeaturesV1`
- `TransitionForecastV1`
- `TradeManagementForecastV1`

### 의미
이건 아직 행동 결정이 아닙니다.

Forecast는:
- confirm으로 갈 것 같은가
- false break일 것 같은가
- hold가 유리한가
- fail_now가 유리한가
- recover/re-entry 중 무엇이 더 plausible한가

를 말하는 **시나리오 점수층**입니다.

즉 Forecast는:
**“앞으로 무슨 전개가 더 유력한가”**를 말합니다.

---

## 4. Observe / Confirm / Action

이건 lifecycle decision 층입니다.

### 역할
semantic foundation + forecast를 읽고

- `WAIT`
- `OBSERVE`
- `CONFIRM`
- `ACTION`

중 어디에 해당하는지 결정합니다.

### 중요한 원칙
- 이 레이어가 policy/lifecycle owner입니다
- raw detector를 다시 읽으면 안 됩니다
- semantic layer를 다시 해석하면 안 됩니다
- forecast를 점수 그대로 action으로 바꾸면 안 됩니다

즉 OCA는:
**“그래서 지금 무엇을 할 건가”**를 말합니다.

---

## 5. Consumer

Consumer는 실행층입니다.

### 역할
이미 결정된 lifecycle/action을 실제로 실행하는 층입니다.

포함되는 것:
- `SetupDetector`
- `EntryService`
- exit/re-entry 실행층

### Consumer가 해야 하는 것
- setup 이름 붙이기
- 실행 guard 적용
- order send
- canonical handoff 기반 관리

### Consumer가 하면 안 되는 것
- raw detector 다시 읽기
- semantic layer 재해석
- 방향을 다시 만들기
- archetype을 바꾸기

즉 Consumer는:
**“결정을 실행한다”**가 맞고,  
**“의미를 다시 만든다”**가 아닙니다.

---

## 6. Policy / Utility Overlay

여기가 네가 지적한 빠졌던 부분입니다.

이 부분은 semantic foundation과 consumer 사이에서,
**의미를 바꾸지 않고 영향 강도와 utility를 다루는 층**입니다.

구조:

```text
raw semantic outputs
-> Layer Mode
-> effective semantic outputs
-> Energy Helper
-> consumer hint usage
```

이건 semantic layer 자체가 아닙니다.
그리고 live decision core를 직접 대체하는 것도 아닙니다.

---

## 6-1. raw semantic outputs

이건 foundation이 그대로 계산한 원래 결과입니다.

예:
- `position_snapshot_v2`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`
- `forecast_*`

### 의미
- 항상 계산됩니다
- 숨기거나 끄지 않습니다
- 이게 기준 truth 입니다

즉 raw semantic outputs는:
**“정책 적용 전 원래 의미 결과”**입니다.

---

## 6-2. Layer Mode

Layer Mode는 semantic 레이어를 끄고 켜는 기능이 아닙니다.

### 역할
각 semantic layer가 실행에 얼마나 강하게 영향을 줄지 정책적으로 조절합니다.

### 모드
- `shadow`
- `assist`
- `enforce`

### 의미
- `shadow`
  - 기록만 하고 행동 영향 거의 없음
- `assist`
  - soft influence
- `enforce`
  - 규칙상 허용된 강한 영향 가능

### 중요한 원칙
- raw 출력은 항상 존재
- mode는 semantic 존재를 없애지 않음
- influence strength만 조정

즉 Layer Mode는:
**“이 semantic layer가 실행에 얼마나 강하게 작용할 수 있는가”**를 조절합니다.

---

## 6-3. effective semantic outputs

이건 Layer Mode 정책이 적용된 뒤의 결과입니다.

### 의미
- raw semantic 결과를 없애는 게 아님
- raw와 나란히 존재함
- 실행 영향 관점에서 조정된 버전

예:
- `evidence_vector_effective_v1`
- `belief_state_effective_v1`
- `barrier_state_effective_v1`
- `forecast_effective_policy_v1`

즉 effective outputs는:
**“원래 의미 결과를 실행 관점에서 조정한 버전”**입니다.

---

## 6-4. Energy Helper

여기도 자주 오해되는 부분입니다.

지금 Energy는 semantic layer가 아닙니다.

### 역할
effective semantic outputs를 읽고,
실행 친화적인 utility/helper 값으로 압축합니다.

### 대표 출력
- `selected_side`
- `action_readiness`
- `continuation_support`
- `reversal_support`
- `suppression_pressure`
- `forecast_support`
- `net_utility`
- `confidence_adjustment_hint`
- `soft_block_hint`

### 중요한 원칙
- Energy는 identity owner가 아닙니다
- `archetype_id`를 만들지 않음
- `side`를 만들지 않음
- semantic truth를 정의하지 않음

즉 Energy는:
**“얼마나 밀어주거나 눌러야 하는가”를 utility/helper로 압축하는 층**입니다.

---

## 6-5. consumer hint usage

이건 Consumer가 utility/helper를 읽는 방식입니다.

### 의미
consumer는 Energy를 읽을 수는 있지만,
그걸 semantic truth처럼 읽으면 안 됩니다.

즉:
- readiness hint
- confidence adjustment hint
- soft block hint
- priority hint
- wait vs enter hint

정도로만 읽어야 합니다.

### 핵심 원칙
- consumer는 semantic identity를 OCA에서 받음
- Energy는 utility hint일 뿐
- Energy를 보고 거래 정체성을 바꾸면 안 됨

즉 consumer hint usage는:
**“실행층이 utility helper를 advisory 수준에서 소비하는 방식”**입니다.

---

## 7. Offline Path

이것도 빠지면 안 되는 축입니다.

구조:

```text
semantic + forecast snapshots
-> OutcomeLabeler
-> validation / replay / dataset / calibration
```

이건 live path가 아니라,
**사후 검증과 학습 준비 경로**입니다.

---

## 7-1. semantic + forecast snapshots

이건 당시의 semantic foundation과 forecast 상태를 저장한 스냅샷입니다.

예:
- position / response / state
- evidence / belief / barrier
- forecast features / transition forecast / management forecast

### 의미
나중에 “그때 왜 그렇게 봤는지”를 replay할 수 있게 해줍니다.

---

## 7-2. OutcomeLabeler

### 역할
당시 forecast와 semantic snapshot을 보고,
미래 결과 기준으로 “그 예측이 맞았는지” 라벨을 붙입니다.

즉:
- forecast는 예측
- outcome labeler는 채점

### 중요한 점
이건 live action path가 아닙니다.
offline validation path입니다.

---

## 7-3. validation

### 역할
라벨이 얼마나 잘 붙었는지, 분포가 어떤지, unknown/censored가 얼마나 되는지 확인합니다.

즉 validation은:
**채점 품질 확인층**입니다.

---

## 7-4. replay

### 역할
과거 decision row를 다시 재생해서
- semantic 상태
- forecast 상태
- label 결과

를 동일하게 다시 볼 수 있게 합니다.

즉 replay는:
**재현성 확보층**입니다.

---

## 7-5. dataset

### 역할
semantic snapshot + forecast snapshot + outcome label을 한 row로 묶어서 학습 데이터셋으로 만듭니다.

즉 dataset은:
**ML/DL 훈련 입력 준비층**입니다.

---

## 7-6. calibration

### 역할
forecast 점수와 실제 outcome 사이의 관계를 다시 점검합니다.

예:
- `confirm_fake_gap`
- `continue_fail_gap`
- 점수 버킷별 실제 positive rate

즉 calibration은:
**현재 forecast가 실제 결과와 얼마나 맞는지 조정하는 단계**입니다.

---

## 8. 왜 이런 구조가 필요한가

이 구조가 필요한 이유는 하나입니다.

**지금 상태를 설명하는 레이어,  
실행 영향 강도를 조절하는 레이어,  
실제 행동을 결정하는 레이어,  
나중에 채점하는 레이어를 분리해야  
실거래 품질과 ML/DL 확장을 둘 다 잡을 수 있기 때문**입니다.

만약 이걸 분리하지 않으면:
- semantic 의미와 policy가 섞이고
- utility helper가 의미층처럼 행동하고
- consumer가 다시 의미를 만들고
- forecast가 맞는지 채점이 안 되고
- 결국 ML/DL도 붙이기 어려워집니다

---

## 9. 지금 구조에서 각 줄의 의미를 다시 한 번 요약

### `Market Data -> Position -> Response -> State -> Evidence -> Belief -> Barrier`
- 현재 상태를 해석 가능한 의미로 정리하는 층

### `-> Forecast Features -> Transition Forecast / Trade Management Forecast`
- 현재 semantic 상태를 바탕으로 다음 시나리오를 예측하는 층

### `-> Observe / Confirm / Action`
- 예측과 semantic 상태를 보고 지금 무엇을 할지 결정하는 층

### `-> Consumer`
- 그 결정을 실제로 실행하는 층

### `Policy / Utility Overlay`
- semantic layer의 영향 강도와 utility를 조절하는 층
- semantic truth를 바꾸는 층이 아님

### `Offline path`
- 나중에 봤을 때 예측이 맞았는지 채점하고
- replay / validation / dataset / calibration을 만드는 층

---

## 10. 최종 한 줄 요약

현재 시스템은

**semantic foundation이 현재 상태를 설명하고,  
policy / utility overlay가 그 의미의 실행 영향 강도를 조절하고,  
forecast가 다음 시나리오를 예측하고,  
OCA가 lifecycle을 결정하고,  
consumer가 실행하며,  
offline path가 나중에 그 예측을 채점하고 학습 가능한 형태로 바꾸는 구조**입니다.

이 전체 흐름을 같이 봐야 지금 구조가 왜 이렇게 나뉘어 있는지 이해할 수 있습니다.
