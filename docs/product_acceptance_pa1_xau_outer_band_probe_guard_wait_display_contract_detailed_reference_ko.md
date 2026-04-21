# Product Acceptance PA1 XAU Outer-Band Probe Guard Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 목적

`XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
family 안에서 `probe_against_default_side` 때문에 hidden으로 떨어지던 row를
`WAIT + wait_check_repeat` contract로 다시 올리는 기준을 고정한다.

## 문제 family

target family 조건:

- `symbol = XAUUSD`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_upper_sell_probe`
- `entry_probe_plan_v1.reason = probe_against_default_side`

구현 전 actual row는 `probe_against_default_side`가 `display_blocked`로 먼저 잡히면서
`check_display_ready = False`, `chart_display_reason = ""` 상태로 남았다.

## 목표 contract

이 family는 leak가 아니라 structural wait row로 본다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = outer_band_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

## 구현 방향

1. `consumer_check_state.py`에 XAU mirror relief를 추가한다.
2. `probe_against_default_side`가 structural wait를 막지 않도록 display-block 예외를 연결한다.
3. generic `probe_guard_wait_as_wait_checks` contract를 그대로 재사용한다.
4. PA0는 generic accepted wait reason으로 queue에서 제외한다.

## 완료 기준

1. representative row replay가 `WAIT + probe_guard_wait_as_wait_checks`로 보인다.
2. 회귀 테스트가 통과한다.
3. fresh exact row가 다시 오면 PA0 `must_show/must_block`가 줄기 시작한다.
