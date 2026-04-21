# Product Acceptance PA1 XAU Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
family를 `hidden blocked confirm`에서 `WAIT + repeated checks` contract로 올린 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

latest PA0 기준 mirror residue는 아래 family였다.

- `symbol = XAUUSD`
- `observe_reason = upper_break_fail_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = ""`

직전 latest queue에서는:

- `must_show_missing = 3`

을 채우고 있었다.

## 3. 해석

이번 축의 질문은 아래와 같다.

```text
upper break fail confirm이 이미 맞는데
energy soft block 때문에 실행만 보류된 상태를
차트에서 계속 숨길 것인가, WAIT로 남길 것인가?
```

이번 축의 답은 `WAIT로 남긴다` 쪽이다.

이 family는:

- no-probe confirm family이고
- 의미상 `upper_reject_confirm` mirror에 가깝고
- 실행만 soft block 된 상태다.

즉 숨기는 것보다 `blocked confirm wait surface`로 남기는 편이 맞다.

## 4. 실제 문제는 무엇이었나

대표 row replay 전 상태는 아래와 같았다.

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `blocked_display_reason = execution_soft_blocked`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

구조는 직전 `upper_reject_confirm` 축과 거의 같았고,
핵심 suppress owner도 동일하게 `xau_upper_sell_repeat_suppressed`였다.

## 5. 목표 contract

이번 하위축에서 고정한 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_break_fail_confirm_energy_soft_block_as_wait_checks`

즉 hidden blocked confirm이 아니라
`WAIT + repeated checks`
surface로 올리는 것이 목표다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
   `xau_upper_break_fail_confirm_energy_soft_block_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
   `xau_upper_break_fail_confirm_energy_wait_relief`를 추가한다.
3. same file에서 `xau_upper_sell_repeat_suppressed`가 target family를 다시 숨기지 않게 예외를 넣는다.
4. blocked reason carry와 PA0 accepted wait-check reason 등록을 같이 반영한다.

## 7. 이번 축에서 하지 않는 것

- `upper_reject_confirm + energy_soft_block` fresh 재발 재확인
- BTC upper sell blocked family 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. fresh exact row가 생기면 live row에서 same reason이 찍히는지 확인한다.
4. fresh exact row가 없더라도 PA0 queue가 빠졌는지 memo/delta에 분리 기록한다.
