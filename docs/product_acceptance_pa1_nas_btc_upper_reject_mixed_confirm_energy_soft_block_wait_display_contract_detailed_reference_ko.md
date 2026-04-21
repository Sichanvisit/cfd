# Product Acceptance PA1 NAS/BTC Upper-Reject Mixed-Confirm Energy-Soft-Block Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 하위축은 아래 SELL mixed-confirm energy residue를
`WAIT + wait_check_repeat` contract로 올리는 작업이다.

- `NAS100 + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `BTCUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

직전 active runtime 기준으로 이 family는 live row에서 아래처럼 잡혔다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `entry_block_reason = execution_soft_blocked`
- 그런데 `chart_event_kind_hint / chart_display_mode / chart_display_reason`는 blank

즉 `hide`가 아니라 `wait contract 누락`으로 봐야 하는 residue였다.

## 2. 해석 기준

이 family는

- 방향은 이미 `SELL`로 잡혀 있고
- confirm 구조도 살아 있으며
- 에너지 제한 때문에 실행만 보류된 상태다.

그래서 chart에선 `막아야 할 leakage`가 아니라
`기다림 + 반복 체크`로 보여주는 것이 맞다.

## 3. 계약

### NAS mirror

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

### BTC mirror

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

공통:

- `side = SELL`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_absent`
- `stage = BLOCKED`

## 4. owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- current-build에서 NAS/BTC mixed-confirm energy row가 `WAIT + wait_check_repeat`로 resolve될 것
- live fresh row에서 flat/nested chart reason이 같이 기록될 것
- PA0에서 이 family가 `must_block` / `must_show` queue에서 빠질 것

## 6. 연결 문서

- [product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md)
