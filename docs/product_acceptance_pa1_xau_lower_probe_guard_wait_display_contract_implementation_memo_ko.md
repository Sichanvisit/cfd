# Product Acceptance PA1 XAU Lower Probe Guard Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 이번 축에서 한 일

`XAUUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe`
family를 new wait-display contract로 올렸다.

관련 문서:

- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_delta_ko.md)

## 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 구현 요약

- policy reason `xau_lower_probe_guard_wait_as_wait_checks`를 추가했다.
- build 단계에서 `blocked_display_reason`가 비지 않도록 carry를 추가했다.
- PA0가 이 reason을 accepted wait row로 건너뛰도록 연결했다.

## 대표 replay

대표 row `2026-04-01T14:04:02`를 current build로 replay하면:

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = forecast_guard`
- `chart_display_reason = xau_lower_probe_guard_wait_as_wait_checks`

## 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
102 passed
96 passed
39 passed
```

## live / PA0 메모

- restart log: [cfd_main_restart_20260401_141951.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_141951.out.log)
- err log: [cfd_main_restart_20260401_141951.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_141951.err.log)

post-restart watch에서는 exact target family fresh recurrence가 아직 다시 안 들어왔다.
그래서 current-build replay는 완료됐지만 PA0 actual cleanup은 fresh row 재발 대기 상태다.
