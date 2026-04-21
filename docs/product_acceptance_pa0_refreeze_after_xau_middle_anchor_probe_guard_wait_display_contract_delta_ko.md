# Product Acceptance PA0 Refreeze After XAU Middle-Anchor Probe Guard Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline: `2026-04-01T15:21:43`
- after baseline: `2026-04-01T15:33:45`

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_153345.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_153345.json)

after latest:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

## target family

- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe`

## delta

- `must_show: 4 -> 4`
- `must_block: 4 -> 4`

baseline summary:

- `must_show_missing_count: 15 -> 15`
- `must_hide_leakage_count: 0 -> 0`
- `must_block_candidate_count: 12 -> 12`

## 해석

- current-build replay에서는 target family가 이미 `probe_guard_wait_as_wait_checks`로 정상 resolve된다.
- 그런데 after baseline 시점까지도 exact fresh runtime row가 다시 나오지 않아, recent window에는 old blank row가 그대로 남아 있다.
- 그래서 이번 delta는 `0`으로 줄지 않았고 `4 -> 4`로 유지됐다.

즉 이번 delta는 구현 부족이 아니라 `fresh recurrence 부재`를 뜻한다.

## current top residue

after baseline 기준 top residue:

- `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + xau_second_support_buy_probe` `must_show 4 / must_block 4`
- `XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait` `must_show 5 / must_block 2`
- `BTCUSD + upper_break_fail_confirm + clustered_entry_price_zone` `must_show 6`
- `BTCUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked` `must_block 4`
