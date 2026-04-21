# PA1 NAS Balanced Conflict Hidden Suppression Implementation Checklist

- [x] balanced conflict baseline suppression을 modifier reason으로 승격
- [x] PA0 accepted hidden suppression 목록에 새 reason 추가
- [x] PA0 raw-family fallback 추가
- [x] painter raw-family hidden suppression fallback 추가
- [x] consumer unit test 추가
- [x] painter unit test 추가
- [x] PA0 baseline freeze unit test 추가
- [x] `pytest -q tests/unit/test_consumer_check_state.py`
- [x] `pytest -q tests/unit/test_chart_painter.py`
- [x] `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py`
- [x] `main.py` 재시작
- [x] PA0 refreeze로 `must_show_missing 2 -> 0` 확인
- [x] 상세/memo/delta/follow-up 문서 연결
