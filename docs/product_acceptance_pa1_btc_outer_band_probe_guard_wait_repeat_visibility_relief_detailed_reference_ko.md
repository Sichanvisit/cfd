# Product Acceptance PA1 BTC Outer-Band Probe Guard Wait Repeat Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 왜 다시 열었는지와,
이번 축의 문제가 `build contract 부재`가 아니라
`resolve cadence suppression`이었다는 점을 고정하는 상세 reference다.

관련 문서:

- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

## 2. 문제 family

target family는 아래 structural wait row다.

- `symbol = BTCUSD`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`

이번 구현 직전 baseline에서 이 family는

- `must_show_missing = 5`
- `must_block_candidate = 2`

를 차지하고 있었다.

## 3. 실제 문제였던 것

이번 축의 핵심은 build-time contract는 이미 맞았다는 점이다.

representative replay 기준으로
[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
의 `build_consumer_check_state_v1(...)`는 target family를 이미 아래처럼 만든다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

즉 `기다림 + 체크 반복` contract 자체는 build 단계에서 이미 살아 있었다.

문제는 그 다음 late/runtime 해석 단계였다.

## 4. 어디서 다시 꺼졌는가

`resolve_effective_consumer_check_state_v1(...)` 안의
`btc_lower_structural_cadence_suppressed`
가 반복 structural wait row를 다시 hidden으로 내리고 있었다.

representative replay 기준 old behavior:

- build state:
  - `display_ready = True`
  - `chart_display_reason = probe_guard_wait_as_wait_checks`
- resolve state:
  - `display_ready = False`
  - `blocked_display_reason = btc_lower_structural_cadence_suppressed`
  - `chart_event_kind_hint / chart_display_mode / chart_display_reason = ""`

즉 문제는
`WAIT contract가 없어서`가 아니라
`있던 WAIT contract를 cadence suppression이 late path에서 지워버린 것`이었다.

## 5. 목표 contract

이번 축의 목표는 새 display reason을 더 만드는 것이 아니다.

목표는 아래와 같다.

1. target family는 계속 `probe_guard_wait_as_wait_checks`를 쓴다
2. repeated row라도 `btc_lower_structural_cadence_suppressed`로 다시 숨기지 않는다
3. 차트에는 계속 `WAIT + repeated checks`로 남긴다
4. PA0 freeze는 이 row를 accepted wait-check relief로 보고 queue에서 제외한다

## 6. 구현 방향

1. `resolve_effective_consumer_check_state_v1(...)`에
   `btc_outer_band_probe_guard_wait_repeat_relief`를 추가한다
2. 이 relief는 아래 조건일 때만 켠다
   - `BTCUSD`
   - `BUY`
   - `OBSERVE`
   - `display_ready = True`
   - `outer_band_reversal_support_required_observe`
   - `outer_band_guard`
   - `probe_not_promoted`
   - `btc_lower_buy_conservative_probe`
   - `chart_display_reason = probe_guard_wait_as_wait_checks`
3. 위 relief가 켜진 row는 `btc_lower_structural_cadence_suppressed`에서 제외한다
4. painter와 PA0는 기존 generic `probe_guard_wait_as_wait_checks` 흐름을 그대로 사용한다

## 7. 이번 축에서 하지 않는 것

- 새 chart display reason 추가
- 새 symbol-specific painter branch 추가
- no-probe hidden wait 축 조정
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. repeated BTC outer-band row가 resolve 단계 이후에도 `WAIT + wait_check_repeat`로 남는다
2. `blocked_display_reason`는 cadence suppression이 아니라 `outer_band_guard`로 유지된다
3. PA0 refreeze에서 target family가 queue에서 줄거나 사라진다
4. total count가 그대로여도 replacement family가 무엇인지 설명할 수 있다
