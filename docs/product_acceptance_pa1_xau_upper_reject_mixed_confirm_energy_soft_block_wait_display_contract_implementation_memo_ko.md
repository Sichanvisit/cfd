# Product Acceptance PA1 XAU Upper-Reject Mixed Confirm Energy Soft-Block Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
family를 `WAIT + wait_check_repeat` contract로 올렸다.

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

새 reason:

- `xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `83 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `86 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `29 passed`

## 3. Representative Replay

대표 row:

- `2026-04-01T00:32:56`
- `2026-04-01T00:50:07`

current build replay 결과:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `display_importance_source_reason = xau_upper_reject_development`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

resolve replay에서도 같은 contract가 유지됐다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260401_005634.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_005634.out.log)
- [cfd_main_restart_20260401_005634.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_005634.err.log)

재시작 이후 cfd PID:

- `16700`

cutoff:

- `2026-04-01T00:56:34`

fresh XAU row watch 결과:

- fresh XAU row = `21`
- exact target fresh row = `1`

대표 fresh row:

- `2026-04-01T01:00:11`

fresh row state:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

즉 이번 축은 replay뿐 아니라 fresh live까지 확인됐다.

## 5. PA0 Delta

delta 기록:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

핵심 결과:

- `must_show 9 -> 0`
- `must_hide 15 -> 3`
- `must_block 11 -> 3`

즉 이 family는 크게 줄었고, old backlog 일부만 남은 상태다.

## 6. 현재 잔여 queue

latest PA0 기준 main residue는 아래로 바뀌었다.

- `must_show_missing = 15`: `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
- `must_hide_leakage = 3`: `XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `must_block_candidates = 5`: `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
- `must_block_candidates = 4`: `XAUUSD + outer_band_reversal_support_required_observe + opposite_position_lock + opposite_position_lock + xau_upper_sell_probe`

즉 다음 XAU 메인축은 upper-reject probe promotion family다.
