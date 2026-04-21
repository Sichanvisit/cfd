# Teacher-Label Micro-Structure Top10 Step 6 체크리스트

- [x] Step 6 범위를 cross-stage regression bundle로 고정
- [x] breakout/continuation smoke 케이스 추가
- [x] reversal/wick smoke 케이스 추가
- [x] missing gap anchor safety 케이스 추가
- [x] Step 1 helper -> Step 4 hot payload까지 연결 검증
- [x] Step 5 closed compact 회귀와 함께 묶음 실행
- [x] `pytest -q tests/unit/test_micro_structure_pipeline_regression.py` 통과
- [x] 기존 핵심 회귀 재실행 결과 기록

## 이번 단계 대표 회귀 묶음

- `tests/unit/test_micro_structure_pipeline_regression.py`
- `tests/unit/test_trading_application_micro_structure.py`
- `tests/unit/test_state_contract.py`
- `tests/unit/test_forecast_contract.py`
- `tests/unit/test_entry_engines.py`
- `tests/unit/test_trade_logger_open_snapshots.py`
- `tests/unit/test_trade_logger_close_ops_micro_structure.py`

## 회귀 결과

- `pytest -q tests/unit/test_micro_structure_pipeline_regression.py` -> `3 passed`
- `pytest -q tests/unit/test_trading_application_micro_structure.py` -> `3 passed`
- `pytest -q tests/unit/test_state_contract.py` -> `24 passed`
- `pytest -q tests/unit/test_forecast_contract.py` -> `44 passed`
- `pytest -q tests/unit/test_entry_engines.py` -> `15 passed`
- `pytest -q tests/unit/test_trade_logger_open_snapshots.py tests/unit/test_trade_logger_close_ops_micro_structure.py` -> `5 passed`

## 남은 참고 메모

- Step 6 묶음은 모두 통과했지만 pandas `concat` / fragmented DataFrame 경고는 남아 있다
- 이 경고는 기능 실패는 아니고 성능/향후 버전 대응 이슈라서, 필요하면 별도 housekeeping 축으로 다루면 된다
