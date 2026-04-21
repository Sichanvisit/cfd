# Product Acceptance PA0 Refreeze After NAS Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_013639.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_013639.json)
- `generated_at = 2026-04-01T01:31:42`

after latest:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T01:41:37`

target family:

- `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`

## 2. Representative Replay

대표 replay row:

- `2026-04-01T01:36:21`

current build / resolve 결과:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

## 3. Fresh Runtime Observation

cutoff:

- `2026-04-01T01:36:41`

관찰 window에서는 아래가 먼저 반복됐다.

- `NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait`

exact `energy_soft_block` family는 관찰 window 안에서 재발하지 않았다.

## 4. Target Delta

- `must_show 0 -> 0`
- `must_hide 0 -> 0`
- `must_block 12 -> 12`

핵심 해석:

- replay 기준 계약은 맞다.
- 다만 recent window를 갱신할 fresh exact row가 아직 없어서 PA0 block queue는 그대로다.

## 5. Latest Queue Composition

latest queue는 아래처럼 재편됐다.

- `must_block 12`: `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`
- `must_show 9`: `XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait`
- `must_show 6`: `XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait`
- `must_hide 9`: `BTCUSD + upper_reject_confirm + forecast_guard + observe_state_wait`
- `must_hide 4`: `BTCUSD + upper_break_fail_confirm + forecast_guard + observe_state_wait`
- `must_hide 2`: `BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`

## 6. 결론

이번 NAS energy 축은 `구현/회귀/replay는 닫혔고, live exact recurrence만 남은 상태`다.

다음 확인 포인트는 단순하다.

1. fresh exact `energy_soft_block` row가 새 reason으로 찍히는지 다시 본다.
2. 그 직후 PA0를 다시 얼려 `must_block 12 -> 0`을 확인한다.
