# Teacher-Label Micro-Structure Top10 Step 3 vector/forecast harvest 구현 체크리스트

## 목표

이 문서는 `Step 3. state_vector / forecast harvest 연결` 구현 체크리스트다.

## Checklist

### A. state_vector semantic state

- [ ] `micro_breakout_readiness_state`
- [ ] `micro_reversal_risk_state`
- [ ] `micro_participation_state`
- [ ] `micro_gap_context_state`

### B. coefficient 보정

- [ ] `range_reversal_gain` 보정
- [ ] `trend_pullback_gain` 보정
- [ ] `breakout_continuation_gain` 보정
- [ ] `wait_patience_gain` 보정
- [ ] `confirm_aggression_gain` 보정
- [ ] `hold_patience_gain` 보정
- [ ] `fast_exit_risk_penalty` 보정

### C. metadata source harvest

- [ ] `source_micro_body_size_pct_20`
- [ ] `source_micro_upper_wick_ratio_20`
- [ ] `source_micro_lower_wick_ratio_20`
- [ ] `source_micro_doji_ratio_20`
- [ ] `source_micro_same_color_run_current`
- [ ] `source_micro_same_color_run_max_20`
- [ ] `source_micro_bull_ratio_20`
- [ ] `source_micro_bear_ratio_20`
- [ ] `source_micro_range_compression_ratio_20`
- [ ] `source_micro_volume_burst_ratio_20`
- [ ] `source_micro_volume_burst_decay_20`
- [ ] `source_micro_swing_high_retest_count_20`
- [ ] `source_micro_swing_low_retest_count_20`
- [ ] `source_micro_gap_fill_progress`

### D. forecast harvest

- [ ] `state_harvest`에 micro semantic state를 추가한다
- [ ] `secondary_harvest`에 source micro value를 추가한다
- [ ] `FORECAST_HARVEST_TARGETS_V1`에 새 키를 반영한다

### E. 테스트

- [ ] micro structure가 vector gain에 반영되는지 테스트한다
- [ ] explanatory metadata contract가 유지되는지 테스트한다
- [ ] forecast semantic harvest에 micro state/source가 보이는지 테스트한다

## 완료 기준

- [ ] `pytest -q tests/unit/test_state_contract.py` 통과
- [ ] `pytest -q tests/unit/test_forecast_contract.py` 통과
