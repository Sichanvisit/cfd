# Product Acceptance PA1 XAU Upper-Reject Probe Forecast Wait Display Contract Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`
family를 `hidden leakage`가 아니라 `WAIT + repeated checks` contract로 올리는 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

이번 축의 residue는 아래 family다.

- `symbol = XAUUSD`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = forecast_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_upper_sell_probe`

직전 PA0 latest 기준으로는 이 family가 `must_show_missing = 5`를 채우고 있었다.

## 3. 해석

이 family의 핵심 질문은 아래다.

```text
상방 reject probe 구조는 보였지만 forecast가 아직 부족해서 promote되지 않은 상태를
차트에서 숨길 것인가, WAIT 체크 표기로 남길 것인가?
```

이번 축의 해석은 `WAIT 체크 표기로 남긴다` 쪽이다.

이유:

- `probe_scene`가 이미 붙어 있다.
- `probe_not_promoted`는 진입 거절이라기보다 추가 확인 대기 성격이 강하다.
- `forecast_guard`는 지금 당장 진입만 막는 guard이지, 구조 자체를 지워야 하는 이유는 아니다.

즉 이 family는 leakage보다 `forecast wait probe surface`로 보는 쪽이 맞다.

## 4. 구현 전 상태

representative replay 기준으로 target row는 이미 build 단계에서 아래처럼 살아 있었다.

- `check_candidate = True`
- `check_display_ready = True`
- `check_stage = PROBE`
- `display_strength_level = 6`
- `display_repeat_count = 2`

하지만 아래 항목이 비어 있었다.

- `blocked_display_reason`
- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

그리고 resolve 단계에서는 repeated cadence suppression에 다시 눌릴 수 있는 상태였다.

## 5. 목표 contract

이번 축에서 고정하는 목표 contract는 아래다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_forecast_wait_as_wait_checks`

즉 `forecast 부족으로 아직 promote 안 된 SELL probe`를
`WAIT + repeated checks` surface로 올리는 것이 목표다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `xau_upper_reject_probe_forecast_wait_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `xau_upper_reject_probe_forecast_wait_relief`를 추가한다.
3. same file에서 `blocked_display_reason = forecast_guard` carry를 보장한다.
4. resolve 단계에서 `xau_upper_reject_cadence_suppressed`가 이 contract를 다시 지우지 않게 repeat relief 예외를 둔다.
5. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait-check reason으로 등록한다.

## 7. 이번 축에서 하지 않는 것

- XAU mixed confirm guard-wait residue 정리
- BTC upper sell must-show/must-hide residue 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. PA0 baseline script가 이 reason을 problem seed queue에서 제외한다.
4. live exact row가 아직 없으면 memo/delta에 `replay 완료 + live recurrence pending` 상태를 분리 기록한다.
