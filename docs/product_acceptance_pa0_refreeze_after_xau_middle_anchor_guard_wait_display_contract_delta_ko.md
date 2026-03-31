# Product Acceptance PA0 Refreeze After XAU Middle-Anchor Guard Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_224305.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_224305.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T22:10:15`

after generated_at:

- `2026-03-31T22:47:06`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 0 -> 4`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`

## 3. target family delta

target:

- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`

delta:

- `must_show 12 -> 0`
- `must_block 0 -> 0`

즉 target middle-anchor residue는 latest queue에서 빠졌다.

## 4. fresh runtime 메모

post-restart recent watch에서는 exact target family fresh recurrence가 다시 나오지 않았다.

recent match 4건은 모두 restart 이전 row였다.

- `2026-03-31T22:32:37`
- `2026-03-31T22:32:49`
- `2026-03-31T22:33:03`
- `2026-03-31T22:33:17`

그리고 이 old row들은
`chart_event_kind_hint / chart_display_mode / chart_display_reason`
가 비어 있었다.

즉 이번 delta는
`fresh exact row 증빙`
이 아니라
`current-build replay + queue turnover`
결과를 기록한 것이다.

## 5. replacement queue

after latest main queue는 아래로 이동했다.

- `must_show = 15`
  - `15 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_block = 12`
  - `12 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `must_hide = 4`
  - `2 = BTCUSD + upper_reject_probe_observe +  + probe_not_promoted + btc_upper_sell_probe`
  - `2 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked +`

## 6. 해석

이번 delta의 의미는 아래와 같다.

1. XAU middle-anchor no-probe guard wait는 PA0 main residue에서 벗어났다
2. total count 유지/증가는 구현 실패가 아니라 replacement family 이동 때문이었다
3. 다음 PA1 메인축은 XAU outer-band energy-soft-block으로 이동했다

## 7. 한 줄 요약

```text
XAU middle-anchor guard wait family는 latest PA0에서 must_show 12 -> 0으로 빠졌고,
queue의 메인은 XAU outer-band energy-soft-block family로 이동했다.
```
