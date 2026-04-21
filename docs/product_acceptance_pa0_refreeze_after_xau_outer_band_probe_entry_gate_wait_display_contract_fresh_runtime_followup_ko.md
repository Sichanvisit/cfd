# Product Acceptance PA0 Refreeze After XAU Outer-Band Probe Entry-Gate Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## 1. watch 조건

- restart:
  - [cfd_main_restart_20260401_173548.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_173548.out.log)
  - [cfd_main_restart_20260401_173548.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_173548.err.log)
- cutoff:
  - `2026-04-01T17:16:53`

## 2. watch 결과

- recent row count: `16`
- latest row time: `2026-04-01T17:38:33`
- exact fresh recurrence count:
  - `XAUUSD + outer_band_reversal_support_required_observe + blocked entry-gate + xau_upper_sell_probe = 0`

즉 restart 이후 짧은 watch에서는 target exact family가 다시 뜨지 않았다.

## 3. 대신 확인된 것

representative replay는 명확했다.

sample stored row:

- `2026-04-01T17:16:51`
- stored:
  - `check_display_ready = False`
  - `check_stage = BLOCKED`
  - `chart_event_kind_hint = ""`
  - `chart_display_mode = ""`
  - `chart_display_reason = ""`

current build replay:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = clustered_entry_price_zone`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_outer_band_probe_entry_gate_wait_as_wait_checks`

즉 exact fresh row가 다시 뜨기만 하면 새 wait contract로 기록되어야 하는 상태다.

## 4. refreeze 결과

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T17:38:47`

target family contribution:

- `must_show = 14`
- `must_enter = 10`

따라서 이번 follow-up 시점 상태는 아래로 본다.

- 코드 반영 완료
- 회귀 테스트 완료
- representative replay 확인 완료
- live exact fresh row 직접 증빙 pending
- PA0 actual cleanup pending
