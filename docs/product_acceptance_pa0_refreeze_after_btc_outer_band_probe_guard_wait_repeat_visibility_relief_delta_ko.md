# Product Acceptance PA0 Refreeze After BTC Outer-Band Probe Guard Wait Repeat Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_220633.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_220633.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T21:49:05`

after generated_at:

- `2026-03-31T22:10:15`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 0 -> 0`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 1 -> 0`

## 3. target family delta

target:

- `BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`

delta:

- `must_show 5 -> 0`
- `must_block 2 -> 0`

즉 이번 refreeze에서는 target BTC outer-band backlog가 PA0 queue에서 사라졌다.

## 4. live recurrence 메모

post-restart recent watch를 약 90초 진행했지만,
exact target family fresh row는 이번 watch 안에는 다시 나타나지 않았다.

즉 이번 delta는
`fresh exact row 증빙`
보다는
`current build replay + queue turnover`
결과로 확인된 것이다.

## 5. total이 그대로인 이유

이번 refreeze에서 total은 그대로다.

- `must_show = 15`
- `must_block = 12`

다만 composition은 아래처럼 바뀌었다.

after latest:

- `must_show`
  - `12 = XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
  - `1 = BTCUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
  - `1 = BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait +`
- `must_block`
  - `9 = NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
  - `1 = BTCUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
  - `1 = BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait +`

즉 target family는 빠졌지만,
queue의 main axis는 XAU/NAS/BTC의 다른 residue로 이동했다.

## 6. 해석

이번 delta의 의미는 아래와 같다.

1. `BTC outer_band + probe_not_promoted` 축은 더 이상 PA0 main residue가 아니다
2. total count가 유지된 것은 실패가 아니라 replacement family 때문이었다
3. 다음 PA1 메인축은 BTC outer-band 반복축이 아니라 XAU/NAS residue로 이동했다

## 7. 한 줄 요약

```text
BTC outer-band probe_guard repeated wait backlog는 이번 refreeze에서 must_show 5 -> 0, must_block 2 -> 0으로 빠졌고,
PA0의 남은 메인은 XAU middle-anchor wait와 NAS upper-break-fail energy family로 옮겨갔다.
```
