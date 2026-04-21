# Product Acceptance PA0 Refreeze After BTC Upper-Sell Forecast Preflight Wait Follow-Up Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_132021.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_132021.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T13:20:21`

after generated_at:

- `2026-04-01T13:32:53`

## 2. 대상 family

- `BTCUSD + upper_break_fail_confirm + forecast_guard + observe_state_wait +`
- `BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`
- `BTCUSD + upper_reject_confirm + preflight_action_blocked + preflight_blocked +`

참고 residue:

- `BTCUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
- `BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`

## 3. delta

### 신규 3개 family

- break-fail forecast: `must_hide 4 -> 4`
- probe forecast: `must_hide 2 -> 2`
- confirm preflight: `must_block 2 -> 2`

### 기존 참고 family

- confirm forecast: `must_hide 9 -> 9`
- probe preflight: `must_block 10 -> 10`

## 4. 해석

이번 delta도 그대로인 이유는 이전 BTC upper follow-up과 같다.

1. representative replay 기준 current build는 5개 family 모두 WAIT contract가 정상이다.
2. PA0 baseline은 fresh runtime row에 저장된 embedded contract를 본다.
3. 현재 runtime는 [cfd_main_restart_20260401_132056.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_132056.err.log) 기준 `MT5 connection unavailable` 상태다.
4. fresh row가 없으므로 queue는 old embedded row 기준으로 그대로 남아 있다.

즉 이번 결과도 구현 실패가 아니라 `live recurrence pending` 상태다.
