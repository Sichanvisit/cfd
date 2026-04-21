# Product Acceptance PA1 XAU Lower Probe Guard Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 목적

`XAUUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + xau_second_support_buy_probe`
family를 directional leakage가 아니라 `WAIT + wait_check_repeat` contract로 분리한다.

## 문제 family

target family 조건:

- `symbol = XAUUSD`
- `observe_reason = lower_rebound_probe_observe`
- `blocked_by in {forecast_guard, barrier_guard}`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_second_support_buy_probe`

actual fresh row에서는 `check_display_ready = True`, `check_stage = PROBE`인데
`chart_display_reason`가 비어 있어서 PA0에서 `must_hide` leakage로 계속 잡히고 있었다.

## 목표 contract

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = forecast_guard` 또는 `barrier_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_lower_probe_guard_wait_as_wait_checks`

## 구현 방향

1. policy에 XAU lower probe guard wait contract를 추가한다.
2. PA0 accepted wait reason 목록에 새 reason을 올린다.
3. build / resolve / painter / PA0 skip 테스트를 같이 고정한다.

## 완료 기준

1. representative fresh row replay가 새 reason으로 보인다.
2. 회귀 테스트가 통과한다.
3. fresh exact row가 새 reason으로 기록되면 PA0 `must_hide`가 줄기 시작한다.
