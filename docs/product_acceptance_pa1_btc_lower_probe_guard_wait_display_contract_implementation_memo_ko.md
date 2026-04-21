# Product Acceptance PA1 BTC Lower-Probe Guard Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`BTCUSD + lower_rebound_probe_observe + {forecast_guard | barrier_guard} + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 `WAIT + wait_check_repeat` contract로 올렸다.

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

새 reason:

- `btc_lower_probe_guard_wait_as_wait_checks`

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `80 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `83 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `26 passed`

## 3. Representative Replay

대표 row:

- `2026-04-01T00:00:12` (`forecast_guard`)
- `2026-04-01T00:00:46` (`barrier_guard`)

current build replay 결과:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard | barrier_guard`
- `display_importance_tier = medium`
- `display_importance_source_reason = btc_lower_recovery_start`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_probe_guard_wait_as_wait_checks`

resolve replay에서도 같은 contract가 유지되었다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260401_002123.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_002123.out.log)
- [cfd_main_restart_20260401_002123.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_002123.err.log)

재시작 이후 cfd PID:

- `27388`

cutoff:

- `2026-04-01T00:21:23`

fresh BTC row watch 결과:

- fresh BTC row = `11`
- exact target recurrence = `0`

fresh BTC는 이번 watch 구간에서 target family 대신 아래 family로 이동했다.

- `upper_reject_probe_observe + probe_not_promoted + btc_upper_sell_probe`
- `middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`

즉 이번 축은 `live exact recurrence pending`이었지만, target family는 recent window에서 다시 재발하지 않았다.

## 5. PA0 Delta

delta 기록:

- [product_acceptance_pa0_refreeze_after_btc_lower_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_probe_guard_wait_display_contract_delta_ko.md)

핵심 해석:

- representative replay는 새 contract를 정확히 만든다.
- live fresh row는 exact recurrence가 없었다.
- 그럼에도 recent window turnover 이후 PA0 queue에서 target family는 모두 사라졌다.

즉 상태를 한 줄로 정리하면:

```text
구현 완료 + replay 확인 완료 + live exact recurrence 없음 + queue turnover로 닫힘
```

## 6. 현재 잔여 queue

latest PA0 기준 main residue는 이제 아래로 바뀌었다.

- `must_show_missing = 13`: `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`
- `must_hide_leakage = 10`: `XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `must_block_candidates = 12`: `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`

즉 lower-rebound probe family는 닫혔고, 다음 BTC 메인은 middle-anchor no-probe residue다.
