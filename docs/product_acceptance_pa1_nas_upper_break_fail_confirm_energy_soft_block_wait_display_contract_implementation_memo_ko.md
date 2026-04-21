# Product Acceptance PA1 NAS Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`
family를 `WAIT + wait_check_repeat` contract로 올렸다.

새 reason:

- `nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `87 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `88 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `31 passed`

## 3. Representative Replay

대표 row:

- `2026-04-01T01:36:21`

current build / resolve 결과:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_break_fail_confirm_energy_soft_block_as_wait_checks`
- `display_repeat_count = 1`

즉 코드와 replay 기준으로는 이번 축이 닫혔다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260401_013639.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_013639.out.log)
- [cfd_main_restart_20260401_013639.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_013639.err.log)

재시작 이후 cfd PID:

- `23524`

cutoff:

- `2026-04-01T01:36:41`

fresh NAS row 관찰 결과:

- `upper_break_fail_confirm + forecast_guard + observe_state_wait` hidden family는 반복 확인
- exact `upper_break_fail_confirm + energy_soft_block + execution_soft_blocked` row는 관찰 window 안에서는 재발하지 않음

즉 live는 `exact energy family recurrence pending` 상태다.

## 5. PA0 Delta

delta 문서:

- [product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

직전 snapshot 대비 결과:

- `must_show 0 -> 0`
- `must_hide 0 -> 0`
- `must_block 12 -> 12`

이건 구현 실패라기보다 fresh exact row가 아직 새 contract로 recent window를 교체하지 못한 상태로 해석한다.

## 6. 현재 해석

이번 축은 아래처럼 본다.

- 코드 구현 완료
- 회귀 잠금 완료
- replay 확인 완료
- live exact recurrence 대기

즉 `implementation complete + live turnover pending` 상태다.

## 7. 같이 확인한 XAU turnover

같은 턴에 XAU promotion family turnover도 다시 확인했다.

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md)

결과:

- `must_show 12 -> 1`

즉 XAU promotion backlog는 거의 정리됐다.
