# Teacher-Label Micro-Structure Top10 Step 2 state_raw_snapshot 구현 체크리스트

## 목표

이 문서는 `Step 2. state_raw_snapshot 편입` 구현 체크리스트다.

## Checklist

### A. owner 확정

- [ ] [models.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/core/models.py)에 canonical field를 추가한다
- [ ] [builder.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/state/builder.py)에서 `micro_structure_v1`를 읽는다
- [ ] [test_state_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_state_contract.py)에 회귀를 추가한다

### B. raw canonical field 승격

- [ ] `s_body_size_pct_20`
- [ ] `s_upper_wick_ratio_20`
- [ ] `s_lower_wick_ratio_20`
- [ ] `s_doji_ratio_20`
- [ ] `s_same_color_run_current`
- [ ] `s_same_color_run_max_20`
- [ ] `s_bull_ratio_20`
- [ ] `s_bear_ratio_20`
- [ ] `s_range_compression_ratio_20`
- [ ] `s_volume_burst_ratio_20`
- [ ] `s_volume_burst_decay_20`
- [ ] `s_swing_high_retest_count_20`
- [ ] `s_swing_low_retest_count_20`
- [ ] `s_gap_fill_progress`

### C. fallback 규칙

- [ ] `micro_structure_v1`가 없을 때 안전하게 동작한다
- [ ] `direction_run_stats` nested fallback을 둔다
- [ ] `recent_body_mean` fallback을 둔다
- [ ] `compression_score` fallback을 둔다
- [ ] `gap_fill_progress`는 `None` 허용 규칙을 유지한다

### D. metadata surface

- [ ] `micro_structure_version`
- [ ] `micro_structure_data_state`
- [ ] `micro_structure_anchor_state`
- [ ] `micro_structure_window_size`
- [ ] `micro_structure_volume_source`
- [ ] flat `micro_*` surface를 추가한다
- [ ] raw `micro_structure_v1` dict도 같이 보존한다

### E. 테스트

- [ ] micro_structure가 있을 때 승격되는지 테스트한다
- [ ] micro_structure가 없을 때 기본값이 유지되는지 테스트한다
- [ ] 기존 raw contract 테스트가 깨지지 않는지 확인한다

## 완료 기준

- [ ] Step 2 상세 기준서와 구현이 일치한다
- [ ] `pytest -q tests/unit/test_state_contract.py`가 통과한다
