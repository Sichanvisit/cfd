# Product Acceptance PA1 XAU Upper-Reject Probe Promotion Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 축에서는
`XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
family를 `WAIT + wait_check_repeat` contract로 올렸다.

새 reason:

- `xau_upper_reject_probe_promotion_wait_as_wait_checks`

코드 반영:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `85 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `87 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `30 passed`

## 3. Representative Replay

대표 row:

- `2026-04-01T01:11:30`

current build / resolve 결과:

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_promotion_wait_as_wait_checks`
- `display_repeat_count = 2`

즉 build와 resolve 둘 다 새 wait contract를 유지한다.

## 4. Live Restart

재시작 로그:

- [cfd_main_restart_20260401_011221.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_011221.out.log)
- [cfd_main_restart_20260401_011221.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_011221.err.log)

재시작 이후 cfd PID:

- `29724`

cutoff:

- `2026-04-01T01:12:23`

fresh exact row:

- `2026-04-01T01:16:23`

fresh row state:

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_promotion_wait_as_wait_checks`

즉 이번 축은 replay뿐 아니라 live fresh row에서도 새 contract가 확인됐다.

## 5. PA0 Delta

delta 문서:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_delta_ko.md)

직전 snapshot 대비 결과:

- `must_show 15 -> 12`
- `must_hide 0 -> 0`
- `must_block 5 -> 0`

즉 fresh row가 들어오면서 block queue는 닫혔고, must-show는 old hidden backlog가 남아 있어 부분 감소 상태다.

## 6. 현재 해석

이번 축은 구현 자체는 닫혔다.

- build/resolve replay 확인 완료
- live fresh exact row 확인 완료
- PA0 `must_block` 제거 확인 완료

현재 남은 `must_show 12`는 같은 family old backlog turnover가 덜 끝난 상태로 본다.

## 7. 다음 residue

latest PA0 기준 다음 큰 residue는 아래다.

- 같은 family `must_show 12` turnover follow-up
- `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked` `must_block 9`
- `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe` `must_show 2 / must_block 2`

## 8. Turnover Follow-Up

같은 family turnover refreeze 기록:

- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md)

turnover 결과:

- `must_show 12 -> 1`
- `must_block 0 유지`

즉 XAU promotion backlog는 거의 정리된 상태다.
