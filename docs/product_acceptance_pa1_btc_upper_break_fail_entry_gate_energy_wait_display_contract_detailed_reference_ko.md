# Product Acceptance PA1 BTC Upper-Break-Fail Entry-Gate / Energy Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 하위축은 `BTCUSD + upper_break_fail_confirm` 계열에서 `entry gate`와 `energy soft block` 때문에 차트에서 숨겨지던 residue를 `WAIT + wait_check_repeat` 계약으로 올리는 작업이다.

직전 축인 `BTC upper-sell promotion / energy` 이후에도 아래 family가 PA0 queue에 남아 있었다.

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_progressed`
- `BTCUSD + upper_break_fail_confirm + pyramid_not_in_drawdown`
- `BTCUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`

## 2. 해석 기준

이 family는 `display leakage`가 아니라 다음으로 해석한다.

- 아직 진입은 열리지 않았지만
- 상단 리버설 confirm 구조는 살아 있고
- entry gate 또는 energy soft block 때문에 대기 중이며
- 차트에는 `기다림 + 반복 체크`로 보여주는 것이 맞다.

즉 `hide`가 아니라 `wait-style display relief`로 올린다.

## 3. 계약 분리

### entry gate family

대상:

- `clustered_entry_price_zone`
- `pyramid_not_progressed`
- `pyramid_not_in_drawdown`

계약:

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `blocked_display_reason = blocked_by`

### energy family

대상:

- `energy_soft_block + execution_soft_blocked`

계약:

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks`
- `blocked_display_reason = energy_soft_block`

## 4. owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- current-build replay에서 representative row가 `WAIT + wait_check_repeat`로 resolve될 것
- resolve 단계에서 late suppression이 다시 이 family를 숨기지 않을 것
- PA0 accepted wait-check 목록이 새 reason 2개를 skip할 것
- exact fresh runtime row가 다시 나오면 PA0 queue에서 이 family가 순차적으로 빠질 것

## 6. 연결 문서

- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md)
