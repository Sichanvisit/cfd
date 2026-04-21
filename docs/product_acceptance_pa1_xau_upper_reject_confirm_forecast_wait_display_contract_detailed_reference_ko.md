# Product Acceptance PA1 XAU Upper-Reject Confirm Forecast Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
family를 hidden wait에서 `WAIT + wait_check_repeat` surface로 올린 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)

## 2. 문제 family

- `symbol = XAUUSD`
- `observe_reason = upper_reject_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`

직전 PA0 latest 기준으로 이 family가 `must_show_missing = 9`를 채우고 있었다.

## 3. 해석

이번 축의 질문은 간단하다.

```text
upper_reject_confirm 구조가 이미 잡혀 있는데
forecast가 아직 부족해서 기다리는 상태를
차트에서 숨길 것인가, WAIT 체크 표기로 보여줄 것인가?
```

이번 축의 결론은 `WAIT 체크 표기로 보여준다`이다.

이유:

- 같은 XAU upper-reject 계열에서 `mixed_confirm + forecast_guard`는 이미 WAIT contract로 정리되어 있다.
- 이 family는 `barrier_guard`가 아니라 `forecast_guard`라서 구조 자체가 틀린 것이 아니라, 타이밍 보강이 덜 된 상태에 가깝다.
- 따라서 confirm forecast wait를 hidden leakage로 남기기보다, guard가 걸린 WAIT surface로 올리는 편이 PA1 chart acceptance 목적에 맞다.

## 4. 구현 전 상태

representative row `2026-04-01T01:43:59`를 current build 이전 기준으로 replay하면:

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `blocked_display_reason = xau_upper_reject_guard_wait_hidden`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

반면 `upper_reject_mixed_confirm + forecast_guard` representative row `2026-04-01T01:43:29`는 이미 WAIT contract로 살아 있었다.

즉 이번 턴의 실제 구현 대상은 `confirm forecast wait` 하나였다.

## 5. 목표 contract

이번 축의 목표는 아래와 같다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_confirm_forecast_wait_as_wait_checks`

단, `barrier_guard + observe_state_wait`는 여전히 hidden으로 남겨서 범위를 좁게 유지한다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에 `xau_upper_reject_confirm_forecast_wait_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) build path에서 `xau_upper_reject_confirm_forecast_wait_relief`를 추가한다.
3. `xau_upper_reject_guard_wait_hidden`가 forecast confirm wait를 다시 숨기지 않도록 narrow exemption을 넣는다.
4. resolve path에서 `xau_upper_reject_late_hidden` / `xau_upper_reject_cadence_suppressed`가 이 contract를 다시 죽이지 않도록 repeat relief를 추가한다.
5. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait reason을 추가한다.

## 7. 완료 기준

1. representative confirm forecast row replay에서 build/resolve 모두 `WAIT + wait_check_repeat`로 보인다.
2. mixed forecast row가 기존 contract를 그대로 유지한다.
3. PA0 baseline이 새 reason을 must-show queue에서 accepted wait로 제외한다.
4. live fresh row가 없어도 turnover refreeze 결과를 별도로 기록한다.
