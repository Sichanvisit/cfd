# Product Acceptance PA1 XAU Upper-Reject Mixed Forecast Wait Visibility Relief Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
family를 hidden wait에서 `WAIT + repeated checks` surface로 올리는 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md)

## 2. 문제 family

- `symbol = XAUUSD`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`

직전 PA0 latest에서는 이 family가 `must_show_missing = 6`을 채우고 있었다.

## 3. 해석

이 축의 질문은 간단하다.

```text
mixed confirm 구조는 맞는데 forecast가 아직 부족한 wait 상태를
차트에서 숨길 것인가, WAIT 체크 표기로 남길 것인가?
```

이번 축의 결론은 `WAIT 체크 표기로 남긴다`다.

이유:

- 같은 family의 `barrier_guard` 변형은 이미 `xau_upper_reject_mixed_guard_wait_as_wait_checks`로 다루고 있다.
- `mixed_confirm`는 완전한 confirm보다 덜 강하지만, hidden leakage로 보기에는 구조 정보가 충분하다.
- `forecast_guard`는 promote 보류 조건이지, 구조 삭제 조건은 아니다.

즉 `barrier_guard 전용 예외`였던 mixed wait contract를 `forecast_guard`까지 넓히는 것이 자연스럽다.

## 4. 구현 전 상태

representative replay 기준으로 target row는 아래처럼 숨겨져 있었다.

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `blocked_display_reason = xau_upper_reject_guard_wait_hidden`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

resolve 단계에서도 같은 hidden 상태가 유지됐다.

## 5. 목표 contract

이번 축의 목표는 아래다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_mixed_guard_wait_as_wait_checks`

즉 새 reason을 만드는 것이 아니라, 기존 mixed guard wait contract의 적용 범위를 forecast guard까지 확장한다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에서 `xau_upper_reject_mixed_guard_wait_as_wait_checks`의 `blocked_by_allow`를 `barrier_guard + forecast_guard`로 넓힌다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 `xau_upper_reject_mixed_guard_wait_relief`를 같은 범위로 넓힌다.
3. build path에서 `blocked_display_reason` carry를 추가한다.
4. resolve path의 `xau_upper_reject_late_hidden` / `xau_upper_reject_cadence_suppressed`가 이 contract를 다시 죽이지 않게 repeat relief 예외를 추가한다.

## 7. 완료 기준

1. build replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. PA0 baseline이 이 reason을 must-show queue에서 제외할 수 있다.
4. live fresh exact row가 없더라도 delta 문서에 turnover 결과를 분리 기록한다.
