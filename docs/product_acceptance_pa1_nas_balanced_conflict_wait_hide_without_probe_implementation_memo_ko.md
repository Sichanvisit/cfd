# PA1 NAS Balanced Conflict Hidden Suppression Implementation Memo

## 구현 요약

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py) 에서
  `balanced_conflict_display_suppressed` baseline hidden case를
  `balanced_conflict_wait_hide_without_probe`로 명시했다.
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py) 는
  새 reason을 accepted hidden suppression 목록에 추가했고,
  live CSV flat payload가 여전히 blank여도 raw balanced-conflict family를 accepted hidden으로 건너뛰도록 했다.
- [chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_painter.py) 도 같은 raw-family fallback을 추가해
  flat payload reason 부재 시에도 hidden flow suppression을 유지한다.

## 회귀

- `pytest -q tests/unit/test_consumer_check_state.py` -> `127 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `109 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `52 passed`

## live/runtime 메모

- restart 이후 exact fresh row는 계속 들어왔다.
- 다만 flat CSV column은 여전히
  `chart_event_kind_hint/chart_display_mode/chart_display_reason/modifier_primary_reason=(blank)`였다.
- representative replay는 같은 row를 current build에 다시 태우면
  `modifier_primary_reason=balanced_conflict_wait_hide_without_probe`를 반환했다.
- 그래서 이번 축은 `reason replay + accepted hidden raw-family fallback`으로 PA0를 닫은 케이스다.

## 결과

- latest PA0 baseline에서 `must_show_missing_count=0`
- chart acceptance queue는 사실상 종료 상태가 됐다.
