# Product Acceptance PA1 BTC Upper-Sell Forecast Preflight Wait Follow-Up Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 직전 BTC upper-reject follow-up 이후 남아 있던 mirror residue 3개를 한 번에 정리한다.

- `BTCUSD + upper_break_fail_confirm + forecast_guard + observe_state_wait +`
- `BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`
- `BTCUSD + upper_reject_confirm + preflight_action_blocked + preflight_blocked +`

핵심은 세 family 모두 `current build에서는 보이게 올릴 수 있는데 accepted WAIT contract가 비어 있다`는 점이다.

## 2. 문제 family

### 2-1. Break-fail forecast wait

- `must_hide = 4`
- `observe_reason = upper_break_fail_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`

### 2-2. Probe forecast wait

- `must_hide = 2`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = forecast_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_upper_sell_probe`

### 2-3. Confirm preflight blocked

- `must_block = 2`
- `observe_reason = upper_reject_confirm`
- `blocked_by = preflight_action_blocked`
- `action_none_reason = preflight_blocked`

## 3. 구현 전 상태

representative replay 기준으로 세 family 모두 방향성/구조 정보는 이미 충분했지만 chart wait reason이 비어 있었다.

### break-fail forecast

- `display_ready = True`
- `stage = OBSERVE`
- `blocked_display_reason = ""` on build, `forecast_guard` on resolve
- chart wait reason blank

### probe forecast

- `display_ready = True`
- `stage = PROBE`
- `blocked_display_reason = ""` on build, `forecast_guard` on resolve
- chart wait reason blank

### confirm preflight

- `display_ready = False`
- `stage = BLOCKED`
- `blocked_display_reason = preflight_action_blocked`
- chart wait reason blank

## 4. 목표 contract

### break-fail forecast

- `WAIT + wait_check_repeat + btc_upper_break_fail_confirm_forecast_wait_as_wait_checks`

### probe forecast

- `WAIT + wait_check_repeat + btc_upper_reject_probe_forecast_wait_as_wait_checks`

### confirm preflight

- `WAIT + wait_check_repeat + btc_upper_reject_confirm_preflight_wait_as_wait_checks`
- stage는 `BLOCKED` 유지

## 5. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 3개 reason을 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서 forecast carry를 추가한다.
3. confirm preflight는 display를 복구하되 `BLOCKED` stage는 유지한다.
4. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait reason을 추가한다.

## 6. 완료 기준

1. representative replay에서 세 family 모두 build/resolve 기준으로 wait contract가 채워진다.
2. 회귀 테스트가 통과한다.
3. live MT5 unavailable로 fresh row가 없어도 delta 문서에 pending 상태를 남긴다.
