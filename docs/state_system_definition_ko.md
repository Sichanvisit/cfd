# State 시스템 정의서

## 목적

이 문서는 현재 엔진에서 `State`가 무엇을 책임져야 하는지,
그리고 앞으로 어떤 형태로 체계화해야 하는지를 정리한 기준 문서다.

핵심 목적은 아래 3가지다.

1. `Position`, `Response`, `State`의 owner를 분리한다.
2. `State`가 단순 보조지표 모음이 아니라, 시장 해석과 인내심을 조정하는 레이어임을 고정한다.
3. 나중에 `wait/entry/hold` 보정과 `ML calibration`을 붙일 때 기준점을 만든다.

---

## 한 줄 정의

`State`는

```text
지금 이 반응을 얼마나 믿을지,
얼마나 기다릴지,
얼마나 오래 들고 갈지를 결정하는 시장 상태 레이어
```

다.

즉:

- `Position`이 `어디 있나`
- `Response`가 `무슨 반응이 나왔나`

를 말한다면,

`State`는

```text
그 반응을 지금 장에서 얼마나 신뢰해도 되는가
```

를 말한다.

---

## State가 왜 중요한가

같은 `Response`라도
`State`가 다르면 해석이 완전히 달라진다.

예:

- `lower_hold_up`
  - `RANGE swing state`에서는 좋은 `BUY reversal`
  - `강한 TREND down state`에서는 약한 기술적 반등일 수 있음

- `upper_break_up`
  - `compressed breakout state`에서는 좋은 상방 확장
  - `already expanded exhaustion state`에서는 가짜 돌파일 수 있음

- `mid_reclaim_up`
  - `healthy reclaim state`에서는 재진입 기회
  - `noisy chop state`에서는 그냥 흔들림일 수 있음

즉 `State`가 명확하지 않으면:

- 하단 반등을 너무 믿거나
- 상단 거절을 너무 빨리 믿거나
- 중앙 reclaim/lose를 이상하게 해석하거나
- 기다려야 할 때 못 기다리고
- 반대로 너무 오래 기다리게 된다

---

## State는 무엇이 아니어야 하나

이 경계가 중요하다.

### State가 하면 안 되는 것

- `가격 위치`를 직접 정의
  - 이건 `Position`의 일이다
- `실제 사건`을 직접 감지
  - 이건 `Response`의 일이다
- `BUY / SELL` 방향 자체를 새로 만들기
  - 이건 `Response + Evidence + ObserveConfirm`의 조합이다

즉 `State`는

```text
반응을 만들지 않는다
반응을 해석하고 증폭/감쇠한다
```

가 맞다.

---

## Owner 경계

### `Position`

책임:

- 박스/볼린저/MA/추세선의 위치와 거리 지도
- 크기와 스케일
- edge/middle/anchor 맥락

한 줄:

```text
지금 어디에 있나
```

### `Response`

책임:

- 지지/저항에서 어떤 사건이 나왔나
- 추세선에서 어떤 사건이 나왔나
- 1M / 5M에서 어떤 전환 반응이 나왔나
- candle/structure motif가 무엇을 말하나

한 줄:

```text
지금 무슨 일이 일어났나
```

### `State`

책임:

- 지금 장이 `range/trend/shock` 중 무엇인가
- 지금 반응이 얼마나 신뢰할 만한가
- 지금 얼마나 기다려야 하는가
- 지금 얼마나 오래 들고 갈 가치가 있는가

한 줄:

```text
이 반응을 지금 얼마나 믿고, 얼마나 참을 것인가
```

---

## 현재 코드에서 State가 실제로 하는 일

현재 구현은 아래 파일들에 있다.

- [builder.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
- [quality_state.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/quality_state.py)
- [regime_state.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/regime_state.py)
- [coefficients.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/coefficients.py)
- [models.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)

현재 구조를 요약하면:

### `StateRawSnapshot`

현재 raw 입력은 대체로 아래 수준이다.

- `market_mode`
- `direction_policy`
- `liquidity_state`
- `s_noise`
- `s_conflict`
- `s_alignment`
- `s_disparity`
- `s_volatility`

즉 현재 `StateRawSnapshot`은

```text
regime + quality 요약치
```

에 가깝다.

### `StateVectorV2`

현재 최종 상태 벡터는 아래 항목들을 만든다.

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`

즉 현재 `State`는 실제로

```text
gain / damp / penalty를 만드는 보정기
```

역할을 하고 있다.

이건 방향 자체를 만드는 레이어라기보다,
뒤에서 `Evidence`와 실행층을 조절하는 `계수 생성기`다.

---

## 현재 State의 장점

현재 구조의 장점은 분명히 있다.

### 장점 1. 역할이 비교적 깨끗하다

현재 State는 적어도:

- 위치를 직접 만들지 않고
- 사건을 직접 만들지 않고
- 보정 계수로 행동한다

는 점에서 방향이 나쁘지 않다.

### 장점 2. `market_mode`에 따라 반응 성격을 나눈다

예:

- `RANGE`면 `range_reversal_gain`을 올리고
- `TREND`면 `trend_pullback_gain`, `breakout_continuation_gain`을 올린다

이건 아주 좋은 시작점이다.

### 장점 3. noise/conflict/liquidity/volatility를 별도 패널티로 본다

즉 `좋아 보이는 반응이라도 지금은 믿지 말자`는 개념이 이미 있다.

---

## 현재 State의 한계

하지만 지금 State는 아직 충분히 명확하지 않다.

### 한계 1. `큰지도 해석`이 State owner로 완전히 올라오지 않았다

우리는 이미:

- `D1 / H4 / H1 / M30 / M15` MA big map
- `MTF trendline map`

을 만들었다.

하지만 지금 이 값들은 대부분:

- `Position metadata`
- 혹은 후보 메타데이터

로 남아 있고,
`State`의 정식 owner로 들어간 건 아직 아니다.

즉 지금 `State`는

```text
큰 방향을 얼마나 신뢰할지
```

를 충분히 자기 책임으로 말하지 못한다.

### 한계 2. `wait patience`와 `hold patience`를 State가 직접 말하지 않는다

현재는:

- `ObserveConfirm`
- `Barrier`
- `WaitEngine`
- `ExitProfileRouter`

쪽에서 기다림과 보유를 많이 결정한다.

그런데 그때 근본적으로 필요한 것은:

```text
지금 이 장은 기다릴 가치가 큰가
지금 이 장은 빨리 잘라야 하는가
지금 이 장은 반대 edge까지 버틸 가치가 있는가
```

를 `State`가 먼저 말해주는 것이다.

이 부분은 아직 약하다.

### 한계 3. `range swing`과 `trend continuation` 같은 운영 성격이 명시적 상태로 분리되지 않았다

지금은 `market_mode=RANGE/TREND/SHOCK`가 중심인데,
실전에서는 이보다 더 세밀한 운영 상태가 필요하다.

예:

- `range_swing_state`
- `trend_pullback_state`
- `breakout_expansion_state`
- `exhaustion_state`
- `chop_noise_state`

즉 지금은 `거친 분류`는 있지만
`운영에 바로 쓰는 상태 표현`은 부족하다.

---

## 앞으로 State가 체계적으로 책임져야 할 것

이제부터는 State를 아래 4개 층으로 보는 것이 가장 자연스럽다.

```text
State
= Regime State
+ Quality State
+ Topdown Bias State
+ Patience / Execution State
```

---

## 1. Regime State

이 층은:

```text
지금 시장이 어떤 종류의 장인가
```

를 말한다.

### 책임

- `RANGE`
- `TREND`
- `SHOCK`
- 필요하면 더 세밀한 하위 상태

예:

- `RANGE_SWING`
- `TREND_PULLBACK`
- `BREAKOUT_EXPANSION`
- `CHOP_NOISE`
- `EXHAUSTION`

### 입력

- `market_mode`
- 변동성
- 추세 정렬
- big map bias
- 박스/밴드 크기

### 출력

- reversal을 키울지
- breakout을 키울지
- pullback을 baseline으로 볼지

즉 현재의

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`

은 이 층의 일부로 보면 된다.

---

## 2. Quality State

이 층은:

```text
지금 반응을 얼마나 믿을 만한 장인가
```

를 말한다.

### 책임

- noise
- conflict
- liquidity
- spread
- volatility quality
- disparity 과열 정도
- alignment 품질

### 입력

- `s_noise`
- `s_conflict`
- `s_alignment`
- `s_disparity`
- `s_volatility`
- `liquidity_state`
- `spread_ratio`
- `position_conflict_score`

### 출력

- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `liquidity_penalty`
- `volatility_penalty`

즉 현재 구현의 핵심은 이 층에 있다.

---

## 3. Topdown Bias State

이 층은:

```text
큰지도는 지금 어느 쪽을 더 믿고 있는가
```

를 말한다.

### 책임

- 상위 MA/추세선 정렬 해석
- 상위 방향과 현재 위치의 관계
- 큰지도와 현재 micro 반응의 정합성

### 입력

- `mtf_ma_big_map_v1`
- `mtf_trendline_map_v1`
- `mtf_ma_weight_profile_v1`
- `mtf_trendline_weight_profile_v1`
- `stack_state`
- `raw_bias`
- `bull_bias_weight`
- `bear_bias_weight`

### 출력

- `topdown_bull_bias`
- `topdown_bear_bias`
- `countertrend_penalty`
- `big_map_agreement_score`

즉 현재 metadata로만 흩어져 있는 큰지도 해석을
앞으로는 `State` 정식 owner로 끌어와야 한다.

---

## 4. Patience / Execution State

이 층은:

```text
지금 얼마나 기다릴지, 얼마나 빨리 확정할지, 얼마나 오래 들고 갈지
```

를 말한다.

이게 앞으로 가장 중요해질 가능성이 크다.

### 책임

- 지금 `WAIT`이 좋은 WAIT인지
- 지금 `CONFIRM`을 빨리 줘야 하는지
- 지금 `hold patience`를 더 줘야 하는지
- 지금 `tight protect`를 빨리 걸어야 하는지

### 입력

- Regime State 결과
- Quality State 결과
- Topdown Bias State 결과
- Position conflict/middle/edge 성격

### 출력

- `wait_patience_gain`
- `confirm_aggression_gain`
- `hold_patience_gain`
- `fast_exit_risk_penalty`

이 층이 명확해지면
지금 문제인:

- `WAIT 과보수`
- `조금만 먹고 바로 파는 청산`

을 더 자연스럽게 풀 수 있다.

---

## State가 실제로 영향을 줘야 하는 곳

State는 단독 신호가 아니라
다른 레이어의 `행동 강도`를 조절해야 한다.

### 1. `Evidence`

State는 `Evidence`에 가장 직접적으로 들어간다.

예:

- `RANGE`면 `buy/sell reversal evidence`를 강화
- `TREND`면 `breakout/continuation evidence`를 강화
- `noise/conflict`가 크면 evidence 전체를 약화

### 2. `Belief`

State는 `Belief`의 persistence에도 간접 영향 줄 수 있다.

예:

- 건강한 trend state면 belief를 빨리 쌓게
- chop/noise state면 belief를 늦게 쌓게

### 3. `Barrier`

State는 barrier의 근거가 된다.

예:

- `middle chop state`
- `bad liquidity state`
- `shock state`

이면 barrier를 키운다.

### 4. `ObserveConfirm`

State는 `지금 들어갈지 / 기다릴지`를 조정해야 한다.

예:

- `range_swing state`에서는 edge reversal을 빨리 confirm
- `trend continuation state`에서는 반trend reversal은 더 오래 observe

### 5. `Exit / WaitEngine`

State는 `얼마나 오래 들고 갈지`에도 영향을 줘야 한다.

예:

- `range_swing state`면 반대 edge까지 hold bias 강화
- `shock state`면 fast exit 성향 강화

---

## 앞으로의 State 정의안

아래처럼 정리하는 것이 가장 체계적이다.

## State Raw

현재보다 약간 확장된 raw 입력:

- `market_mode`
- `direction_policy`
- `liquidity_state`
- `s_noise`
- `s_conflict`
- `s_alignment`
- `s_disparity`
- `s_volatility`
- `mtf_big_map_bias`
- `mtf_stack_state`
- `compression_score`
- `expansion_score`
- `position_conflict_score`
- `middle_neutrality`

## State Semantic Buckets

이 raw를 아래 semantic bucket으로 나눈다.

### `regime_state`

- `RANGE_SWING`
- `TREND_PULLBACK`
- `BREAKOUT_EXPANSION`
- `CHOP_NOISE`
- `SHOCK`
- `EXHAUSTION`

### `quality_state`

- `HIGH_QUALITY`
- `MEDIUM_QUALITY`
- `LOW_QUALITY`

### `topdown_state`

- `BULL_ALIGNED`
- `BEAR_ALIGNED`
- `MIXED_TOPDOWN`
- `COUNTERTREND`

### `patience_state`

- `WAIT_FAVOR`
- `CONFIRM_FAVOR`
- `HOLD_FAVOR`
- `FAST_EXIT_FAVOR`

즉 미래의 State는 단순 숫자 계수뿐 아니라,
사람이 읽을 수 있는 semantic label도 같이 갖는 것이 좋다.

---

## 추천 출력 형태

현재 `StateVectorV2`를 유지하되,
장기적으로는 아래 성격으로 확장하는 것이 좋다.

### 계수 출력

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

### semantic metadata 출력

- `regime_state_label`
- `quality_state_label`
- `topdown_state_label`
- `patience_state_label`
- `state_owner_contract`

즉:

```text
숫자 + 의미 라벨
```

을 같이 가지는 것이 좋다.

---

## 가장 중요한 결론

지금까지의 문맥에서 `State`는
단순한 보조지표 통합기가 아니다.

`State`는 앞으로 명확히 아래 역할을 해야 한다.

1. `지금 시장이 어떤 종류의 장인지`
2. `지금 신호를 얼마나 믿을지`
3. `지금 얼마나 기다릴지`
4. `지금 얼마나 오래 들고 갈지`

즉 State를 한 줄로 다시 정의하면:

```text
State는 Position과 Response가 만든 후보 신호의
신뢰도, 인내심, 운영 성격을 조정하는 시장 상태 레이어다.
```

---

## 바로 다음 단계 제안

이제 가장 자연스러운 다음 단계는 두 가지다.

### 1. `현재 State`와 `원하는 State`의 차이를 표로 고정

즉:

- 현재는 무엇이 구현돼 있고
- 무엇이 메타데이터에만 있고
- 무엇이 아직 없는지

를 표로 고정한다.

### 2. `State vNext`에서 먼저 가져올 항목을 결정

추천 우선순위:

1. `Topdown Bias State`
2. `Patience / Execution State`
3. 그 다음 `regime 하위 상태 세분화`

왜냐하면 지금 병목이

- `WAIT 과보수`
- `edge turn confirm 부족`
- `조기청산`

쪽이므로,
바로 체감이 큰 것은 `topdown + patience` 쪽이기 때문이다.
