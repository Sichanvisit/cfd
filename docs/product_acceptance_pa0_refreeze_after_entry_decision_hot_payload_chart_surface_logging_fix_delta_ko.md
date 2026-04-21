# Product Acceptance PA0 Refreeze After Entry-Decision Hot Payload Chart Surface Logging Fix Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline: [product_acceptance_pa0_baseline_snapshot_20260401_153345.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_153345.json)
- after baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T15:56:08`

## summary delta

- `recent_entry_row_count: 360 -> 22`
- `must_show_missing_count: 15 -> 14`
- `must_hide_leakage_count: 0 -> 0`
- `must_enter_candidate_count: 12 -> 3`
- `must_block_candidate_count: 12 -> 5`
- `must_hold_candidate_count: 2 -> 2`
- `must_release_candidate_count: 10 -> 10`
- `bad_exit_candidate_count: 10 -> 10`

## 해석

이번 delta는 특정 residue 축 하나를 닫은 결과라기보다,
active `entry_decisions.csv`가 새 header / 새 surface로 rollover된 상태를 반영한 결과다.

중요한 포인트는 숫자 자체보다 다음이다.

- fresh active CSV에서 non-empty `chart_display_reason` row가 실제로 기록됐다.
- PA0가 이제 live CSV flat surface를 근거로 chart acceptance evidence를 읽을 수 있게 됐다.

대표 fresh row:

- `2026-04-01T15:54:06` `XAUUSD`
  - `WAIT + wait_check_repeat + xau_upper_reject_confirm_energy_soft_block_as_wait_checks`
- `2026-04-01T15:55:44` `XAUUSD`
  - `WAIT + wait_check_repeat + xau_upper_reject_confirm_forecast_wait_as_wait_checks`

즉 이번 delta의 핵심은 `logging surface activation`이다.

## current residue reading

latest active window에서는 queue가 짧아졌고,
남은 `must_show / must_block / must_enter`는 이전 대형 backlog보다
fresh active runtime에서 아직 chart surface가 비어 있는 BTC / NAS 계열이 메인이다.

따라서 이후 blank residue는
`logging omission`이 아니라 `logic residue`로 다시 해석하는 것이 맞다.
