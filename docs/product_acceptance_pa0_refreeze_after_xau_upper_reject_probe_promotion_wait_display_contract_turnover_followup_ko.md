# Product Acceptance PA0 Refreeze After XAU Upper-Reject Probe Promotion Wait Display Contract Turnover Follow-Up

작성일: 2026-04-01 (KST)

## 1. 비교 기준

before:

- [product_acceptance_pa0_baseline_snapshot_20260401_011221.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_011221.json)
- `generated_at = 2026-04-01T01:00:33`

after turnover refreeze:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T01:31:42`

target family:

- `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`

## 2. Turnover Delta

- `must_show 15 -> 1`
- `must_hide 0 -> 0`
- `must_block 5 -> 0`

즉 이전 follow-up에서 `must_show 15 -> 12`였던 same family가 recent window turnover를 거치며 `1`개만 남는 상태까지 더 줄었다.

## 3. Queue 재편

turnover 이후 main queue는 다음처럼 바뀌었다.

- `must_show 6`: `XAUUSD + upper_reject_probe_observe + clustered_entry_price_zone + xau_upper_sell_probe`
- `must_show 3`: `XAUUSD + upper_reject_probe_observe + pyramid_not_progressed + xau_upper_sell_probe`
- `must_show 2`: `XAUUSD + outer_band_reversal_support_required_observe + clustered_entry_price_zone + xau_upper_sell_probe`
- `must_show 2`: `XAUUSD + upper_reject_probe_observe + pyramid_not_in_drawdown + xau_upper_sell_probe`
- `must_show 1`: target promotion wait family 잔존분

## 4. 해석

이번 turnover follow-up으로 아래는 확실해졌다.

1. `xau_upper_reject_probe_promotion_wait_as_wait_checks` 자체는 recent window에서 정상 소화된다.
2. 같은 family의 old hidden backlog는 거의 정리됐다.
3. 이제 XAU main residue는 `promotion wait`보다 `entry gating / clustered_entry_price_zone / pyramid_*` 계열로 넘어갔다.
