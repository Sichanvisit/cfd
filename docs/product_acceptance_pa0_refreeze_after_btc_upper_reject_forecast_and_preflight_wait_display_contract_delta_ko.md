# Product Acceptance PA0 Refreeze After BTC Upper-Reject Forecast And Preflight Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_125657.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_125657.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T12:56:57`

after generated_at:

- `2026-04-01T13:20:21`

## 2. 대상 family

### confirm forecast

- `BTCUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`

### probe preflight

- `BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`

## 3. delta

### confirm forecast

- `must_show 0 -> 0`
- `must_hide 9 -> 9`
- `must_block 0 -> 0`

### probe preflight

- `must_show 0 -> 0`
- `must_hide 0 -> 0`
- `must_block 10 -> 10`

## 4. 해석

이번 delta가 그대로인 이유는 명확하다.

1. current build replay에서는 두 family 모두 새 WAIT contract로 정상 전환된다.
2. 하지만 PA0 baseline은 fresh runtime row에 기록된 embedded contract를 본다.
3. 이번 턴에는 live runtime이 `MT5 connection unavailable` 상태라 fresh row가 쌓이지 않았다.
4. 따라서 queue는 아직 old embedded row 기준으로 남아 있다.

즉 이 결과는 구현 실패가 아니라 `live recurrence pending` 상태를 뜻한다.

## 5. 다음 확인 포인트

다음 live row가 다시 쌓이면 아래를 확인하면 된다.

1. `BTC upper_reject_confirm + forecast_guard + observe_state_wait`가 `btc_upper_reject_confirm_forecast_wait_as_wait_checks`로 찍히는지
2. `BTC upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`가 `btc_upper_reject_probe_preflight_wait_as_wait_checks`로 찍히는지
3. 그 다음 PA0 refreeze에서 `must_hide 9 -> 0`, `must_block 10 -> 0`이 되는지
