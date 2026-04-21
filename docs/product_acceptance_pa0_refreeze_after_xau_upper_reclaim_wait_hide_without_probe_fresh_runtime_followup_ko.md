# Product Acceptance PA0 Refreeze After XAU Upper-Reclaim Wait Hide Without Probe Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## 1. watch 조건

- restart:
  - [cfd_main_restart_20260401_171408.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_171408.out.log)
  - [cfd_main_restart_20260401_171408.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_171408.err.log)
- cutoff:
  - `2026-04-01T17:14:06`

## 2. watch 결과

- recent row count: `30`
- latest row time: `2026-04-01T17:16:31`
- exact fresh recurrence count:
  - `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe = 0`

즉 이번 short watch에서는 exact fresh row가 새 hidden reason으로 찍히는 장면까지는 확보하지 못했다.

## 3. 대신 확인된 것

representative replay는 명확했다.

sample stored row:

- `2026-04-01T16:36:38`

current build replay:

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `modifier_primary_reason = xau_upper_reclaim_wait_hide_without_probe`
- `modifier_stage_adjustment = visibility_suppressed`

즉 live exact recurrence가 다시 뜨기만 하면 이 family는 새 hidden suppression reason으로 내려가야 하는 상태다.

## 4. refreeze 결과

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T17:16:41`

target family contribution:

- `must_hide 5 -> 0`
- `must_block 5 -> 0`

즉 direct fresh proof는 없었지만, turnover 기준으로는 이 축이 queue에서 빠진 것이 확인됐다.

## 5. 현재 판단

이번 축 상태는 아래로 정리한다.

- 코드 반영 완료
- 회귀 테스트 완료
- representative replay 확인 완료
- live exact fresh row 직접 증빙은 pending
- PA0 queue cleanup은 완료
