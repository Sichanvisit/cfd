# Product Acceptance PA1 XAU Outer-Band Probe Guard Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 이번 축에서 한 일

`XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
family 안의 `probe_against_default_side` hidden row를 structural wait contract로 다시 연결했다.

관련 문서:

- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_guard_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_guard_wait_display_contract_delta_ko.md)

## 변경 owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 구현 요약

- `xau_outer_band_probe_against_default_side_wait_relief`를 추가했다.
- `probe_against_default_side`가 structural wait row를 `display_blocked`로 죽이지 않게 했다.
- generic `probe_guard_wait_as_wait_checks` reason을 재사용했다.

## 대표 replay

대표 row `2026-04-01T01:48:48`을 current build로 replay하면:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = outer_band_guard`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

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

post-restart watch에서는 exact target family fresh recurrence가 아직 없었다.
그래서 current-build replay는 해결됐지만, PA0 actual cleanup은 old backlog turnover 기준으로만 확인 중이다.
