# Product Acceptance PA1 BTC Upper-Reject Forecast And Preflight Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 BTC 상단 sell 계열의 두 residue를 한 번에 정리한다.

- `BTCUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
- `BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`

둘 다 PA0 latest에서 상단 sell chart acceptance residue로 남아 있었고, 이번 턴에서는 이를 `WAIT + wait_check_repeat` chart contract로 올리는 것이 목적이다.

## 2. 문제 family

### 2-1. Confirm forecast wait

- `symbol = BTCUSD`
- `observe_reason = upper_reject_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`

직전 PA0 latest에서 `must_hide_leakage = 9`를 채우고 있었다.

### 2-2. Probe preflight blocked

- `symbol = BTCUSD`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = preflight_action_blocked`
- `action_none_reason = preflight_blocked`
- `probe_scene_id = btc_upper_sell_probe`

직전 PA0 latest에서 `must_block_candidates = 10`을 채우고 있었다.

## 3. 해석

이번 축의 핵심은 둘을 같은 방식으로 보지 않는 것이다.

### 3-1. Confirm forecast wait

이 family는 이미 current build에서 `display_ready = True`로 보이지만, accepted WAIT contract가 없어서 leakage로 남아 있었다.

즉 실제 문제는:

```text
보이면 안 되는가?
```

가 아니라

```text
보이는 것을 WAIT contract로 명시하지 못하고 있는가?
```

에 가깝다.

따라서 해법은 hidden suppression이 아니라 `WAIT + wait_check_repeat` contract 추가다.

### 3-2. Probe preflight blocked

이 family는 `preflight_action_blocked` 때문에 `BLOCKED + hidden`으로 남아 있었다.

하지만 `probe_scene_id = btc_upper_sell_probe`가 있고, 구조적으로는 계속 추적해야 하는 blocked probe이다.
따라서 stage는 `BLOCKED`로 유지하되, chart surface는 `WAIT + repeated checks`로 복구하는 것이 맞다.

## 4. 구현 전 상태

### 4-1. Confirm forecast representative row

representative row `2026-04-01T01:41:06` current-build replay 전 기준:

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = ""` on build, `forecast_guard` on resolve
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

즉 방향성 surface는 살아 있었지만 accepted wait reason이 없었다.

### 4-2. Probe preflight representative row

representative row `2026-04-01T01:49:24` current-build replay 전 기준:

- `check_display_ready = False`
- `check_stage = BLOCKED`
- `blocked_display_reason = preflight_action_blocked`
- `chart_event_kind_hint / chart_display_mode / chart_display_reason = blank`

즉 blocked probe가 차트에는 안 보이는 상태였다.

## 5. 목표 contract

### 5-1. Confirm forecast

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_reject_confirm_forecast_wait_as_wait_checks`

### 5-2. Probe preflight

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = preflight_action_blocked`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_upper_reject_probe_preflight_wait_as_wait_checks`

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 두 family 전용 wait contract를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 confirm forecast carry를 추가한다.
3. 같은 파일에서 probe preflight blocked row는 stage `BLOCKED`를 유지한 채 display를 복구한다.
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 두 reason을 accepted wait 목록으로 추가한다.

## 7. 완료 기준

1. representative replay에서 confirm forecast와 probe preflight 둘 다 build/resolve 기준으로 `WAIT + wait_check_repeat`가 보인다.
2. 회귀 테스트가 통과한다.
3. live가 멈춰 있어 PA0 delta가 안 줄어도, 그 상태와 이유를 별도 delta 문서에 기록한다.
