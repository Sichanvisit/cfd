# Teacher-Label Micro-Structure Top10 Step 4 체크리스트

- [x] Step 4 hot payload scope를 semantic/source 최소 surface로 고정
- [x] `ENTRY_DECISION_FULL_COLUMNS` / `ENTRY_DECISION_LOG_COLUMNS`에 flat column 추가
- [x] `build_entry_decision_hot_payload`에서 `state_vector_v2.metadata` 기반 micro surface 추출
- [x] semantic/source 값이 없을 때 빈 문자열 / `None` fallback 규칙 고정
- [x] recorder 회귀 테스트 추가
- [x] `pytest -q tests/unit/test_entry_engines.py` 통과 확인

## Step 4 대상 flat column

- semantic:
  - `micro_breakout_readiness_state`
  - `micro_reversal_risk_state`
  - `micro_participation_state`
  - `micro_gap_context_state`
- source:
  - `micro_body_size_pct_20`
  - `micro_doji_ratio_20`
  - `micro_same_color_run_current`
  - `micro_same_color_run_max_20`
  - `micro_range_compression_ratio_20`
  - `micro_volume_burst_ratio_20`
  - `micro_volume_burst_decay_20`
  - `micro_gap_fill_progress`
