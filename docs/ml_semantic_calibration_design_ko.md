# ML Semantic Calibration Design

## 목적

이 문서는 현재 `PRSEBB + ObserveConfirm + Exit/Wait` 구조를 유지한 상태에서,
`ML`을 **의미 구조를 대체하는 엔진**이 아니라 **숫자와 threshold를 보정하는 calibrator**로 쓰는 방법을 정리한다.

핵심 원칙은 아래와 같다.

- 의미 구조의 owner는 계속 사람이 정한다.
- `Position / Response / State / Evidence / Belief / Barrier`의 역할은 유지한다.
- ML은 이 구조가 만들어낸 수치와 경계값을 더 잘 맞추는 데만 쓴다.
- 즉, `semantic structure first, ML calibration second`가 기본 원칙이다.


## 한 줄 결론

```text
사람이 의미를 만든다
-> 시스템이 semantic feature를 만든다
-> ML이 그 semantic feature의 숫자/threshold/가중치를 보정한다
```


## 왜 이렇게 해야 하나

`좋은 진입`, `좋은 청산`, `많은 수익`은 서로 다른 목표다.

- 좋은 진입:
  - 초반 adverse move가 작고
  - 유리한 방향으로 출발하는가
- 좋은 청산:
  - 너무 빨리 털지 않고
  - 너무 늦게 버티지도 않는가
- 많은 수익:
  - 순이익이 크고
  - drawdown, churn, overstay가 적은가

이 세 개를 한 번에 black-box로 최적화하면 쉽게 꼬인다.
그래서 ML도 최소한 아래 3개의 하위 문제로 쪼개는 것이 안전하다.

- `Entry Quality Calibration`
- `Hold / Exit Calibration`
- `Utility / Expectancy Calibration`


## 구조에서 ML이 들어가는 위치

```text
Position
Response
State
Evidence
Belief
Barrier
-> ObserveConfirm
-> Exit / Wait / ReEntry
```

여기서 ML은 아래처럼 들어간다.

- `Position`:
  - zone threshold
  - proximity blend
  - map size / trendline / MA 보조 weight
- `Response`:
  - subsystem blend
  - motif 기여 비율
  - context gate 강도
  - 6축 재결선 비율
- `State`:
  - range / trend / shock 보정
  - 큰지도 gain / damp
- `Evidence`:
  - reversal / continuation blend
  - confirm / wait 경계값
- `Belief`:
  - persistence 민감도
  - EMA / streak 반응 속도
- `Barrier`:
  - ambiguity penalty
  - chop / conflict / liquidity 억제 강도
- `Exit / Wait`:
  - hold bias
  - BE 조건
  - reverse 허용 타이밍

즉 ML은 **의미를 새로 만들지 않고, 현재 의미 구조의 숫자를 더 잘 맞춘다.**


## 절대 ML에 넘기면 안 되는 것

아래는 black-box가 owner가 되면 안 된다.

- `Position / Response / State`의 역할 구분 자체
- `support_hold`와 `support_break`의 의미 정의
- `upper_reject`와 `upper_break`의 의미 정의
- `archetype_id`
- `side`의 semantic ownership
- `management_profile_id`
- `invalidation_id`

즉 아래 질문은 사람이 계속 책임져야 한다.

- 지금 하단 반등인가
- 지금 하단 붕괴인가
- 지금 상단 거절인가
- 지금 상단 돌파인가
- 어떤 archetype인가


## 현재 실제로 쓸 수 있는 입력 feature

아래는 현재 런타임에서 실제로 확인된 주요 semantic feature다.

### Position 계층

- `position_vector_v2`
  - `x_box`
  - `x_bb20`
  - `x_bb44`
  - `x_ma20`
  - `x_ma60`
  - `x_sr`
  - `x_trendline`
- `position_interpretation_v2`
  - `primary_label`
  - `alignment_label`
  - `bias_label`
  - `conflict_kind`
  - `dominance_label`
  - `secondary_context_label`
  - `pos_composite`
- `position_energy_v2`
  - `upper_position_force`
  - `lower_position_force`
  - `middle_neutrality`
  - `position_conflict_score`

### Position metadata

- `position_interpretation_v2.metadata.position_scale`
  - `box_height`
  - `bb20_width`
  - `bb44_width`
  - `box_size_state`
  - `bb20_width_state`
  - `bb44_width_state`
  - `map_size_state`
  - `compression_score`
  - `expansion_score`
- `position_interpretation_v2.metadata.mtf_ma_big_map_v1`
- `position_interpretation_v2.metadata.mtf_trendline_map_v1`

### Response raw 계층

- `response_raw_snapshot_v1`
  - 기존 BB / Box raw
  - `candle_lower_reject`
  - `candle_upper_reject`
  - `pattern_double_bottom`
  - `pattern_inverse_head_shoulders`
  - `pattern_double_top`
  - `pattern_head_shoulders`
  - `sr_*`
  - `trend_*`
  - `micro_*`

### Response metadata

- `response_raw_snapshot_v1.metadata.candle_descriptor_v1`
- `response_raw_snapshot_v1.metadata.candle_pattern_v1`
- `response_raw_snapshot_v1.metadata.candle_motif_v1`
- `response_raw_snapshot_v1.metadata.structure_motif_v1`
- `response_raw_snapshot_v1.metadata.sr_subsystem_v1`
- `response_raw_snapshot_v1.metadata.trendline_subsystem_v1`
- `response_raw_snapshot_v1.metadata.micro_tf_subsystem_v1`
- `response_raw_snapshot_v1.metadata.response_context_gate_v1`

### Response 6축

- `response_vector_v2`
  - `lower_hold_up`
  - `lower_break_down`
  - `mid_reclaim_up`
  - `mid_lose_down`
  - `upper_reject_down`
  - `upper_break_up`

### State

- `state_vector_v2`
  - `range_reversal_gain`
  - `trend_pullback_gain`
  - `breakout_continuation_gain`
  - `noise_damp`
  - `conflict_damp`
  - `alignment_gain`
  - `countertrend_penalty`
  - `liquidity_penalty`
  - `volatility_penalty`

### Evidence / Belief / Barrier

- `evidence_vector_v1`
  - `buy_reversal_evidence`
  - `sell_reversal_evidence`
  - `buy_continuation_evidence`
  - `sell_continuation_evidence`
  - `buy_total_evidence`
  - `sell_total_evidence`
- `belief_state_v1`
  - `buy_belief`
  - `sell_belief`
  - `buy_persistence`
  - `sell_persistence`
  - `belief_spread`
  - `transition_age`
- `barrier_state_v1`
  - `buy_barrier`
  - `sell_barrier`
  - `conflict_barrier`
  - `middle_chop_barrier`
  - `direction_policy_barrier`
  - `liquidity_barrier`

### Forecast / Execution

- `transition_forecast_v1`
  - `p_buy_confirm`
  - `p_sell_confirm`
  - `p_false_break`
  - `p_reversal_success`
  - `p_continuation_success`
- `trade_management_forecast_v1`
  - `p_continue_favor`
  - `p_fail_now`
  - `p_recover_after_pullback`
  - `p_reach_tp1`
  - `p_opposite_edge_reach`
  - `p_better_reentry_if_cut`
- `forecast_gap_metrics_v1`
  - `transition_side_separation`
  - `transition_confirm_fake_gap`
  - `transition_reversal_continuation_gap`
  - `management_continue_fail_gap`
  - `management_recover_reentry_gap`
- `observe_confirm_v2`
  - `state`
  - `action`
  - `side`
  - `confidence`
  - `reason`
  - `archetype_id`
  - `invalidation_id`
  - `management_profile_id`


## ML 문제를 4개로 쪼개는 방법

## 1. Wait Quality Calibration

### 질문

```text
지금 기다리는 게 좋은 기다림인가, 나쁜 기다림인가?
```

### 왜 별도 owner가 필요한가

`WAIT`는 단순히 "아직 안 들어감"이 아니다.

실전에서 wait는 최소 3가지로 나뉜다.

- 좋은 기다림
  - 조금만 더 기다리면 훨씬 좋은 자리에서 들어갈 수 있음
  - 애매한 자리에서 불필요한 진입을 막음
- 나쁜 기다림
  - 이미 좋은 진입을 놓치고 있음
  - confirm이 너무 늦어서 수익 구간을 잃음
- 중립 기다림
  - 아직 어느 쪽도 유의미하지 않음

즉 `wait`는 단순 부정이 아니라 별도의 품질 판단 대상이다.

### 현재 구조에서 wait owner

- 엔트리 wait:
  - `observe_confirm_v2`
  - `barrier_state_v1`
  - `WaitEngine`
- 보유 중 wait:
  - `ExitProfileRouter`
  - `WaitEngine`
  - `ExitManagePositions`

즉 ML도 wait를 아래처럼 분리해서 보는 것이 맞다.

- `entry_wait_quality`
- `exit_wait_quality`

### 입력 feature

- `position_interpretation_v2`
- `position_energy_v2`
- `position_scale`
- `response_vector_v2`
- `response_context_gate_v1`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`
- `transition_forecast_v1`
- `trade_management_forecast_v1`
- `forecast_gap_metrics_v1`
- `observe_confirm_v2`

추가로 wait에는 아래 값이 특히 중요하다.

- `observe_confirm_v2.state`
- `observe_confirm_v2.reason`
- `observe_confirm_v2.confidence`
- `barrier_state_v1.conflict_barrier`
- `barrier_state_v1.middle_chop_barrier`
- `response_context_gate_v1.pre_axis_candidates`
- `response_vector_v2.metadata.axis_candidate_scores`

### label 후보

#### entry_wait_quality_label

질문:

```text
지금 WAIT했는데, 실제로 조금 뒤에 더 좋은 진입이 나왔는가?
```

좋은 wait 예시:

- 지금 WAIT
- K봉 이내에 더 높은 entry_quality의 같은 방향 진입이 출현
- 현재 진입했을 때보다 adverse excursion이 작아짐

나쁜 wait 예시:

- 지금 WAIT
- 실제로는 이미 좋은 진입점이었고
- K봉 뒤엔 더 나쁜 가격 / 더 낮은 품질만 남음

즉 label은 아래처럼 만들 수 있다.

```text
entry_wait_quality
= future_best_entry_quality_within_k
- current_entry_quality
- missed_move_penalty
```

#### exit_wait_quality_label

질문:

```text
지금 청산하지 않고 더 기다리는 게 좋은가?
```

좋은 wait 예시:

- 지금 청산 안 함
- K봉 뒤 더 큰 유리한 move가 나옴
- drawdown 증가가 제한적임

나쁜 wait 예시:

- 지금 안 팔았더니 수익 반환 또는 손실 확대

즉:

```text
exit_wait_quality
= future_hold_value
- immediate_exit_value
- extra_drawdown_penalty
```

### ML이 여기서 할 일

- `WAIT` 경계값 보정
- `observe -> confirm` 전환 타이밍 보정
- `hard_wait / soft_wait / helper_wait` 민감도 조정
- `barrier`가 지나치게 wait를 만들고 있는지 조정
- `좋은 wait`는 살리고 `나쁜 wait`는 줄이는 calibration

### 현재 시스템에서 특히 중요한 이유

지금 시스템의 대표 pain point 중 하나는 아래다.

- 들어가야 할 자리를 너무 기다림
- 기다린 뒤 더 나쁜 자리에서 들어감
- 혹은 너무 일찍 들어가서 wait가 부족함

즉 wait는 entry와 exit 사이에 끼어 있는 부수 기능이 아니라,
별도 최적화 대상이다.


## 2. Entry Quality Calibration

### 질문

```text
지금 이 진입은 좋은 진입인가?
```

### 입력 feature

- `position_vector_v2`
- `position_interpretation_v2`
- `position_energy_v2`
- `position_scale`
- `mtf_ma_big_map_v1`
- `mtf_trendline_map_v1`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`
- `transition_forecast_v1`
- `forecast_gap_metrics_v1`
- `observe_confirm_v2.action`
- `observe_confirm_v2.archetype_id`

### label 후보

- `entry_quality_label`
  - 진입 후 N봉 안에 favorable move가 충분하면 `1`
  - 진입 직후 adverse move가 크면 `0`
- `confirm_success_label`
  - 진입 후 directionally 맞게 출발하면 `1`
- `false_break_label`
  - 진입 직후 fake move면 `1`

### 실무용 목적함수 예시

```text
entry_quality_score
= favorable_excursion
- 0.8 * adverse_excursion
- 0.6 * false_break_penalty
- 0.3 * churn_penalty
```

### ML이 여기서 할 일

- confirm threshold 보정
- wait vs confirm 경계 조정
- `Response 6축 -> Evidence` blend 보정
- 특정 market mode에서 reversal/break 쪽 weight 조정


## 3. Hold / Exit Calibration

### 질문

```text
지금 청산해야 하나, 더 들고 가야 하나?
```

### 입력 feature

- 진입 당시 semantic feature snapshot
- 현재 semantic feature snapshot
- 현재 PnL
- current drawdown
- peak profit
- elapsed bars / elapsed seconds
- `management_profile_id`
- `trade_management_forecast_v1`
- `belief_state_v1`
- `barrier_state_v1`
- `response_vector_v2`

### label 후보

- `hold_better_than_exit`
  - 지금 안 팔고 K봉 더 들고 갔을 때 더 좋으면 `1`
- `exit_better_than_hold`
  - 지금 파는 게 더 낫다면 `1`
- `reach_tp1_label`
- `fail_now_label`
- `opposite_edge_reach_label`

### 실무용 목적함수 예시

```text
hold_utility
= future_best_value_if_hold
- immediate_exit_value_penalty
- 0.7 * extra_drawdown
- 0.3 * overstay_penalty
```

### ML이 여기서 할 일

- `allow_wait_be`, `allow_wait_tp1`, `max_wait_seconds` 보정
- early exit를 줄이는 threshold 조정
- countertrend hold를 더 짧게 / aligned hold를 더 길게 조정


## 4. Utility / Expectancy Calibration

### 질문

```text
이 선택이 기대값이 있는가?
```

### 입력 feature

- Entry Quality 모델 출력
- Hold / Exit 모델 출력
- 전체 semantic feature
- 심볼
- 시장 모드
- 세션 정보

### target 후보

- `expected_return`
- `expected_drawdown`
- `expected_hold_time`
- `expected_win_loss_asymmetry`

### 실무용 목적함수 예시

```text
utility
= pnl
- 0.7 * max_drawdown
- 0.2 * overstay_penalty
- 0.3 * churn_penalty
```

여기서 `churn_penalty`가 중요하다.
현재 시스템이 싫어하는 패턴인

- 자잘한 손실 반복
- 즉시 청산 반복
- 동일 구간 연속 진입

같은 현상을 직접 벌점으로 넣을 수 있다.


## 실제 학습 출력은 무엇으로 쓸까

ML이 곧바로 `BUY/SELL/NONE`을 내리게 하지 말고,
아래처럼 **calibration output**만 내게 하는 것이 좋다.

- `confirm_boost`
- `wait_penalty`
- `barrier_relaxation`
- `barrier_tightening`
- `hold_extension_bias`
- `early_exit_penalty`
- `reentry_cooldown_bias`
- `symbol_regime_bias`

즉 ML은 최종 semantic identity를 만들지 않고,
**이미 나온 의미 구조를 얼마나 더 믿고, 얼마나 더 기다리고, 얼마나 더 보수적으로 볼지**만 조정한다.


## 가장 안전한 학습 파이프라인

## 1단계. 데이터셋 만들기

한 row는 아래 단위로 쪼개는 것이 좋다.

- `entry_decision row`
- `open position management row`
- `close decision row`

### 입력 데이터 source

- [data/runtime_status.json](c:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)
- [data/trades/entry_decisions.csv](c:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [data/trades/trade_history.csv](c:/Users/bhs33/Desktop/project/cfd/data/trades/trade_history.csv)
- [data/trades/trade_closed_history.csv](c:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

### 권장 join key

- `symbol`
- `event_ts`
- `action`
- `setup_id` 또는 `archetype_id`
- `management_profile_id`


## 2단계. Shadow 학습

처음엔 live gate를 절대 바꾸지 않는다.

- 모델은 예측만 한다
- 현재 규칙과 비교만 한다
- 좋은 차이 / 나쁜 차이를 리포트한다

즉 shadow 기간에는:

- `if model says better -> log only`
- `no live override`


## 3단계. Calibration만 반영

바로 모델로 진입시키지 말고 아래부터 시작한다.

- threshold 튜닝
- blend ratio 추천
- ambiguity penalty 보정
- hold duration 보정


## 4단계. 제한적 live 반영

이 단계에서도 owner는 바꾸지 않는다.

허용:

- confidence 조정
- wait vs confirm minor shift
- hold bias / early exit bias 조정

금지:

- archetype 재정의
- side 재정의
- invalidation / management profile owner 변경


## 어떤 알고리즘이 잘 맞나

현재 구조에는 end-to-end black-box보다 아래가 더 잘 맞는다.

- LightGBM
- XGBoost
- CatBoost
- Logistic regression calibration
- Isotonic / Platt scaling
- small ranking model

이유:

- feature 해석 가능
- 특정 축이 왜 먹었는지 볼 수 있음
- shadow 비교가 쉬움
- 과최적화 위험이 덜함


## 추천 우선순위

가장 먼저 손대기 좋은 순서는 아래다.

### 1순위

`Wait Quality Calibration`

이유:

- 지금 시스템은 "기다려야 할 때 못 기다리거나", 반대로 "들어가야 할 때 너무 기다리는" 문제가 직접적인 체감 pain point다
- 이 문제를 해결해야 `Entry Quality`와 `Hold / Exit`도 안정된다

### 2순위

`Entry Quality Calibration`

이유:

- 지금 가장 체감이 큰 문제는 엉뚱한 진입 / 빠른 진입 / 늦은 진입이다
- 현재 semantic feature가 이미 충분히 풍부하다

### 3순위

`Hold / Exit Calibration`

이유:

- 지금 시스템은 `조금만 흔들리면 바로 청산`이 중요한 pain point다
- hold bias와 exit threshold를 ML로 보정할 여지가 크다

### 4순위

`Utility / Expectancy Calibration`

이유:

- 이건 가장 강력하지만 가장 과최적화되기 쉽다
- 앞의 두 모델이 어느 정도 안정된 뒤가 좋다


## 지금 구조에서 바로 쓸 수 있는 실무 버전

```text
입력
= semantic feature bundle

모델 1
= good_wait_probability

모델 2
= good_entry_probability

모델 3
= hold_vs_exit_probability

모델 4
= expected_utility

최종 반영
= threshold / blend / penalty / hold_profile calibration
```


## 최종 요약

- ML은 현재 의미 구조를 대체하면 안 된다.
- ML은 현재 의미 구조의 숫자를 더 잘 맞추는 쪽으로 써야 한다.
- 진입, 보유/청산, 기대수익은 분리해서 학습하는 것이 좋다.
- 첫 적용은 항상 shadow로 시작한다.
- 첫 live 반영은 side/archetype 재정의가 아니라 threshold / calibration부터 시작한다.

가장 중요한 문장 하나만 남기면 이거다.

```text
의미 구조는 사람이 만들고,
수치 최적화는 ML이 한다.
```
