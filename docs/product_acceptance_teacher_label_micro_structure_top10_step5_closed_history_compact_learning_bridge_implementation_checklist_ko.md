# Teacher-Label Micro-Structure Top10 Step 5 체크리스트

- [x] Step 5 범위를 closed-history compact bridge로 고정
- [x] `TRADE_COLUMNS` / `TEXT_TRADE_COLUMNS`에 micro compact field 추가
- [x] `normalize_trade_df`에서 micro semantic/source 정규화 추가
- [x] `TradeLogger.log_entry`가 micro snapshot을 OPEN row로 싣게 확장
- [x] `upsert_open_snapshots`가 micro snapshot을 보존/갱신하게 확장
- [x] closed row copy 경로에서 micro 값이 유지되는지 테스트 추가
- [x] `pytest -q tests/unit/test_trade_logger_open_snapshots.py` 통과
- [x] `pytest -q tests/unit/test_trade_logger_close_ops_micro_structure.py` 통과
- [x] `pytest -q tests/unit/test_trade_logger_lifecycle.py` 통과
- [x] `pytest -q tests/unit/test_loss_quality_wait_behavior.py` 통과

## Step 5 micro compact field

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

## 회귀 결과

- `pytest -q tests/unit/test_trade_logger_open_snapshots.py` -> `4 passed`
- `pytest -q tests/unit/test_trade_logger_close_ops_micro_structure.py` -> `1 passed`
- `pytest -q tests/unit/test_trade_logger_lifecycle.py` -> `3 passed`
- `pytest -q tests/unit/test_loss_quality_wait_behavior.py` -> `5 passed`

## 구현 중 잡은 보정

- open snapshot refresh에서 semantic micro 값은 유지되는데 numeric micro 값은 빈 문자열 refresh 때 `0`으로 덮이는 버그가 있었음
- [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)에 `_pick_numeric` 규칙을 추가해서 `blank -> keep current`로 보정함
