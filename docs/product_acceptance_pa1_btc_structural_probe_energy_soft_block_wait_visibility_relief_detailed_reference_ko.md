# Product Acceptance PA1 BTC Structural Probe Energy Soft Block Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 문서 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
family를 어떻게 해석하고 어떤 chart contract로 연결해야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md)

## 2. 문제 family

대상 family는 아래 조건이 동시에 붙는 BTC structural probe blocked scene이다.

- `symbol = BTCUSD`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = btc_lower_buy_conservative_probe`

직전 PA0 baseline에서는 이 family가 다음 queue를 거의 그대로 채우고 있었다.

- `must_show_missing 13/15`
- `must_block_candidates 12/12`

즉 chart에는 거의 안 보이는데, 실제 구조는 반복적으로 관찰되고 있는 상태였다.

## 3. 왜 hide가 아니라 wait-style relief인가

이 family는 no-probe leakage와 다르다.

- probe scene이 이미 붙어 있다
- importance source가 `btc_structural_rebound`로 살아 있다
- blocked 이유가 hard stop이 아니라 `energy_soft_block`다
- entry는 아직 아니지만 구조적으로 계속 봐야 하는 lower-side structural wait scene이다

정리하면:

```text
아직 들어가면 안 되지만,
probe scene이 살아 있어서 WAIT + repeated checks로 보여줘야 하는 blocked structural scene
```

그래서 이 family를 계속 hidden blocked scene으로 두면
PA0 must-show / must-block queue가 backlog로 남고,
chart acceptance 기준에서도 구조적으로 중요한 BTC lower-side wait surface가 사라진다.

## 4. 목표 contract

이 family의 목표 chart contract는 아래와 같다.

- directional BUY marker로 강하게 밀지 않는다
- `WAIT + wait_check_repeat`로 보인다
- blocked reason은 `energy_soft_block`로 surface에 남긴다
- PA0에서는 accepted wait relief로 분류한다

대표 current-build replay 기대값:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `display_score ~= 0.82`
- `display_repeat_count = 2`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_structural_probe_energy_soft_block_as_wait_checks`

## 5. 구현 방향

이번 하위축의 구현 방향은 아래와 같다.

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 BTC structural probe wait relief policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 `btc_structural_probe_energy_wait_relief` family를 식별한다.
3. relief가 적용될 때 `blocked_display_reason = energy_soft_block`가 carry되게 한다.
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait relief reason으로 추가한다.
5. consumer state / chart painter / PA0 skip 테스트를 동시에 고정한다.
6. live restart 후 fresh row recurrence를 보되, exact family가 바로 안 나와도 representative backlog row replay와 PA0 refreeze delta를 같이 남긴다.

## 6. 이번 하위축에서 하지 않는 것

이번 문서에서 다루지 않는 범위는 아래와 같다.

- BTC no-probe hidden suppression
- NAS probe leakage 정리
- XAU lower-side probe leakage 정리
- entry / wait / hold / exit acceptance 전체 확장
- broad threshold retune

## 7. 완료 기준

이번 하위축의 완료 기준은 아래와 같다.

1. current build replay에서 representative backlog row가 실제로 `WAIT + wait_check_repeat`로 올라간다.
2. PA0 script가 이 reason을 accepted wait relief로 skip한다.
3. exact target family가 재시작 직후 바로 다시 나오지 않더라도, 그 부재와 queue 미감소 원인을 문서에 분리해서 기록한다.

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 reopen point는 두 갈래다.

1. exact BTC structural family가 post-restart runtime에서 실제로 다시 발생하는지 재확인
2. current must-hide 주도 family인 XAU/BTC probe leakage 축 정리
