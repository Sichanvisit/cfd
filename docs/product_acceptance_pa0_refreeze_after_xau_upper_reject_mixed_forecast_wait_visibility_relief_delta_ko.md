# Product Acceptance PA0 Refreeze After XAU Upper-Reject Mixed Forecast Wait Visibility Relief Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_000637.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_000637.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T23:50:08`

after generated_at:

- `2026-04-01T00:06:37`

## 2. target family

- `symbol = XAUUSD`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`

## 3. delta

- `must_show 6 -> 0`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

## 4. 해석

이번 delta의 핵심은 아래다.

1. mixed forecast family는 current build에서 wait relief로 바뀌었다.
2. live fresh exact row는 직접 재발하지 않았지만, recent window turnover 이후 target backlog는 `0`이 됐다.
3. 즉 이 하위축은 PA0 기준선에서는 닫힌 상태로 봐도 된다.

## 5. 현재 must-show 교체 상태

latest must-show는 아래 family로 교체됐다.

- `6 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
- `8 = BTCUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
- `1 = NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait +`
