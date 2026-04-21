# Product Acceptance PA1 XAU Upper-Reject Mixed Confirm Energy Soft-Block Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
family를 `WAIT + wait_check_repeat` contract로 올린 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)

## 2. 문제 family

이번 축의 target family는 아래였다.

- `symbol = XAUUSD`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = (blank)`

직전 PA0 latest 기준으로 이 family는 아래처럼 queue를 채우고 있었다.

- `must_show_missing = 9`
- `must_hide_leakage = 15`
- `must_block_candidates = 11`

## 3. 해석

이 family는 이미 live row 기준으로

- `check_stage = BLOCKED`
- `check_display_ready = True`
- `blocked_display_reason = energy_soft_block`

까지는 올라와 있었지만,
차트 쪽 contract가 비어 있어서 PA0 queue에 그대로 잡히고 있었다.

즉 질문은 아래였다.

```text
mixed confirm upper reject 구조가 이미 보이는 상태에서
energy soft block 때문에 실행만 막힌 row를
hidden leakage로 볼 것인가, WAIT 체크 surface로 볼 것인가?
```

이번 축의 결론은 `WAIT 체크 surface로 본다`이다.

이유:

- `upper_reject_confirm`, `upper_break_fail_confirm` energy-soft-block 축도 이미 같은 방향으로 정리됐다.
- 이 row는 `execution_soft_blocked`이지, 구조 자체가 무효라는 뜻이 아니다.
- 실제 live row도 이미 `display_ready=True`로 올라와 있어 hidden으로 보는 해석과 맞지 않는다.

## 4. representative replay 기준

대표 row:

- `2026-04-01T00:32:56`
- `2026-04-01T00:50:07`

current build replay 결과:

- `check_display_ready = True`
- `check_side = SELL`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `display_importance_source_reason = xau_upper_reject_development`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

resolve replay에서도 같은 contract가 유지된다.

## 5. 목표 contract

이번 축에서 고정하는 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

즉 `mixed confirm 구조는 보이되, 실행은 아직 energy soft block에 막힌 상태`를 WAIT surface로 표현하는 것이 목표다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 energy wait relief blocked reason carry를 추가한다.
3. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait-check reason으로 등록한다.

## 7. 이번 축에서 하지 않는 것

- XAU upper-reject probe promotion residue 정리
- XAU opposite-position-lock residue 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. fresh live row에서 새 reason이 실제로 찍힌다.
3. PA0 baseline script가 이 reason을 problem seed queue에서 제외한다.
4. delta 문서에 `must_show / must_hide / must_block` 감소를 수치로 남긴다.
