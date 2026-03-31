# Symbol / Regime Adaptive Semantic Calibration Proposal

## 목적

이 문서는 아래 문제를 구체적으로 다루기 위한 제안서다.

- 같은 `Position / Response / State` 구조를 써도
  `NAS100`, `XAUUSD`, `BTCUSD`는 같은 순간에 전혀 다른 성격으로 움직인다.
- 같은 공식으로 계산해도
  심볼, 시장모드, 변동성, 미세 반응이 달라지면
  어떤 축을 더 믿어야 하는지도 달라진다.
- 이 차이를 사람이 규칙으로 끝없이 박아넣기보다,
  `semantic structure는 고정`하고 `숫자와 threshold만 ML이 보정`하는 편이 더 낫다.

즉 목표는 이거다.

```text
의미 구조는 유지
-> 심볼/상황마다 어떤 축을 더 믿을지
-> 얼마나 기다릴지
-> 얼마나 오래 들고 갈지
를 ML로 보정
```

---

## 지금 왜 같은 코드인데 값이 다르게 나오나

겉으로는 같은 수식이지만,
실제로는 각 심볼에 들어가는 입력이 다르기 때문에 값이 달라진다.

### 같은 것

- `transition_vector.py`
- `context_gate.py`
- `evidence_engine.py`
- `observe_confirm_router.py`

즉 계산 공식 자체는 동일하다.

### 달라지는 것

하지만 아래 입력은 심볼마다 매 시점 다르다.

- `Position`
  - `box_state`
  - `bb_state`
  - `primary_label`
  - `secondary_context_label`
  - `position_conflict_score`
  - `map_size_state`
- `Response raw`
  - `S/R strength`
  - `trendline strength`
  - `micro 1M/5M strength`
  - candle / pattern / motif
- `Context Gate`
  - `support_anchor`
  - `resistance_anchor`
  - `bull_reversal_gate`
  - `bear_reversal_gate`
  - `bull_break_gate`
  - `bear_break_gate`
  - `ambiguity_penalty`
- `State`
  - `market_mode`
  - `TREND / RANGE / SHOCK`
  - volatility
  - spread
  - liquidity

즉:

```text
공식은 같지만
입력 feature가 다르므로
출력 6축도 다르다
```

이건 이상한 현상이 아니라 정상이다.

문제는 그 다음이다.

```text
그 다른 입력 차이를
사람이 매번 수동 규칙으로 얼마나 잘 흡수할 수 있느냐
```

여기서 ML 보정이 필요해진다.

---

## 현재 관찰에서 보이는 실제 차이

최근 live 관찰을 기준으로 보면:

- `NAS100`
  - 하단 붕괴 쪽 재료가 더 많이 들어온다
  - `trend_support_break_strength`
  - `micro_bear_break_strength`
  - `micro_bear_reject_strength`
  쪽이 강하다
- `XAUUSD`
  - 중앙/하단 혼합형으로 나온다
  - `lower_hold_up`와 `mid_lose_down`가 비슷해진다
  - ambiguity가 커서 `WAIT`가 자연스럽다
- `BTCUSD`
  - 하단 컨텍스트인데 상방 micro break가 같이 살아난다
  - `trend_resistance_break_strength`
  - `micro_bull_break_strength`
  - `micro_bull_reject_strength`
  가 같이 들어와 conflict가 생긴다

즉 같은 `Response 6축` 구조를 쓰더라도,
심볼과 장 상황에 따라
더 믿어야 할 축과 덜 믿어야 할 축이 달라진다.

바로 이 부분을 ML이 다루게 하면 된다.

---

## 가장 중요한 전제

### ML이 하면 안 되는 것

ML이 아래를 직접 새로 결정하면 안 된다.

- `Position / Response / State`의 owner 구조
- `lower_hold_up`, `lower_break_down` 같은 축 의미 정의
- `BUY / SELL side`의 의미 자체
- `archetype_id`
- `management_profile_id`
- `invalidation_id`

즉 ML은 `의미 자체`를 만들면 안 된다.

### ML이 해야 하는 것

ML은 아래를 조정해야 한다.

- 축별 신뢰도 multiplier
- ambiguity penalty 강도
- wait/confirm threshold
- hold/exit patience
- symbol / regime bias

즉:

```text
semantic meaning = 사람이 정의
numeric trust = ML이 조정
```

이게 핵심이다.

---

## 추천 구조

## 1. Base Semantic Engine

이건 지금처럼 유지한다.

```text
Position
Response
State
Evidence
Belief
Barrier
-> ObserveConfirm
-> Exit / Wait
```

즉 현재의 semantic pipeline은 그대로 둔다.

---

## 2. ML Calibrator Layer

semantic output 위에 따로 붙는 얇은 조정층이다.

```text
semantic features
-> ML calibrator
-> axis/threshold/wait/hold 보정값
```

이 층은 아래처럼 동작하면 가장 좋다.

### axis calibration

```text
adjusted_lower_hold
= lower_hold_up * w_lower_hold(context)

adjusted_lower_break
= lower_break_down * w_lower_break(context)

adjusted_upper_reject
= upper_reject_down * w_upper_reject(context)

adjusted_upper_break
= upper_break_up * w_upper_break(context)
```

### ambiguity calibration

```text
adjusted_ambiguity
= ambiguity_penalty * w_ambiguity(context)
```

### wait / confirm calibration

```text
confirm_threshold'
= base_confirm_threshold + delta_confirm(context)

wait_bias'
= base_wait_bias + delta_wait(context)
```

### hold / exit calibration

```text
hold_patience'
= base_hold_patience + delta_hold(context)

early_exit_penalty'
= base_early_exit_penalty + delta_exit(context)
```

즉 ML은 semantic result를 대체하는 게 아니라,
semantic result에 `조정치`를 덧붙이는 역할이다.

---

## 어떤 컨텍스트를 보고 조정하나

ML이 보는 입력은 현재 이미 시스템이 잘 만들고 있는 semantic feature들이면 충분하다.

## A. Position 입력

- `position_primary_label`
- `position_secondary_context_label`
- `position_conflict_score`
- `middle_neutrality`
- `map_size_state`
- `compression_score`
- `expansion_score`
- `x_box`
- `x_bb20`
- `x_bb44`
- `x_tl_m1 / m15 / h1 / h4`
- `tl_proximity_*`
- `mtf_ma_big_map_v1`
- `mtf_trendline_map_v1`

## B. Response 입력

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`
- `response_context_gate_v1.pre_axis_candidates`
- `sr_subsystem_v1.strengths`
- `trendline_subsystem_v1.strengths`
- `micro_tf_subsystem_v1.strengths`
- `candle_motif_v1`
- `structure_motif_v1`

## C. State 입력

- `market_mode`
- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `liquidity_penalty`
- `volatility_penalty`

## D. Decision / Execution 입력

- `observe_confirm_v2.action`
- `observe_confirm_v2.side`
- `observe_confirm_v2.reason`
- `observe_confirm_v2.confidence`
- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`

## E. Symbol / market context 입력

- `symbol`
- `session`
- `spread_ratio`
- `volatility_ratio`
- `regime_name`

이 정도면 `심볼/상황별 적응`에는 충분하다.

---

## ML을 4개 문제로 나누는 게 좋다

이건 매우 중요하다.

`좋은 진입`, `좋은 기다림`, `좋은 보유`, `많은 수익`은 같은 문제가 아니다.

한 모델에 전부 몰아넣으면 과최적화되기 쉽다.

그래서 아래처럼 나누는 게 좋다.

## 1. Wait Quality Model

질문:

```text
지금 기다리는 게 좋은 wait인가
아니면 기회손실 wait인가
```

예:

- 좋은 wait
  - 조금 더 기다리면 더 좋은 진입이 나온다
  - 지금 진입하면 adverse가 큰데 wait 뒤엔 개선된다
- 나쁜 wait
  - 이미 가장 좋은 자리였는데 놓쳤다
  - wait 후 더 나쁜 가격에서만 들어가게 된다

추천 target:

- `good_wait_probability`

추천 label 예시:

```text
wait_quality
= future_best_entry_quality_within_k
- current_entry_quality
- missed_move_penalty
```

---

## 2. Entry Quality Model

질문:

```text
지금 이 진입이 좋은 진입점인가
```

예:

- 진입 직후 favorable move가 잘 나온다
- 초기 MAE가 작다
- false break가 아니다

추천 target:

- `good_entry_probability`

추천 label 예시:

```text
entry_quality
= favorable_excursion
- adverse_excursion
- false_break_penalty
- churn_penalty
```

---

## 3. Hold / Exit Model

질문:

```text
지금은 들고 가야 하나
지금은 끊어야 하나
```

예:

- 지금 안 팔면 TP1/반대쪽 edge로 더 갈 확률이 높다
- 지금 안 팔면 다시 손실로 되돌아갈 가능성이 높다

추천 target:

- `hold_better_than_exit_probability`

추천 label 예시:

```text
hold_quality
= future_hold_value
- immediate_exit_value
- extra_drawdown_penalty
- overstay_penalty
```

---

## 4. Utility / Expectancy Model

질문:

```text
이 선택의 기대값이 있는가
```

추천 target:

- `expected_return`
- `expected_drawdown`
- `expected_hold_time`
- `expected_utility`

추천 목적함수 예시:

```text
utility
= pnl
- 0.7 * drawdown
- 0.2 * overstay_penalty
- 0.3 * churn_penalty
```

여기서 `churn_penalty`는 특히 중요하다.

지금 시스템이 싫어하는 현상:

- 자잘한 손절 반복
- 금방 들어갔다가 금방 나옴
- 같은 구간에서 연속 진입/연속 청산

이걸 직접 벌점으로 넣어야 한다.

---

## 더 나은 조언: DL보다 먼저 ML이 맞다

여기서 가장 중요한 조언은 이거다.

### 지금은 DL보다 ML이 먼저다

이유:

- 이미 semantic feature가 아주 잘 정리돼 있다
- `Position / Response / State`가 구조화된 표 feature로 존재한다
- explainability가 중요하다
- 잘못됐을 때 원인을 다시 볼 수 있어야 한다

따라서 1차 추천은:

- LightGBM
- XGBoost
- CatBoost
- Logistic calibration
- Isotonic / Platt scaling

이다.

### DL은 어디에 늦게 들어오면 좋나

DL은 나중에 아래 용도로 고려하면 좋다.

- `1M / 5M` raw 시퀀스 자체
- micro candle sequence embedding
- regime sequence encoder

즉 DL은 semantic structure를 대체하는 게 아니라,
나중에 micro sequence를 더 정교하게 읽을 때 보조로 쓰는 편이 낫다.

---

## 더 나은 조언: per-symbol 모델보다 shared model + symbol feature가 낫다

처음부터

- `NAS용 모델`
- `XAU용 모델`
- `BTC용 모델`

이렇게 나누면 데이터가 금방 부족해진다.

처음은 아래가 더 좋다.

```text
공용 모델 1개
+ symbol feature
+ regime feature
+ session feature
```

즉:

- 모델은 공유
- 심볼 차이는 feature로 표현

이 방식이 더 안정적이다.

그 다음에 정말 필요할 때만
심볼별 calibration head를 붙이는 게 좋다.

---

## 더 나은 조언: 조정폭은 bounded 해야 한다

이 부분이 아주 중요하다.

ML이 가중치를 무제한으로 흔들면
semantic structure가 무너진다.

그래서 조정치는 bounded 해야 한다.

예:

```text
w_axis(context) ∈ [0.75, 1.25]
delta_confirm(context) ∈ [-0.08, +0.08]
delta_wait(context) ∈ [-0.10, +0.10]
delta_hold(context) ∈ [-0.15, +0.15]
```

즉 ML은

- semantic meaning을 뒤집지 않고
- 신뢰도와 인내심을 조절만 하게 해야 한다

이게 훨씬 안전하다.

---

## 더 나은 조언: 첫 적용은 꼭 shadow여야 한다

적용 순서는 이게 가장 좋다.

## 1단계. Dataset 만들기

로그에서 아래를 모은다.

- entry row
- wait row
- hold / exit row
- trade closed result

## 2단계. Shadow inference

실시간으로 모델은 돌리되
아직 live gate는 바꾸지 않는다.

즉:

- `model says wait`
- `model says confirm`
- `model says hold`

를 그냥 로그로만 남긴다.

## 3단계. Calibration only

그 다음에야 아래만 반영한다.

- threshold shift
- penalty shift
- hold patience shift

## 4단계. Never hand over identity

아래는 계속 사람이 owner다.

- side
- archetype
- invalidation
- management profile

이 원칙을 깨면 system drift가 커진다.

---

## 가장 추천하는 첫 실무 버전

지금 구조에 바로 붙이기 좋은 첫 버전은 이거다.

## Model A. Wait Quality

출력:

- `good_wait_probability`

사용:

- `ObserveConfirm` wait bias 보정
- `outer_band_reversal_support_required_observe` 같은 대기를 덜/더 보수적으로 조정

## Model B. Entry Quality

출력:

- `good_entry_probability`

사용:

- candidate 상위축의 confirm threshold 조정
- `WAIT -> CONFIRM` 경계 보정

## Model C. Hold / Exit

출력:

- `hold_better_than_exit_probability`

사용:

- `ExitProfileRouter`
- `WaitEngine`
- 조기청산 억제

즉 첫 버전은

```text
wait
entry
hold/exit
```

이 3개면 충분하다.

`utility`는 그다음이다.

---

## 지금 구조에서 가장 잘 맞는 적용 포인트

### Response 6축 calibration

예:

```text
adjusted_axis
= base_axis * axis_multiplier(context)
```

적용 후보:

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

### Context gate calibration

예:

```text
adjusted_ambiguity
= ambiguity_penalty * ambiguity_multiplier(context)
```

적용 후보:

- `ambiguity_penalty`
- `bull_reversal_gate`
- `bear_reversal_gate`
- `bull_break_gate`
- `bear_break_gate`

### Observe / Wait calibration

예:

```text
confirm_threshold'
= confirm_threshold + delta_confirm(context)
```

적용 후보:

- `WAIT vs OBSERVE`
- `OBSERVE vs CONFIRM`
- `conflict observe` 완화/강화

### Exit / Hold calibration

적용 후보:

- `hold bias`
- `BE wait`
- `TP1 wait`
- `early exit penalty`

---

## 추천 우선순위

### 1순위

`Wait Quality`

이유:

- 지금 체감 병목이 `읽고도 WAIT가 너무 많음`
  쪽으로 보이는 케이스가 많다
- 따라서 먼저 `좋은 기다림 / 나쁜 기다림`을 가르는 게 좋다

### 2순위

`Entry Quality`

이유:

- wait 다음으로 중요한 건 실제 진입 품질이다
- `Response는 맞는데 confirm으로 안 넘어감` 문제도 여기와 연결된다

### 3순위

`Hold / Exit`

이유:

- 조기청산 문제는 여전히 중요하다
- 하지만 먼저 wait/entry가 정리돼야 해석이 쉬워진다

---

## 최종 제안

가장 안전하고 강한 방향은 이거다.

```text
1. semantic structure는 그대로 둔다
2. ML은 wait / entry / hold의 수치만 조정한다
3. shared model + symbol/regime/session feature로 시작한다
4. axis/threshold 조정폭은 bounded 한다
5. 첫 적용은 반드시 shadow로 한다
6. side/archetype/management profile ownership은 끝까지 semantic 쪽에 남긴다
```

---

## 한 줄 결론

지금처럼 `NAS`, `XAU`, `BTC`가 같은 구조 안에서도 서로 다른 재료를 받아 다르게 해석되는 환경에서는, semantic 구조를 고정한 채 `symbol + regime + response context`를 입력으로 받아 축 가중치, wait/confirm 경계, hold/exit 인내심을 조정하는 ML calibrator를 두는 방식이 가장 적절하다.
