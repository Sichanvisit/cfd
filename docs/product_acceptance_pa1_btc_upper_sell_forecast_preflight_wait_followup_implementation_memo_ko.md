# Product Acceptance PA1 BTC Upper-Sell Forecast Preflight Wait Follow-Up Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 follow-up에서는 BTC 상단 sell 잔여 3개를 추가로 WAIT contract로 올렸다.

- `btc_upper_break_fail_confirm_forecast_wait_as_wait_checks`
- `btc_upper_reject_probe_forecast_wait_as_wait_checks`
- `btc_upper_reject_confirm_preflight_wait_as_wait_checks`

반영 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

- `pytest -q tests/unit/test_consumer_check_state.py` -> `98 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `94 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `37 passed`

## 3. Representative Replay

### break-fail forecast

- `2026-04-01T01:45:56`
- build/resolve 공통:
  - `display_ready = True`
  - `stage = OBSERVE`
  - `blocked_display_reason = forecast_guard`
  - `chart_display_reason = btc_upper_break_fail_confirm_forecast_wait_as_wait_checks`

### probe forecast

- `2026-04-01T01:40:49`
- build/resolve 공통:
  - `display_ready = True`
  - `stage = PROBE`
  - `blocked_display_reason = forecast_guard`
  - `chart_display_reason = btc_upper_reject_probe_forecast_wait_as_wait_checks`

### confirm preflight

- `2026-04-01T01:44:55`
- build/resolve 공통:
  - `display_ready = True`
  - `stage = BLOCKED`
  - `blocked_display_reason = preflight_action_blocked`
  - `chart_display_reason = btc_upper_reject_confirm_preflight_wait_as_wait_checks`

## 4. PA0 Delta

delta 문서:

- [product_acceptance_pa0_refreeze_after_btc_upper_sell_forecast_preflight_wait_followup_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_upper_sell_forecast_preflight_wait_followup_delta_ko.md)

결과:

- break-fail forecast `must_hide 4 -> 4`
- probe forecast `must_hide 2 -> 2`
- confirm preflight `must_block 2 -> 2`
- 기존 residue인 confirm forecast `9 -> 9`, probe preflight `10 -> 10`도 그대로

즉 이번 follow-up도 replay/테스트는 완료됐고, PA0 queue는 live fresh row가 없어서 아직 안 줄었다.

## 5. Live 상태

runtime는 새 코드로 올라와 있지만 fresh row는 계속 막혀 있다.

- active main pid: `13908`
- err log: [cfd_main_restart_20260401_132056.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_132056.err.log)
- 핵심 상태: `MT5 connection unavailable`

따라서 지금 BTC 상단 sell 계열은 `코드/테스트/replay 선반영 완료` 상태로 쌓여 있고, 실제 PA0 cleanup은 MT5 연결 복구 후 fresh runtime row가 다시 쌓여야 움직인다.
