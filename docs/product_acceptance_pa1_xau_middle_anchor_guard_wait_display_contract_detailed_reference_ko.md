# Product Acceptance PA1 XAU Middle-Anchor Guard Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
family를 왜 다시 열었는지와,
이번 축이 `hidden suppression`이 아니라
`WAIT + repeated checks` contract 축이라는 점을 고정하는 상세 reference다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

latest PA0 기준 target family는 아래와 같다.

- `symbol = XAUUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`

직전 baseline에서 이 family는

- `must_show_missing = 12`

를 채우고 있었다.

## 3. 이 family를 어떻게 해석할 것인가

이번 축의 질문은 아래 한 줄이다.

```text
middle anchor guard 때문에 아직 들어가면 안 되지만,
차트에는 구조 확인 중인 WAIT로 남겨야 하는가?
```

이번 축에서는 이 질문에 `그렇다`로 답한다.

즉 이 family는

- 진입 신호는 아니지만
- 구조적으로는 계속 봐야 하고
- 차트에는 `WAIT + repeated checks`로 남겨야 한다.

## 4. 실제 문제였던 것

이 family는 build 단계에서 이미 `display_ready = True`, `stage = OBSERVE`까지는 살아 있었다.

하지만 두 가지가 비어 있었다.

1. `chart_event_kind_hint / chart_display_mode / chart_display_reason`
2. repeated runtime row에서의 late cadence keep

즉 target family는
`보여줄지 말지`
문제라기보다
`보여주되 WAIT contract로 보여주지 못하고 있었던 문제`
에 가까웠다.

## 5. 목표 contract

이번 하위축의 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = middle_sr_anchor_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_middle_anchor_guard_wait_as_wait_checks`

즉 hidden suppression이 아니라
`guarded structural wait surface`
로 올리는 것이 목적이다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
   `xau_middle_anchor_guard_wait_as_wait_checks`를 추가한다
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
   이 family가 `blocked_display_reason = middle_sr_anchor_guard`를 carry하도록 맞춘다
3. repeated row가 `xau_middle_anchor_cadence_suppressed`로 다시 죽지 않도록
   resolve 예외를 추가한다
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
   accepted wait-check reason을 추가한다

## 7. 이번 축에서 하지 않는 것

- XAU no-probe family 전체를 한 번에 숨김/표시 재분류
- XAU outer-band energy-soft-block 축 처리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. current-build replay에서 target family가 `WAIT + wait_check_repeat`로 보인다
2. repeated resolve에서도 cadence suppression으로 다시 숨지지 않는다
3. PA0 queue에서 target family가 줄거나 사라진다
4. fresh exact row가 아직 없으면 그 사실을 memo에 분리해 기록한다
