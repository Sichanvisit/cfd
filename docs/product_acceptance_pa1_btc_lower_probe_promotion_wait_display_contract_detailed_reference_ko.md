# Product Acceptance PA1 BTC Lower Probe Promotion Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 문서 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 어떤 chart contract로 연결해야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 현재 문제 family

대상 family는 아래 조건이 동시에 붙는 BTC lower probe promotion wait scene이다.

- `symbol = BTCUSD`
- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = probe_promotion_gate`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`

직전 latest baseline에서는 이 family가 must-hide leakage main axis였다.

- `must_hide_leakage 10/15`

중요한 점은 이 family가 hidden scene이 아니라는 것이다.

- `display_ready = True`
- `check_stage = PROBE`
- `display_score ~= 0.91`
- `display_repeat_count = 3`

즉 차트에는 이미 보이는데, accepted wait contract가 비어 있어서 leakage로 잡히던 상태였다.

## 3. 왜 hide가 아니라 wait-display contract인가

이 family는 no-probe leakage도 아니고 hard hide 대상도 아니다.

- probe scene이 이미 붙어 있다
- importance source가 `btc_lower_recovery_start`로 높다
- entry는 아니지만 lower probe를 계속 체크해야 하는 초기 구조다
- 실제 stage도 `PROBE`로 올라가 있다

정리하면 의미는 아래와 같다.

```text
아직 진입은 아니지만,
probe promotion을 기다리며 계속 체크해야 하는 BTC lower-side probe wait scene
```

그래서 이 family는 숨길 것이 아니라
`WAIT + repeated checks`로 차트 계약을 명시해야 한다.

## 4. 목표 contract

대상 family의 목표 chart contract는 아래와 같다.

- directional BUY probe를 그대로 밀지 않는다
- `WAIT + wait_check_repeat`로 neutral wait surface로 내린다
- blocked reason은 `probe_promotion_gate`로 남긴다
- PA0에서는 accepted wait relief로 분류한다

대표 current-build replay 기대값:

- `check_display_ready = True`
- `check_stage = PROBE`
- `display_score ~= 0.91`
- `display_repeat_count = 3`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_probe_promotion_wait_as_wait_checks`

## 5. 구현 방향

이번 하위축 구현 방향은 아래와 같다.

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 BTC lower probe promotion wait relief policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 해당 family match와 blocked reason carry를 추가한다.
3. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason을 추가한다.
4. consumer state / effective state / chart painter / PA0 skip 테스트를 묶어 고정한다.
5. live restart와 PA0 refreeze로 queue에서 실제로 빠지는지 확인한다.

## 6. 이번 하위축에서 하지 않는 것

이번 문서 범위 밖은 아래와 같다.

- BTC structural energy-soft-block backlog 정리 전체
- XAU middle-anchor energy-soft-block backlog 정리 전체
- NAS upper-reject no-probe / probe leakage 정리
- broad threshold retune

## 7. 완료 기준

이번 하위축의 완료 기준은 아래와 같다.

1. representative row replay가 실제로 `WAIT + wait_check_repeat`로 나온다.
2. PA0 script가 이 reason을 accepted wait relief로 skip한다.
3. latest refreeze에서 target must-hide leakage가 queue에서 `0`으로 빠진다.

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 reopen point는 NAS upper-reject must-hide family다.
