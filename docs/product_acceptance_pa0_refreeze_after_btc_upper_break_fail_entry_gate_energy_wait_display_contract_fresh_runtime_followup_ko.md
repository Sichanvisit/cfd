# Product Acceptance PA0 Refreeze After BTC Upper-Break-Fail Entry-Gate Energy Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## restart

- out log: [cfd_main_restart_20260401_151920.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.out.log)
- err log: [cfd_main_restart_20260401_151920.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.err.log)
- active pid: `25136`

## fresh runtime 상태

- `entry_decisions.csv` total rows: `2999`
- latest row time: `2026-04-01T15:20:54`

fresh row 유입 자체는 정상이다. 다만 restart 이후 watch 구간에서는 exact target family가 다시 기록되지 않았다.

확인 결과:

- `upper_break_fail_confirm + clustered_entry_price_zone`: recent target row는 있었지만 모두 old blank row
- `upper_break_fail_confirm + pyramid_not_progressed`: recent target row는 있었지만 모두 old blank row
- `upper_break_fail_confirm + pyramid_not_in_drawdown`: recent target row는 있었지만 모두 old blank row
- `upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`: recent target row는 있었지만 모두 old blank row

즉 post-restart fresh runtime에서 아직 아래 reason은 직접 기록되지 않았다.

- `btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

## current-build replay 확인

stored CSV는 아직 blank지만, current build로 representative row를 다시 태우면 결과는 정상이다.

- `2026-04-01T14:43:08` -> `WAIT + wait_check_repeat + btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `2026-04-01T14:42:16` -> `WAIT + wait_check_repeat + btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `2026-04-01T14:50:45` -> `WAIT + wait_check_repeat + btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

## 해석

이 follow-up은 구현 실패를 뜻하지 않는다.

- runtime은 살아 있고 fresh row는 들어온다.
- current build는 target family를 올바르게 resolve한다.
- 다만 restart 이후 watch 구간에 exact same family가 다시 안 나와서 live CSV `chart_display_reason` 증빙이 아직 비어 있다.

다음 체크포인트는 exact fresh target row가 한 번 더 나오면 곧바로 PA0를 refreeze해서 `clustered / energy` backlog가 실제로 줄어드는지 확인하는 것이다.
