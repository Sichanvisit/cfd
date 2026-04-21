# Product Acceptance PA1 XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
family를 `hidden blocked confirm`에서 `WAIT + repeated checks` contract로 올리는 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

latest PA0 기준 main residue는 아래 family였다.

- `symbol = XAUUSD`
- `observe_reason = upper_reject_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = ""`

직전 latest queue에서는:

- `must_show_missing = 12`

를 채우고 있었다.

## 3. 해석

이번 축의 질문은 아래와 같다.

```text
upper reject confirm은 이미 맞는데
energy soft block 때문에 실행이 막힌 상태를
차트에서 계속 숨길 것인가, WAIT로 남길 것인가?
```

이번 축의 답은 `WAIT로 남긴다` 쪽이다.

이 family는:

- no-probe confirm family지만
- confirm 의미는 이미 충분히 있고
- execution soft block 때문에 entry만 보류된 상태다.

즉 `보이지 말아야 할 leakage`보다는
`confirm-blocked wait surface`로 보는 쪽이 맞다.

## 4. 실제 문제는 무엇이었나

대표 row replay 전 상태는 아래와 같았다.

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `blocked_display_reason = execution_soft_blocked`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

중요한 점은 이 family가 단순히 build에서 숨는 것만이 아니라,
원래 blocked visible 후보가 `xau_upper_sell_repeat_suppressed`에 다시 눌려 사라지는 구조였다는 점이다.

## 5. 목표 contract

이번 하위축에서 고정한 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_confirm_energy_soft_block_as_wait_checks`

즉 hidden confirm blocked가 아니라
`WAIT + repeated checks`
surface로 올리는 것이 목표다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
   `xau_upper_reject_confirm_energy_soft_block_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
   `xau_upper_reject_confirm_energy_wait_relief`를 추가한다.
3. same file에서 `xau_upper_sell_repeat_suppressed`가 target family를 다시 숨기지 않게 예외를 넣는다.
4. blocked reason carry와 PA0 accepted wait-check reason 등록을 같이 반영한다.

## 7. 이번 축에서 하지 않는 것

- `upper_break_fail_confirm + energy_soft_block` mirror family 정리
- XAU mixed confirm leakage 정리
- BTC upper sell blocked family 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. fresh exact row가 생기면 PA0 queue에서 target family가 줄어든다.
4. fresh exact row가 없으면 memo/delta에 `구현 완료 but live recurrence pending` 상태를 분리 기록한다.
