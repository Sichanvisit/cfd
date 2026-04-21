# Product Acceptance PA1 XAU Middle-Anchor Probe Guard Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 하위축은 `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe` residue를 다시 점검하는 작업이다.

latest PA0 기준 이 family는 다음으로 남아 있었다.

- `must_show_missing = 4`
- `must_block_candidates = 4`

대표 row는 다음이다.

- `2026-04-01T14:59:07`
- `2026-04-01T14:59:15`
- `2026-04-01T14:59:46`
- `2026-04-01T14:59:54`

## 2. 핵심 판단

이번 축은 새 production modifier를 더 추가해야 하는 케이스가 아니었다.

current-build replay 결과 이 family는 이미 공통 계약인 `probe_guard_wait_as_wait_checks`로 정상 resolve된다.

즉 이번 residue는:

- `로직 미구현` 문제가 아니라
- `old blank row backlog + exact fresh recurrence 부재`

로 보는 것이 맞다.

## 3. current-build 계약

대표 replay 기준:

- `check_side = BUY`
- `check_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`
- `display_importance_source_reason = xau_second_support_reclaim`
- `display_importance_tier = medium`

resolve 이후에는:

- `blocked_display_reason = middle_sr_anchor_guard`

까지 정상적으로 carry된다.

## 4. owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. 이번 턴의 목표

- exact family가 이미 generic contract에 포함된다는 점을 재확인
- exact family용 회귀 테스트를 추가해서 이후 회귀를 방지
- fresh runtime recurrence가 없는 상태에서도 queue가 왜 남아 있는지 문서로 고정

## 6. 연결 문서

- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)
