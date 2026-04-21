# Product Acceptance PA1 XAU Upper-Reject Confirm Forecast Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
family를 hidden wait에서 `WAIT + wait_check_repeat`로 올렸다.

핵심 변경:

- `xau_upper_reject_confirm_forecast_wait_as_wait_checks` policy 추가
- build path에서 `xau_upper_reject_confirm_forecast_wait_relief` 추가
- `xau_upper_reject_guard_wait_hidden` / `xau_upper_reject_late_hidden` / `xau_upper_reject_cadence_suppressed`가 이 family를 다시 죽이지 않도록 narrow exemption 추가
- PA0 accepted wait reason에 새 reason 추가

반영 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

- `pytest -q tests/unit/test_consumer_check_state.py` -> `88 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `89 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `32 passed`

## 3. Representative Replay

representative confirm row `2026-04-01T01:43:59` replay 기준 current build는 아래 contract로 올라간다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_confirm_forecast_wait_as_wait_checks`
- `display_repeat_count = 3`

resolve replay에서도 같은 contract가 유지된다.

같은 시점 mixed forecast representative row `2026-04-01T01:43:29`도 여전히
`xau_upper_reject_mixed_guard_wait_as_wait_checks`
contract로 유지되는 것을 같이 재확인했다.

## 4. Live / Refreeze

재시작 로그:

- [cfd_main_restart_20260401_125318.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_125318.out.log)
- [cfd_main_restart_20260401_125318.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_125318.err.log)

이번 재시작 뒤에는 fresh runtime row가 아예 쌓이지 않았다.

- watch cutoff: `2026-04-01T12:54:13`
- fresh `BTC/NAS/XAU` row count: 모두 `0`
- latest persisted row time: `2026-04-01T01:49:24`
- err log에는 `MT5 connection unavailable` 재시도 로그가 남았다.

그래서 이번 턴의 live 확인은 `fresh exact row 확인`이 아니라
`replay 확인 + turnover refreeze` 기준으로 닫았다.

## 5. PA0 Delta

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_014137.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_014137.json)

after latest:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

delta 문서:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_forecast_wait_display_contract_delta_ko.md)

핵심 결과:

- `XAU upper_reject_confirm + forecast_guard` -> `must_show 9 -> 5`
- `XAU upper_reject_mixed_confirm + forecast_guard` -> `must_show 6 -> 6`
- `NAS upper_break_fail_confirm + energy_soft_block` -> `must_block 12 -> 0`

즉 confirm forecast는 현재 구현 완료 + turnover partial close 상태이고,
mixed forecast는 구현 대상이 아니라 기존 contract 유지 확인 상태다.
