# Product Acceptance PA1 XAU Outer-Band Probe Energy Soft-Block Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
family를 `hidden blocked scene`에서 `WAIT + repeated checks` contract로 올린 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

직전 latest PA0 기준 main residue는 아래 family였다.

- `symbol = XAUUSD`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_upper_sell_probe`

직전 baseline에서 이 family는:

- `must_show_missing = 15`
- `must_block_candidates = 12`

를 사실상 대부분 채우고 있었다.

## 3. 이 family를 어떻게 해석할 것인가

이번 축의 질문은 단순하다.

```text
XAU outer-band probe가 이미 잡혀 있는데
energy soft block 때문에 실행만 막힌 상태를
차트에서 계속 숨길 것인가, WAIT로 살릴 것인가?
```

이번 축의 답은 `WAIT로 살린다` 쪽이다.

이 family는:

- 아직 entry/execute로 승격되면 안 되지만
- probe scene 자체는 이미 존재하고
- soft block 이유도 execution gate 쪽으로 명확하고
- 차트에서는 "계속 보는 wait probe"로 남겨두는 편이 맞다.

즉 leakage가 아니라 `probe-ready but temporarily blocked wait surface`로 본다.

## 4. 실제 문제는 무엇이었나

representative current-build replay 이전 상태에서는:

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

즉 row 자체가 chart acceptance surface에 올라오지 못했다.

이 문제는 repeated cadence suppress 문제가 아니라,
애초에 build 단계에서 숨겨진 blocked scene으로 굳어지는 쪽에 가까웠다.

## 5. 목표 contract

이번 하위축에서 고정한 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = PROBE or BLOCKED`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_outer_band_probe_energy_soft_block_as_wait_checks`

핵심은:

- direction push가 아니라
- `WAIT + repeated checks`
- 그리고 blocked energy context는 그대로 carry

다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
   `xau_outer_band_probe_energy_soft_block_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
   이 family를 `probe_ready_but_blocked` blanket hide 예외로 뺀다.
3. same file에서 resolve surface가 `blocked_display_reason`를 carry할 수 있게 한다.
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
   accepted wait-check reason으로 등록한다.

## 7. 이번 축에서 하지 않는 것

- XAU no-probe confirm family 전체 정리
- XAU mixed confirm leakage 정리
- BTC upper sell backlog 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative current-build replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. PA0 queue에서 target family가 `must_show / must_block` main residue에서 빠진다.
4. fresh exact row가 없으면 memo와 delta에 그 사실을 분리 기록한다.
