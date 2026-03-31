# State vNext 로드맵

## 목적

이 문서는 `State`를 다음 단계로 끌어올리기 위한 실제 실행 로드맵이다.

이번 문서의 핵심은 아래 5가지다.

1. 현재 `State`가 이미 쓰고 있는 변수
2. 이미 가져오고 있지만 아직 `State`가 안 쓰는 변수
3. painter 안에 있지만 아직 `State` 파이프라인으로 안 들어온 정보
4. MetaTrader5에서 지금 바로 가져올 수 있는 정보
5. 추가하면 좋은 정보와 우선순위

즉 한 줄로 말하면:

`State를 막연히 더 만들자는 게 아니라, 지금 이미 있는 입력과 앞으로 넣을 입력을 분리해서 실제 구현 순서를 잡는 문서`

---

## 먼저 고정할 핵심 원칙

### Position / Response / State 역할

- `Position`
  - 어디에 있는가
  - 지도와 거리
- `Response`
  - 거기서 무슨 일이 일어났는가
  - 반응 사건
- `State`
  - 그 반응을 얼마나 믿을지
  - 얼마나 기다릴지
  - 얼마나 오래 들고 갈지

### State가 해야 하는 일

`State`는 아래 4가지를 말해야 한다.

1. `시장 모드`
   - range / trend / shock
2. `큰지도 편향`
   - 위/아래 어느 쪽이 더 유리한가
3. `반응 품질`
   - 지금 반응이 깨끗한가, 노이즈가 많은가
4. `실행 성격`
   - 기다릴지, 확인할지, 오래 들고 갈지

즉:

`State = 시장 성격 + 신뢰도 + 인내심`

---

## 현재 State가 실제로 쓰는 변수

파일 기준:

- [builder.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)
- [coefficients.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/coefficients.py)

### 현재 raw로 쓰는 변수

- `market_mode`
  - 시장 기본 모드
- `direction_policy`
  - `BOTH / BUY_ONLY / SELL_ONLY`
- `liquidity_state`
  - `GOOD / OK / BAD`
- `s_noise`
  - 노이즈 강도
- `s_conflict`
  - 충돌 강도
- `s_alignment`
  - 정렬 강도
- `s_disparity`
  - 이격도 강도
- `s_volatility`
  - 변동성 스트레스
- `s_topdown_bias`
  - 큰지도 signed bias
- `s_topdown_agreement`
  - 큰지도 agreement
- `s_compression`
  - 압축도
- `s_expansion`
  - 확장도
- `s_middle_neutrality`
  - 가운데 애매함

### 현재 최종 State 출력

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `noise_damp`
- `conflict_damp`
- `alignment_gain`
- `countertrend_penalty`
- `liquidity_penalty`
- `volatility_penalty`
- `topdown_bull_bias`
- `topdown_bear_bias`
- `big_map_alignment_gain`
- `wait_patience_gain`
- `confirm_aggression_gain`
- `hold_patience_gain`
- `fast_exit_risk_penalty`

### 현재 라벨

- `regime_state_label`
- `quality_state_label`
- `topdown_state_label`
- `patience_state_label`

결론:

`State`는 이미 기본 틀은 있다.
문제는 입력 재료가 아직 부족하고, execution layer 연결이 약하다는 점이다.

---

## 놀고 있는 변수들

여기서 말하는 `놀고 있는 변수`는
이미 수집되거나 계산되는데 `State`가 아직 안 쓰는 값들이다.

## A. 이미 context metadata에 들어오는데 State가 안 쓰는 변수

파일 기준:

- [context_classifier.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)

### 1. momentum / quality 계열

- `current_rsi`
  - 현재 RSI
- `current_adx`
  - 현재 ADX
- `current_plus_di`
  - +DI
- `current_minus_di`
  - -DI
- `current_disparity`
  - 현재 이격도 raw

현재 상태:

- 일부는 간접 축약값으로만 사용된다
  - 예: `s_disparity`
- 하지만 raw indicator 수준으로는 아직 State가 직접 안 먹는다

State에서 쓰면 좋은 이유:

- trend quality
- impulse quality
- exhaustion risk
- weak reclaim vs real continuation 구분

### 2. candle size / volatility 계열

- `recent_range_mean`
  - 최근 봉 평균 길이
- `recent_body_mean`
  - 최근 몸통 평균 길이
- `current_volatility_ratio`
  - 최근 변동성 비율

현재 상태:

- `current_volatility_ratio`는 일부 축약돼 쓰이지만
- `recent_range_mean`, `recent_body_mean`는 거의 놀고 있다

State에서 쓰면 좋은 이유:

- 장이 실제로 살아 있는지
- 봉이 너무 작아 의미 없는 장인지
- impulsive한지 dead한지

### 3. signal timing 계열

- `signal_timeframe`
  - 현재 signal 기준 TF

현재 상태:

- forecast 쪽 메타로 일부 쓰일 수 있지만
- State는 아직 거의 의미 있게 쓰지 않는다

State에서 쓰면 좋은 이유:

- M15 기준 판단인지, 다른 기준인지
- wait/confirm temperament를 조절하는 힌트

### 4. pattern window raw

- `pattern_recent_highs`
- `pattern_recent_lows`
- `pattern_recent_closes`

현재 상태:

- Response pattern 계산 쪽 힌트는 되지만
- State는 직접 안 쓴다

주의:

이건 우선순위가 낮다.
이 값들은 주로 `Response` owner에 더 가깝다.

### 5. S/R 메타

- `sr_active_support_tf`
- `sr_active_resistance_tf`
- `sr_level_rank`
- `sr_touch_count`

현재 상태:

- S/R subsystem에서는 의미가 있지만
- State는 아직 안 쓴다

State에서 쓰면 좋은 이유:

- 지지/저항 중요도
- 반복 터치된 레벨 신뢰도
- 레인지 성격 / break 성격 구분

---

## B. painter 안에 있는데 아직 State 파이프라인에 안 들어온 정보

파일 기준:

- [chart_painter.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_painter.py)
- [session_manager.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/session_manager.py)

### 1. session 관련 정보

현재 실제 계산 가능:

- `ASIA / EUROPE / USA session high`
- `ASIA / EUROPE / USA session low`
- `session box height`
- `position_in_session_box`
- `session expansion target`

현재 상태:

- painter는 그림으로 그린다
- Position은 일부 box low/high로만 활용한다
- State는 아직 직접 안 쓴다

State에서 쓰면 좋은 이유:

- `RANGE_SWING` vs `BREAKOUT_EXPANSION` 구분
- 세션 박스 압축 / 돌파 / exhaustion 판단

### 2. MTF MA line 구조 정보

현재 painter가 그리는 것:

- `15M_MA20`
- `30M_MA20`
- `1H_MA20`
- `4H_MA20`
- `1D_MA20`

현재 상태:

- Position의 큰지도엔 들어감
- State는 `bias/agreement` 축약값만 일부 먹음
- MA spacing / slope / compression은 아직 거의 직접 안 씀

State에서 쓰면 좋은 이유:

- topdown bias
- trend maturity
- compression / expansion

### 3. MTF trendline 구조 정보

현재 painter가 그리는 것:

- `1M / 15M / 1H / 4H` support/resistance trendline

현재 상태:

- Position에는 거리 지도로 들어감
- Response에는 반응 subsystem이 있음
- State는 trendline confluence / conflict를 아직 직접 거의 안 씀

State에서 쓰면 좋은 이유:

- 추세선 합류 여부
- 추세선 충돌 여부
- 구조가 깨끗한지 난잡한지

---

## MetaTrader5에서 지금 바로 가져올 수 있는 변수

파일 기준:

- [mt5_broker_adapter.py](c:/Users/bhs33/Desktop/project/cfd/adapters/mt5_broker_adapter.py)
- [mt5_snapshot_service.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/mt5_snapshot_service.py)

### 1. symbol_info_tick

현재 바로 가능:

- `bid`
- `ask`
- `last`
- `time`

State에 쓰기 좋은 의미:

- 실시간 spread stress
- execution friction
- 현재 유동성 악화

추천 필드:

- `tick_spread_state`
- `execution_friction_state`

### 2. symbol_info

현재 바로 가능:

- `spread`
- `point`
- `digits`
- `trade_mode`
- `stops_level`
- `freeze_level`
- `volume_min`
- `volume_step`

State에 쓰기 좋은 의미:

- broker execution constraint
- symbol-specific friction

추천 필드:

- `broker_constraint_state`
- `spread_stress_state`

### 3. copy_rates_from_pos

현재 바로 가능:

- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`
- `real_volume`

State에 쓰기 좋은 의미:

- volume participation
- spread stress
- impulse quality
- dead market vs alive market

추천 필드:

- `volume_participation_state`
- `volume_anomaly_state`
- `spread_stress_state`
- `impulse_quality_state`

### 4. positions_get

현재 바로 가능:

- 현재 열린 포지션들

State 또는 execution state로 쓸 수 있는 의미:

- 최근 churn
- 같은 심볼 반복 진입
- self-induced instability

추천 필드:

- `churn_risk_state`
- `recent_whipsaw_state`

주의:

이건 pure market state라기보다
`execution/system temperament`
에 더 가깝다.

---

## 추가하면 좋은 것

여기부터는 지금 어댑터에는 없지만,
추가 가치가 큰 입력들이다.

### 1. tick history

추천 이유:

- 순간 변동성
- stop hunt
- liquidity sweep
- intrabar impulse quality

추천 필드:

- `micro_volatility_state`
- `stop_hunt_risk_state`
- `sweep_risk_state`

우선순위:

- 중상
- 하지만 지금 당장 1순위는 아님

### 2. order book

추천 이유:

- bid/ask imbalance
- 호가 공백
- execution stress

추천 필드:

- `orderbook_imbalance_state`
- `liquidity_void_state`

우선순위:

- 중
- 브로커/심볼 지원 여부가 변수

### 3. event risk

추천 이유:

- 뉴스 전후 장 성격이 완전히 달라짐
- wait/fast exit에 직접 영향

추천 필드:

- `event_risk_state`
- `pre_news_state`
- `post_news_shock_state`

우선순위:

- 높음
- 특히 금/지수에서 중요

### 4. session open 기준

추천 이유:

- 세션 박스뿐 아니라
  - day open
  - week open
  - session open
  기준선 자체가 장 성격을 많이 바꿈

추천 필드:

- `session_open_bias_state`
- `open_drive_state`

우선순위:

- 높음
- 구현 난이도도 낮은 편

---

## State vNext에 넣기 좋은 우선순위

여기서부터가 실제 실행 순서다.

## 1순위: 이미 있는데 안 쓰는 값부터 붙이기

이 단계가 가장 중요하다.

대상:

- `current_rsi`
- `current_adx`
- `current_plus_di`
- `current_minus_di`
- `recent_range_mean`
- `recent_body_mean`
- `sr_level_rank`
- `sr_touch_count`

이유:

- 데이터 추가 수집이 필요 없다
- 지금 구조 위에서 바로 State quality를 강화할 수 있다
- 위험이 가장 낮다

### 이 단계 목표

- `momentum_quality_state`
- `impulse_quality_state`
- `level_reliability_state`

를 먼저 만든다.

---

## 2순위: session 기반 state 붙이기

대상:

- `session high/low`
- `session box height`
- `position_in_session_box`
- `session expansion target`
- `session open`

이유:

- 이미 painter/session_manager에 재료가 있다
- range vs breakout 해석에 직접 도움 된다
- `State`가 실제로 장 성격을 말하게 만들어 준다

### 이 단계 목표

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`

---

## 3순위: topdown spacing / slope 강화

대상:

- `mtf_ma_big_map_v1`
- `mtf_trendline_map_v1`

이유:

- 지금은 bias/agreement만 일부 들어간다
- spacing/slope가 들어가면 큰지도 해석이 훨씬 좋아진다

### 이 단계 목표

- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`

---

## 4순위: spread / volume stress 강화

대상:

- `symbol_info_tick`
- `symbol_info`
- `copy_rates_from_pos`의 volume/spread

이유:

- execution temperament에 직접 영향
- `wait_patience_gain`, `fast_exit_risk_penalty`와 잘 맞는다

### 이 단계 목표

- `spread_stress_state`
- `volume_participation_state`
- `execution_friction_state`

---

## 5순위: event risk

대상:

- 뉴스 / 경제지표 / 장 시작 이벤트

이유:

- effect가 크다
- 다만 외부 입력이 필요할 가능성이 크다

### 이 단계 목표

- `event_risk_state`

---

## 6순위: tick history / order book

대상:

- tick stream
- 호가창

이유:

- 굉장히 좋지만 구현 난이도와 운영 복잡도가 올라간다

### 이 단계 목표

- `micro_volatility_state`
- `stop_hunt_risk_state`
- `orderbook_imbalance_state`

---

## State 로드맵

### Phase S0. Freeze

목표:

- `State`의 역할을 더 이상 흔들지 않는다.

고정 문장:

`State는 Position도 아니고 Response도 아니다. State는 시장 성격과 신뢰도, 인내심을 말한다.`

### Phase S1. Existing input harvest

목표:

- 이미 있는데 안 쓰는 값부터 State로 끌어온다.

대상:

- `current_rsi`
- `current_adx`
- `current_plus_di`
- `current_minus_di`
- `recent_range_mean`
- `recent_body_mean`
- `sr_level_rank`
- `sr_touch_count`

완료 기준:

- State raw에 새 필드가 생기고
- quality 라벨이 더 풍부해진다.

### Phase S2. Session state

목표:

- session 기반 장 성격을 State가 직접 말하게 한다.

대상:

- session range
- session box height
- session expansion target
- position in session box

완료 기준:

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
생성

### Phase S3. Topdown slope / spacing

목표:

- 큰지도를 더 정교하게 해석한다.

대상:

- MTF MA spacing
- MTF MA slope
- MTF trendline confluence/conflict

완료 기준:

- `topdown_spacing_state`
- `topdown_slope_state`
- `topdown_confluence_state`
생성

### Phase S4. Spread / volume stress

목표:

- execution temperament를 강화한다.

대상:

- tick spread
- rate spread
- tick volume
- real volume

완료 기준:

- `spread_stress_state`
- `volume_participation_state`
- `execution_friction_state`
생성

### Phase S5. State -> execution layer 연결

목표:

- 새 State가 실제 행동을 바꾸게 한다.

연결 대상:

- `ObserveConfirm`
- `WaitEngine`
- `ExitProfileRouter`
- `ExitManagePositions`

완료 기준:

- `WAIT 과보수`
- `조기청산`
증상이 줄어든다.

### Phase S6. optional advanced inputs

목표:

- tick history / event risk / order book 확장

완료 기준:

- 고급 State가 필요한 구간에서만 추가 입력을 켠다.

---

## 최종 조언

지금 State를 키울 때 가장 좋은 순서는 이거다.

1. 새 데이터 붙이기 전에
   - 이미 있는데 안 쓰는 값부터 먹인다.
2. 그다음
   - session
   - topdown spacing/slope
   - spread/volume stress
   순으로 확장한다.
3. tick history / order book은
   - 나중에 붙여도 늦지 않다.

한 줄 결론:

`State vNext의 핵심은 "새로운 복잡성"보다 "이미 있는 입력을 제대로 owner화하는 것"이고, 우선순위는 momentum-quality -> session -> topdown spacing/slope -> spread/volume stress -> event risk -> tick/orderbook 순서가 가장 안전하다.`
