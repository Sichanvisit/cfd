# Product Acceptance PA1 XAU Middle Anchor Probe Energy Soft Block Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 문서 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + middle_sr_anchor_required_observe + energy_soft_block + execution_soft_blocked + xau_second_support_buy_probe`
family를 어떤 chart contract로 봐야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 현재 문제 family

최신 baseline 기준 must-show / must-block main axis는 아래 family다.

- `symbol = XAUUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_second_support_buy_probe`

직전 PA0 latest에서 이 family는 다음 비중을 차지했다.

- `must_show_missing 11/15`
- `must_block_candidates 3/12`

즉 recent queue 기준으로 XAU lower-side blocked scene이 차트 acceptance의 새 메인축으로 올라온 상태다.

## 3. 왜 wait-style relief인가

이 family는 no-probe hidden suppression 축이 아니다.

- probe scene이 이미 있다
- importance source가 `xau_second_support_reclaim`으로 살아 있다
- blocked 이유가 `energy_soft_block`이다
- 구조적으로는 계속 체크해야 하는 XAU lower-side probe wait scene이다

즉 의미는 아래와 같다.

```text
아직 진입은 아니지만,
second support reclaim 구조를 계속 체크해야 하는 blocked wait scene
```

그래서 이 family를 숨긴 blocked scene으로 두면
must-show / must-block backlog가 계속 남고
chart에는 “기다림 + 체크” 성격이 반영되지 않는다.

## 4. 목표 contract

이 family의 목표 chart contract는 아래와 같다.

- directional BUY marker로 과장하지 않는다
- `WAIT + wait_check_repeat`로 surface에 올린다
- blocked reason은 `energy_soft_block`로 남긴다
- PA0에서는 accepted wait relief로 분류한다

대표 current-build replay 기대값:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `display_score ~= 0.75 ~ 0.82`
- `display_repeat_count >= 1`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_middle_anchor_probe_energy_soft_block_as_wait_checks`

## 5. 구현 방향

이번 하위축 구현 방향은 아래와 같다.

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 XAU middle-anchor probe wait relief policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `xau_middle_anchor_probe_energy_wait_relief` family match를 추가한다.
3. relief 적용 시 `blocked_display_reason = energy_soft_block`를 carry한다.
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason을 추가한다.
5. consumer state / chart painter / PA0 skip 테스트를 묶어 고정한다.
6. live restart 후 exact target recurrence를 보고, 없다면 representative row replay와 refreeze delta를 같이 기록한다.

## 6. 이번 하위축에서 하지 않는 것

이번 문서 범위 밖은 아래와 같다.

- BTC structural energy-soft-block 재검증 전체
- BTC lower rebound no-probe leakage 정리
- NAS upper-reject probe leakage 정리
- broad threshold retune

## 7. 완료 기준

이번 하위축 완료 기준은 아래와 같다.

1. representative XAU row replay에서 `WAIT + wait_check_repeat`가 실제로 나온다.
2. PA0 script가 이 reason을 accepted wait relief로 skip한다.
3. exact family가 post-restart fresh row에 안 나올 경우 그 부재와 queue 미감소 원인을 분리해 기록한다.

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 reopen point는 둘 중 하나다.

1. exact XAU middle-anchor energy-soft-block family recurrence 재확인
2. current must-hide main family를 다음 PA1 축으로 진행
