# Product Acceptance PA1 Sell Entry-Gate Wait Display Contract Follow-Up Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 follow-up은 SELL 쪽 entry-gate blocked family를 `WAIT + wait_check_repeat` 계약으로 공통 정리하는 축이다.

대상 family:

- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone / pyramid_not_progressed / pyramid_not_in_drawdown`
- `NAS100 + upper_break_fail_confirm + clustered_entry_price_zone / pyramid_not_progressed / pyramid_not_in_drawdown`
- `XAUUSD + upper_reject_mixed_confirm + clustered_entry_price_zone / pyramid_not_progressed / pyramid_not_in_drawdown`

## 2. 왜 follow-up이 한 번 더 필요했는가

policy mirror만 추가한 뒤 current-build replay는 정상적으로 `WAIT`로 보였지만, 첫 post-restart fresh row에서는 여전히 blank/hide가 남았다.

대표 fresh row:

- `2026-04-01T16:42:10`
- `XAUUSD + upper_reject_mixed_confirm + pyramid_not_in_drawdown`
- stored state:
  - `check_display_ready = false`
  - `check_stage = BLOCKED`
  - `chart_event_kind_hint = ""`
  - `chart_display_mode = ""`
  - `chart_display_reason = ""`

즉 이 축의 실제 문제는 `reason 미등록`이 아니라, hidden baseline이 modifier 단계에서 다시 살아나지 못하는 점이었다.

## 3. 이번에 고정한 계약

entry-gate family는 baseline이 `BLOCKED / hidden`이어도 chart wait policy가 restore될 수 있어야 한다.

공통 동작:

- `restore_hidden_display = true`
- `restore_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`

reason:

- `btc_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `nas_upper_break_fail_confirm_entry_gate_wait_as_wait_checks`
- `xau_upper_reject_mixed_confirm_entry_gate_wait_as_wait_checks`

## 4. owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- current-build replay에서 BTC/NAS/XAU entry-gate family가 `WAIT + wait_check_repeat`로 resolve될 것
- hidden baseline에서도 modifier가 `BLOCKED -> OBSERVE` visibility restore를 줄 것
- PA0 accepted wait-check 목록에서 reason 3개를 skip할 것
- exact fresh runtime row가 다시 뜨면 live CSV flat surface에도 같은 reason이 실제 기록될 것

## 6. 연결 문서

- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md)
- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md)
