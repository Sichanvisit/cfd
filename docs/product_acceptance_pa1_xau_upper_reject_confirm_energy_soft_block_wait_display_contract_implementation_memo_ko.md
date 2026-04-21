# Product Acceptance PA1 XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 하위축에서 한 일

이번 PA1 하위축에서는
`XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
family를 `WAIT + repeated checks` contract로 올렸다.

이 family는 no-probe confirm blocked row라서,
probe family처럼 빠르게 보이는 신호는 아니지만
차트에서 완전히 숨길 대상도 아니라고 판단했다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. wait contract 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_upper_reject_confirm_energy_soft_block_as_wait_checks`를 추가했다.

조건:

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = upper_reject_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_absent = True`
- `stage = BLOCKED`

반환:

- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_upper_reject_confirm_energy_soft_block_as_wait_checks`

### 3-2. suppression 예외

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`xau_upper_reject_confirm_energy_wait_relief`를 추가하고,
`xau_upper_sell_repeat_suppressed`가 target family를 다시 숨기지 않도록 예외를 넣었다.

### 3-3. blocked reason carry / PA0 skip

same file에서 `blocked_display_reason = energy_soft_block`가 유지되도록 했고,
[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
새 display reason을 accepted wait-check reason으로 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
73 passed
79 passed
22 passed
```

고정된 테스트:

- [test_build_consumer_check_state_keeps_xau_upper_reject_confirm_energy_soft_block_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_xau_upper_reject_confirm_energy_soft_block_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_xau_upper_reject_confirm_energy_soft_block_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_xau_upper_reject_confirm_energy_soft_block_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. current-build replay

representative replay (`2026-03-31T23:10:54`) 결과는 아래와 같다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `check_side = SELL`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_confirm_energy_soft_block_as_wait_checks`
- `display_repeat_count = 3`
- `display_strength_level = 5`
- `display_score = 0.91`
- `display_importance_tier = high`
- `display_importance_source_reason = xau_upper_reject_core`

resolve replay에서도 같은 reason과 blocked_display_reason이 유지됐다.

## 6. live/runtime 확인

cfd runtime은 아래 로그 기준으로 재시작했다.

- out log: [cfd_main_restart_20260331_231838.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_231838.out.log)
- err log: [cfd_main_restart_20260331_231838.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_231838.err.log)

post-restart cutoff (`2026-03-31T23:18:40`) 이후:

- exact target fresh row = `0`
- `WAIT + wait_check_repeat + xau_upper_reject_confirm_energy_soft_block_as_wait_checks` fresh row = `0`

즉 이번 축은
`구현 / replay / 테스트는 완료`
지만
`fresh exact row live 증빙은 아직 없음`
상태다.

## 7. 판단

이번 축은 코드 단에서는 닫혔다고 본다.

근거:

- current-build replay가 WAIT contract로 바뀜
- resolve replay가 같은 contract를 유지함
- 회귀 테스트 전부 통과

다만 PA0 queue는 old hidden backlog가 recent window에 그대로 남아 있어서,
fresh exact row가 다시 찍히기 전까지는 `must_show` residue가 그대로 보이는 상태다.
