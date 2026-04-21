# Product Acceptance PA1 BTC Upper-Break-Fail Entry-Gate / Energy Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 이번 턴에서 한 일

`BTCUSD + upper_break_fail_confirm` 하위축의 entry gate / energy residue를 `WAIT + wait_check_repeat` 계약으로 올렸다.

관련 문서:

- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 요약

- policy에 `btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`를 추가했다.
- policy에 `btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks`를 추가했다.
- build 단계에서 entry gate / energy row 모두 `blocked_display_reason`를 carry하게 맞췄다.
- resolve 단계에서 `DEFAULT_LATE_DISPLAY_SUPPRESS_GUARDS_V1`가 entry gate family를 다시 숨기지 않게 exemption을 넣었다.
- PA0 accepted wait-check reason 목록에 새 reason 2개를 올렸다.

## 4. representative replay

### entry gate

- row: `2026-04-01T14:43:08`
- family: `upper_break_fail_confirm + clustered_entry_price_zone`
- stored:
  - `chart_event_kind_hint = ""`
  - `chart_display_mode = ""`
  - `chart_display_reason = ""`
- build / resolve:
  - `check_display_ready = True`
  - `check_stage = OBSERVE`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
  - `blocked_display_reason = clustered_entry_price_zone`

### pyramid gate

- row: `2026-04-01T14:42:16`
- family: `upper_break_fail_confirm + pyramid_not_progressed`
- build / resolve:
  - `check_display_ready = True`
  - `check_stage = OBSERVE`
  - `chart_display_reason = btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
  - `blocked_display_reason = pyramid_not_progressed`

### energy soft block

- row: `2026-04-01T14:50:45`
- family: `upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`
- build / resolve:
  - `check_display_ready = True`
  - `check_stage = BLOCKED`
  - `chart_event_kind_hint = WAIT`
  - `chart_display_mode = wait_check_repeat`
  - `chart_display_reason = btc_upper_break_fail_confirm_energy_soft_block_as_wait_checks`
  - `blocked_display_reason = energy_soft_block`

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
112 passed
101 passed
44 passed
```

## 6. live / refreeze 메모

- restart log: [cfd_main_restart_20260401_151920.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.out.log)
- err log: [cfd_main_restart_20260401_151920.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_151920.err.log)
- active pid: `25136`

fresh row는 다시 움직였다.

- `entry_decisions.csv` total rows: `2999`
- latest row time: `2026-04-01T15:20:54`

하지만 post-restart watch에서는 exact target family fresh recurrence가 다시 나오지 않았다. 그래서 stored CSV 기준 `chart_display_reason`는 아직 blank old row가 recent window에 남아 있다.

## 7. 현재 해석

이번 축은 `코드 / 테스트 / replay`는 닫혔다.

actual PA0 cleanup은 부분 진행 상태다.

- `clustered_entry must_show: 4 -> 6`
- `pyramid_not_progressed must_show: 4 -> 1`
- `pyramid_not_in_drawdown must_show: 3 -> 0`
- `energy_soft_block must_block: 5 -> 4`

즉 `pyramid / drawdown` 쪽은 줄었지만, `clustered`와 `energy`는 exact fresh recurrence가 아직 없어 old blank backlog가 남아 있다.

다음 체크포인트는 exact fresh row가 다시 나오는 순간 PA0를 한 번 더 얼려서 `clustered / energy`가 실제로 빠지는지 확인하는 것이다.
