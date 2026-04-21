# Product Acceptance PA1 XAU Upper-Reject Mixed Forecast Wait Visibility Relief Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
family를 기존 `xau_upper_reject_mixed_guard_wait_as_wait_checks` contract에 합류시켰다.

핵심 변경:

- `barrier_guard 전용 mixed wait relief`를 `forecast_guard`까지 확장
- build에서 `blocked_display_reason = forecast_guard` carry
- resolve cadence suppression 재은닉 방지

반영 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

- `pytest -q tests/unit/test_consumer_check_state.py` -> `78 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `82 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `25 passed`

## 3. Representative Replay

representative hidden row replay 기준, current build는 이제 아래 contract로 본다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`

resolve replay에서도 같은 contract가 유지된다.

## 4. Live / Refreeze

재시작 로그:

- [cfd_main_restart_20260401_000440.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_000440.out.log)
- [cfd_main_restart_20260401_000440.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_000440.err.log)

재시작 이후 fresh XAU는 target mixed forecast 대신 아래 family로 이동했다.

- `upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
- `upper_reject_confirm + energy_soft_block + execution_soft_blocked`

그래도 PA0 refreeze 결과 target mixed forecast family는 `must_show 6 -> 0`으로 빠졌다.

delta 문서:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md)

## 5. 함께 확인된 Probe Forecast Follow-Up

같은 refreeze에서 `upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`도 `must_show 7 -> 0`으로 빠졌다.

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md)
