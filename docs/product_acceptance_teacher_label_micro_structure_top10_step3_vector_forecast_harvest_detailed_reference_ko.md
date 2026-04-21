# Teacher-Label Micro-Structure Top10 Step 3 vector/forecast harvest 상세 기준서

## 목적

이 문서는 `Step 3. state_vector / forecast harvest 연결`의 상세 기준서다.

Step 3의 목적은 Step 2에서 raw snapshot으로 승격된 micro-structure canonical field를
그대로 복사하는 것이 아니라,

- `state_vector_v2`의 semantic state와 coefficient bias
- `forecast_features_v1`의 harvest surface

로 한 단계 더 끌어올리는 것이다.

## Step 3 owner

- [coefficients.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/coefficients.py)
- [forecast_features.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_features.py)
- [forecast_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/forecast_engine.py)
- [test_state_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_state_contract.py)
- [test_forecast_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_forecast_contract.py)

## Step 3 핵심 원칙

1. raw 값을 전부 직접 coefficient에 꽂지 않는다
2. 먼저 중간 semantic state를 만든다
3. coefficient 보정은 작고 해석 가능한 폭으로만 넣는다
4. forecast harvest에는 semantic state와 source micro value를 같이 남긴다

## 1차 semantic state

Step 3 1차에서 만드는 중간 state는 아래 4개다.

- `micro_breakout_readiness_state`
- `micro_reversal_risk_state`
- `micro_participation_state`
- `micro_gap_context_state`

## 1차 source micro harvest

forecast secondary harvest에는 아래 raw micro source를 남긴다.

- `source_micro_body_size_pct_20`
- `source_micro_upper_wick_ratio_20`
- `source_micro_lower_wick_ratio_20`
- `source_micro_doji_ratio_20`
- `source_micro_same_color_run_current`
- `source_micro_same_color_run_max_20`
- `source_micro_bull_ratio_20`
- `source_micro_bear_ratio_20`
- `source_micro_range_compression_ratio_20`
- `source_micro_volume_burst_ratio_20`
- `source_micro_volume_burst_decay_20`
- `source_micro_swing_high_retest_count_20`
- `source_micro_swing_low_retest_count_20`
- `source_micro_gap_fill_progress`

## coefficient 보정 범위

Step 3 1차에서 micro-structure 보정을 허용하는 coefficient는 아래다.

- `range_reversal_gain`
- `trend_pullback_gain`
- `breakout_continuation_gain`
- `wait_patience_gain`
- `confirm_aggression_gain`
- `hold_patience_gain`
- `fast_exit_risk_penalty`

## 해석 방향

### breakout 쪽

- compression이 높고
- volume burst가 살아 있고
- run이 이어지고
- doji/decay가 낮으면

`breakout_readiness`를 올린다.

### reversal 쪽

- wick가 크고
- retest가 많고
- doji/decay가 높으면

`reversal_risk`를 올린다.

### participation 쪽

- burst는 높은데 decay가 낮으면 `BURST_CONFIRMED`
- burst도 높고 decay도 높으면 `BURST_FADING`
- burst가 거의 없으면 `QUIET_PARTICIPATION`

### gap 쪽

- gap progress가 없으면 `GAP_CONTEXT_MISSING`
- 0.33 미만이면 `EARLY_GAP_FILL`
- 0.85 미만이면 `ACTIVE_GAP_FILL`
- 그 이상이면 `LATE_GAP_FILL`

## Step 3 완료 기준

아래를 만족하면 Step 3 1차 완료로 본다.

1. `StateVectorV2.metadata`에 micro semantic state가 생긴다
2. coefficient reasons에 micro adjustment 근거가 추가된다
3. `ForecastFeaturesV1.metadata["semantic_forecast_inputs_v2"]`에서 micro state/source harvest가 보인다
4. state/forecast 회귀 테스트가 통과한다
