# State 입력 인벤토리 및 설계 초안

## 목적

이 문서는 `State`를 제대로 정의하기 위해,

1. 원래 구상했던 `State`의 역할이 무엇인지
2. 현재 코드와 painter 안에서 이미 확보된 정보가 무엇인지
3. MetaTrader5에서 지금 바로 가져올 수 있는 정보가 무엇인지
4. 앞으로 추가하면 좋은 정보가 무엇인지

를 한 번에 정리하는 기준 문서다.

핵심 목표는 단순하다.

`State`를 막연한 보조지표 묶음이 아니라,
`Position`과 `Response` 사이에서
`신뢰 / 인내심 / 큰지도 / execution temperament`
를 조절하는 명확한 owner 레이어로 세우는 것이다.

---

## 가장 먼저 고정할 원칙

### State는 무엇을 해야 하나

`State`는 아래를 말해야 한다.

- 지금 장이 `range`인가 `trend`인가 `shock`인가
- 지금 반응을 얼마나 믿어도 되는가
- 지금은 빨리 confirm 해야 하는가, 더 기다려야 하는가
- 지금은 오래 들고 갈 가치가 있는가, 빨리 털어야 하는가
- 큰지도는 위/아래 어느 쪽으로 더 기울어 있는가

즉 한 줄로:

`State = 지금 이 반응을 얼마나 믿고, 얼마나 기다리고, 얼마나 오래 들고 갈지를 조절하는 시장 해석 레이어`

### State가 하면 안 되는 것

- `Position`처럼 위치를 직접 owner로 잡기
- `Response`처럼 사건을 직접 owner로 잡기
- `BUY/SELL` identity를 직접 만들기

즉:

- `Position = 어디 있나`
- `Response = 무슨 일이 일어났나`
- `State = 그걸 얼마나 믿고, 얼마나 참을까`

이 경계는 계속 유지하는 게 좋다.

---

## 원래 구상한 State 큰 구조

현재까지의 대화 기준으로 보면,
`State`는 아래 4층으로 정리하는 게 가장 자연스럽다.

### 1. Regime State

시장 모드 자체를 말하는 층.

예:

- `RANGE_SWING`
  - 레인지 왕복 장
- `RANGE_COMPRESSION`
  - 압축 레인지
- `TREND_PULLBACK`
  - 추세 속 눌림목
- `BREAKOUT_EXPANSION`
  - 돌파 확장 장
- `CHOP_NOISE`
  - 노이즈 장
- `SHOCK`
  - 충격 장

### 2. Quality State

지금 장이 얼마나 깨끗하고 믿을 만한지 말하는 층.

예:

- `HIGH_QUALITY`
- `MEDIUM_QUALITY`
- `LOW_QUALITY`

여기서 주로 보는 것:

- noise
- conflict
- liquidity
- volatility stress

### 3. Topdown Bias State

큰지도가 위/아래 어느 쪽으로 더 기울어 있는지 말하는 층.

예:

- `BULL_ALIGNED`
- `BEAR_ALIGNED`
- `MIXED_TOPDOWN`
- `NEUTRAL_TOPDOWN`

여기서 주로 보는 것:

- 상위 MA 정렬
- 상위 추세선 거리 지도
- 큰지도 alignment

### 4. Patience / Execution State

지금 얼마나 기다릴지, 얼마나 오래 들고 갈지, 얼마나 성급히 끊어야 할지를 말하는 층.

예:

- `WAIT_FAVOR`
- `CONFIRM_FAVOR`
- `HOLD_FAVOR`
- `FAST_EXIT_FAVOR`

즉 이 층은:

- ObserveConfirm
- WaitEngine
- ExitProfileRouter
- ExitManagePositions

로 이어져야 한다.

---

## 중요한 구분: painter를 직접 읽을 것인가?

결론부터 말하면:

`State`는 가능하면 painter가 그린 결과물을 직접 읽는 레이어가 되면 안 된다.

더 정확한 구조는 이렇다.

- painter는 `시각화 / 디버그 / 비교용`
- 실제 `State`는 painter가 그릴 때 쓴 원본 데이터를 읽어야 한다

즉:

- `draw.csv`를 State의 직접 입력으로 삼기보다
- painter가 그리기 위해 계산한
  - session range
  - MTF trendline
  - MTF MA
  - BB
  - box
  를 만드는 원본 데이터와 계산 규칙을 직접 사용하는 게 좋다.

다만 painter가 이미 그리고 있는 항목들은
`State에 넣을 후보 목록`
으로는 아주 유용하다.

---

## 현재 painter 안에 이미 있는 정보

파일 기준:

- [chart_painter.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_painter.py)
- [session_manager.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/session_manager.py)

### 1. Session Box

painter가 이미 그리는 것:

- `ASIA`
- `EUROPE`
- `USA`
세션 박스

실제 가지고 있는 값:

- `session_high`
  - 세션 고가
- `session_low`
  - 세션 저가
- `session_t1`
  - 세션 시작 시간
- `session_t2`
  - 세션 종료 시간
- `session_box_height`
  - 세션 박스 높이
- `position_in_session_box`
  - 현재가가 박스 안의 어디인지
- `session_expansion_target`
  - 세션 돌파 시 1x 확장 타겟

State에서 쓸 수 있는 의미:

- `session_regime_state`
  - 현재 세션이 압축/확장 중인지
- `session_expansion_bias`
  - 세션 박스 돌파 에너지
- `session_exhaustion_risk`
  - 이미 세션 박스를 많이 확장했는지

### 2. H1 Bollinger Lines

painter가 이미 그리는 것:

- `1H_BB20_UP`
- `1H_BB20_MID`
- `1H_BB20_DN`

State에서 바로 읽으면 좋은 것:

- `bb20_width`
  - 밴드 폭
- `bb20_width_ratio`
  - 최근 변동 대비 밴드 폭
- `bb20_width_state`
  - `COMPRESSED / NORMAL / EXPANDED`

State에서 쓸 수 있는 의미:

- `compression`
- `expansion`
- `breakout readiness`
- `exhaustion risk`

### 3. H1 Trendline

painter가 이미 그리는 것:

- `1H_RES_TREND`
- `1H_SUP_TREND`

State에서 간접적으로 쓸 수 있는 것:

- 상단/하단 추세선 간 간격
- 현재가가 추세선 중간에서 얼마나 멀리 벗어났는지
- 추세선 기울기 강도

이건 Position/Response owner가 더 강하지만,
State에서 아래 보정용으로 쓸 수 있다.

- `trend_cleanliness`
  - 추세선 구조가 깨끗한지
- `trend_pressure_state`
  - 수렴인지 발산인지

### 4. MTF Trendline

painter가 이미 그리는 것:

- `1M_RES_TREND`, `1M_SUP_TREND`
- `15M_RES_TREND`, `15M_SUP_TREND`
- `1H_RES_TREND`, `1H_SUP_TREND`
- `4H_RES_TREND`, `4H_SUP_TREND`

State에서 의미 있게 쓸 수 있는 것:

- 상위 추세선 정렬도
- 서로 다른 시간대 추세선의 일치/충돌
- 좁아지는 구조인지, 벌어지는 구조인지

추천 State 필드:

- `mtf_trend_agreement`
  - 여러 시간대 추세선 정합도
- `trend_confluence_state`
  - 추세선 합류 상태
- `trend_conflict_state`
  - 추세선 충돌 상태

### 5. MTF MA20

painter가 이미 그리는 것:

- `15M_MA20`
- `30M_MA20`
- `1H_MA20`
- `4H_MA20`
- `1D_MA20`

State에서 바로 쓸 수 있는 것:

- 상위 MA 정렬
- 상위 MA 간격
- 상위 MA 수렴/확장

추천 State 필드:

- `topdown_ma_stack_state`
  - `BULL_STACK / BEAR_STACK / MIXED_STACK`
- `topdown_ma_agreement`
  - 큰지도 정합도
- `topdown_compression`
  - 큰지도 MA 압축도

---

## 현재 코드에서 이미 State가 먹을 수 있는 정보

파일 기준:

- [context_classifier.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- [trend_manager.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/trend_manager.py)
- [state/builder.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)

### A. 현재 OHLC 기반으로 이미 들어오는 값

#### 현재 15M current / previous / pre_previous candle

- `current_open`
- `current_high`
- `current_low`
- `current_close`
- `previous_open`
- `previous_high`
- `previous_low`
- `previous_close`
- `pre_previous_open`
- `pre_previous_high`
- `pre_previous_low`
- `pre_previous_close`

State에서의 의미:

- 최근 3봉 관성
- 체력 감소/증가
- momentum fade 여부

#### 현재 indicator 값

`trend_manager.add_indicators()`에서 이미 계산되는 것:

- `ma_20`
- `ma_40`
- `ma_60`
- `ma_120`
- `ma_240`
- `ma_480`
- `bb_20_up`
- `bb_20_mid`
- `bb_20_dn`
- `bb_4_up`
- `bb_4_dn`
- `bb_4_3_up`
- `bb_4_3_mid`
- `bb_4_3_dn`
- `disparity`
  - 20MA 기준 이격도
- `rsi`
- `adx`
- `plus_di`
- `minus_di`

State에서 이미/또는 곧바로 쓸 수 있는 의미:

- `s_disparity`
  - 현재는 이미 State raw로 들어감
- `s_alignment`
  - MA 정렬 기반으로 현재 들어감
- `trend_strength_state`
  - ADX, DI 차이로 강화 가능
- `momentum_exhaustion_state`
  - RSI + disparity 조합으로 강화 가능

#### 현재 volatility / spread / quality 메타데이터

context에 이미 들어가는 것:

- `current_volatility_ratio`
- `current_spread_ratio`
- `recent_range_mean`
- `recent_body_mean`
- `wait_score`
- `wait_conflict`
- `wait_noise`
- `liquidity_state`
- `market_mode`
- `direction_policy`

State에서 현재 실제로 쓰는 것:

- `market_mode`
  - `RANGE / TREND / SHOCK`
- `direction_policy`
  - `BOTH / BUY_ONLY / SELL_ONLY`
- `liquidity_state`
  - `GOOD / OK / BAD`
- `s_noise`
  - `wait_noise` 기반
- `s_conflict`
  - `wait_conflict` 기반
- `s_volatility`
  - `current_volatility_ratio` 기반

### B. Position에서 State raw로 이미 넘어오는 값

현재 State raw에 이미 들어오는 것:

- `s_topdown_bias`
  - `mtf_context_weight_profile_v1.bias`
- `s_topdown_agreement`
  - `mtf_context_weight_profile_v1.agreement_score`
- `s_compression`
  - `position_scale.compression_score`
- `s_expansion`
  - `position_scale.expansion_score`
- `s_middle_neutrality`
  - `position_energy.middle_neutrality`

즉 지금 State는 이미:

- 큰지도 정렬
- 압축/확장
- 가운데 애매함

을 받을 수 있게는 되어 있다.

---

## MT5에서 지금 바로 가져올 수 있는 정보

파일 기준:

- [mt5_broker_adapter.py](c:/Users/bhs33/Desktop/project/cfd/adapters/mt5_broker_adapter.py)
- [mt5_snapshot_service.py](c:/Users/bhs33/Desktop/project/cfd/backend/services/mt5_snapshot_service.py)

현재 어댑터가 직접 노출하는 것:

- `symbol_info_tick(symbol)`
- `symbol_info(symbol)`
- `copy_rates_from_pos(symbol, timeframe, start_pos, count)`
- `positions_get(...)`

### 1. tick 정보

`symbol_info_tick()`에서 일반적으로 활용 가능한 값:

- `bid`
- `ask`
- `last`
- `time`

State에서 쓸 수 있는 의미:

- 실시간 spread 상태
- 현재 유동성 악화 여부
- 체결 불리함 증가 여부

추천 State 필드:

- `tick_spread_state`
- `execution_friction_state`

### 2. symbol_info 정보

`symbol_info()`에서 일반적으로 활용 가능한 값:

- `spread`
- `digits`
- `point`
- `trade_mode`
- `volume_min`
- `volume_step`
- `stops_level`
- `freeze_level`

State에서 쓸 수 있는 의미:

- 실행 제약
- 체결 불편함
- 비정상 상태

추천 State 필드:

- `broker_execution_constraint_state`
- `spread_stress_state`

### 3. OHLCV rates 정보

`copy_rates_from_pos()`가 주는 캔들에는 보통 아래가 같이 온다.

- `open`
- `high`
- `low`
- `close`
- `tick_volume`
- `spread`
- `real_volume`

여기서 State에 특히 좋은 것:

- `tick_volume`
  - 지금 봉 거래 참여 강도
- `spread`
  - 봉 단위 spread 스트레스
- `real_volume`
  - 가능할 경우 실거래량

추천 State 필드:

- `volume_participation_state`
- `volume_anomaly_state`
- `spread_stress_state`
- `impulse_quality_state`

### 4. positions 정보

`positions_get()`는 본래 포지션 관리용이지만,
State에도 간접적으로 활용 가능하다.

예:

- 동일 심볼에서 최근 churn이 심한지
- 최근 reversal 청산이 반복되는지

추천 State/Execution 필드:

- `churn_risk_state`
- `recent_whipsaw_state`

주의:

이건 pure market state보다는 execution temperament에 더 가깝다.

---

## 지금은 직접 안 쓰지만, 현재 데이터만으로 계산 가능한 정보

이 부분이 실전적으로 중요하다.

새 데이터를 안 붙여도,
이미 있는 OHLC + indicator + MTF map만으로 만들 수 있는 State가 많다.

### 1. MA spacing state

의미:

- 상위 MA 사이 간격이 좁은가 넓은가
- 압축 구조인가 발산 구조인가

후보:

- `mtf_ma_spacing_score`
- `mtf_ma_compression_state`
- `mtf_ma_expansion_state`

### 2. Trend slope state

의미:

- M15/H1/H4 MA20 기울기
- M15/H1/H4 trendline 기울기

후보:

- `ma_slope_state`
- `trendline_slope_state`
- `topdown_slope_agreement`

### 3. Session regime state

세션 박스 기반으로 만들 수 있는 것:

- 현재 세션이 압축인지
- 이미 세션 박스를 과도하게 돌파했는지
- 세션 high/low에서 얼마만큼 멀어졌는지

후보:

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`

### 4. Momentum quality state

현재 indicator만으로 가능한 것:

- `RSI + ADX + DI gap + disparity`

후보:

- `momentum_quality_state`
- `impulse_quality_state`
- `exhaustion_risk_state`

### 5. Range cleanliness state

현재 Position / Response와 결합해 만들 수 있는 것:

- edge turn은 자주 나오는데 break는 약한가
- middle neutrality가 높은가
- conflict가 높은가

후보:

- `range_cleanliness_state`
- `swing_friendliness_state`

---

## 추가하면 좋은 MT5/브로커 입력

이건 지금 어댑터에는 없지만,
추가하면 State 질이 확 좋아질 수 있는 것들이다.

### 1. tick history

추천 API:

- `copy_ticks_from`
- `copy_ticks_range`

이게 있으면 좋은 이유:

- 실시간 미세 변동성
- stop hunt / sweep 흔적
- 체결 왜곡
- intrabar impulse quality

추천 State 필드:

- `micro_volatility_state`
- `sweep_risk_state`
- `stop_hunt_risk_state`

### 2. market depth / book

추천 API:

- `market_book_add`
- `market_book_get`

좋은 이유:

- 호가가 비는 구간
- bid/ask imbalance
- 체결 불리함

추천 State 필드:

- `orderbook_imbalance_state`
- `liquidity_void_state`

주의:

브로커/심볼에 따라 안 되는 경우가 있으니 optional로 봐야 한다.

### 3. calendar / event risk

MT5 자체보다는 외부 경제 캘린더가 더 자연스럽지만,
State에는 매우 중요하다.

추천 State 필드:

- `event_risk_state`
- `pre_news_state`
- `post_news_shock_state`

### 4. session open reference

현재도 세션 박스는 있지만,
더 직접적으로:

- day open
- week open
- session open

을 넣으면 좋다.

추천 State 필드:

- `open_drive_state`
- `session_open_bias_state`

---

## State에 특히 잘 맞는 추가 정보 추천

지금 기준으로 우선순위를 주면 이 순서가 좋다.

### 1순위. session 기반 state

이유:

- 이미 painter와 session_manager에 재료가 있다
- 추가 비용이 작다
- range / breakout / exhaustion 해석에 바로 도움 된다

추천:

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`

### 2순위. topdown slope / spacing

이유:

- 이미 MTF map이 있다
- 큰지도를 더 믿을지 덜 믿을지 정하는 데 중요하다

추천:

- `mtf_ma_spacing_score`
- `mtf_ma_compression_state`
- `topdown_slope_agreement`

### 3순위. momentum quality

이유:

- 이미 RSI/ADX/DI/disparity가 있다
- trend continuation vs weak reclaim 구분에 도움 된다

추천:

- `momentum_quality_state`
- `impulse_quality_state`
- `exhaustion_risk_state`

### 4순위. volume / spread stress

이유:

- MT5 rates/tick에서 바로 얻을 수 있다
- wait/exit temperament에 영향이 크다

추천:

- `volume_anomaly_state`
- `spread_stress_state`
- `execution_friction_state`

---

## State vNext 입력 체계 제안

### A. 지금 바로 넣을 수 있는 입력

- `market_mode`
- `direction_policy`
- `liquidity_state`
- `s_noise`
- `s_conflict`
- `s_alignment`
- `s_disparity`
- `s_volatility`
- `s_topdown_bias`
- `s_topdown_agreement`
- `s_compression`
- `s_expansion`
- `s_middle_neutrality`
- `current_rsi`
- `current_adx`
- `current_plus_di`
- `current_minus_di`
- `current_disparity`
- `current_volatility_ratio`
- `current_spread_ratio`
- `recent_range_mean`
- `recent_body_mean`

### B. 같은 데이터로 바로 추가 계산 가능한 입력

- `session_regime_state`
- `session_expansion_state`
- `session_exhaustion_state`
- `mtf_ma_spacing_score`
- `mtf_ma_compression_state`
- `mtf_ma_expansion_state`
- `topdown_slope_agreement`
- `momentum_quality_state`
- `impulse_quality_state`
- `exhaustion_risk_state`
- `range_cleanliness_state`

### C. 어댑터 확장 후 넣으면 좋은 입력

- `tick_spread_state`
- `volume_participation_state`
- `volume_anomaly_state`
- `micro_volatility_state`
- `orderbook_imbalance_state`
- `liquidity_void_state`
- `event_risk_state`

---

## 최종 정리

지금 `State`를 제대로 세우려면 가장 중요한 건 이거다.

1. `Position`과 `Response`가 말하지 않는 것만 State가 말한다.
2. painter는 참고용이고, State는 painter가 그리기 위해 쓰는 원본 데이터를 읽는다.
3. 지금도 이미 State에 넣을 수 있는 재료가 꽤 많다.
4. 특히
   - `session`
   - `topdown spacing/slope`
   - `momentum quality`
   - `spread/volume stress`
   이 네 묶음이 next-state를 크게 강화할 후보들이다.

한 줄 결론:

`State는 지금부터 "보조지표 묶음"이 아니라, session + big map + quality + patience를 함께 해석하는 시장 성격 레이어로 확장하는 게 맞다.`
