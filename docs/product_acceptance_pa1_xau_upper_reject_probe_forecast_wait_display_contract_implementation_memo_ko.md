# Product Acceptance PA1 XAU Upper-Reject Probe Forecast Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 구현 요약

이번 축에서는
`XAUUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`
family를 `WAIT + wait_check_repeat` contract로 올렸다.

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

새 reason:

- `xau_upper_reject_probe_forecast_wait_as_wait_checks`

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `77 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `81 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `24 passed`

## 3. Representative Replay

대표 row:

- `2026-03-31T23:33:28`

current build replay 결과:

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_forecast_wait_as_wait_checks`

resolve replay에서도 같은 contract가 유지됐다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260331_234652.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_234652.out.log)
- [cfd_main_restart_20260331_234652.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_234652.err.log)

재시작 이후 cfd PID:

- `25004`

cutoff:

- `2026-03-31T23:46:54`

fresh XAU row watch 결과:

- exact target fresh row = `0`
- `xau_upper_reject_probe_forecast_wait_as_wait_checks` fresh row = `0`

즉 이번 축은 `코드/테스트/replay 완료`, `live exact recurrence pending` 상태다.

## 5. PA0 Delta

delta 기록:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md)

현재 해석:

- build와 resolve는 target contract를 정확히 만든다.
- 하지만 PA0 latest에는 old hidden backlog가 아직 recent window에 남아 있어 target `must_show`가 `7`로 유지된다.

## 6. 함께 본 Upper-Reject Confirm Recheck

같은 턴에서 `upper_reject_confirm + energy_soft_block` follow-up도 다시 확인했다.

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md)

이 축은 `must_show 5 -> 0`으로 닫힌 상태다.

## 7. 추가 Fresh Runtime Follow-Up

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md)
