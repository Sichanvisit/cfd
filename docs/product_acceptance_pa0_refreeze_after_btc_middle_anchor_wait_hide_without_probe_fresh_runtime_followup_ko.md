# Product Acceptance PA0 Refreeze After BTC Middle-Anchor Wait Hide Without Probe Fresh Runtime Follow-Up

작성일: 2026-04-01 (KST)

## 1. 확인 범위

이번 follow-up은
`BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
family가 fresh live row에서 다시 뜨는지 확인한 뒤,
PA0 refreeze로 `must_hide 12 -> 0`까지 실제로 내려가는지 보는 목적이었다.

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_004631.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_004631.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T00:38:54`

after generated_at:

- `2026-04-01T00:46:32`

## 2. fresh runtime watch 결과

cutoff:

- `2026-04-01T00:38:54`

fresh BTC row:

- `67`

fresh exact target recurrence:

- `0`

watch 구간에서 BTC는 주로 아래 family로 이동했다.

- `btc_midline_sell_watch` `39`
- `conflict_box_lower_bb20_upper_balanced_observe` `15`
- `middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_lower_buy_conservative_probe` `10`

즉 이번 watch에서는 `observe_state_wait + no_probe` exact family 자체가 다시 뜨지 않았다.

## 3. PA0 refreeze 결과

target family delta:

- `must_show 0 -> 0`
- `must_hide 12 -> 0`
- `must_block 0 -> 0`

핵심은 `must_hide 12 -> 0`이 실제로 확인됐다는 점이다.

## 4. 해석

이번 결과는 아래처럼 읽는 것이 맞다.

1. exact fresh target row가 새 hidden reason으로 재발한 건 아니다.
2. 하지만 recent window에서 old sell backlog가 밀려났다.
3. 그 결과 target family는 PA0 queue에서 완전히 사라졌다.

즉 상태를 한 줄로 정리하면:

```text
fresh exact recurrence 없음 + queue turnover로 must_hide 12 -> 0 확인
```

## 5. 현재 queue composition

after latest 기준 main queue는 아래처럼 바뀌었다.

- `must_show_missing`
  - `9 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
  - `3 = XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
  - `2 = XAUUSD + upper_reject_mixed_confirm + pyramid_not_progressed`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

- `must_hide_leakage`
  - `15 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

- `must_block_candidates`
  - `11 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

## 6. 결론

이번 BTC middle-anchor no-probe 축은 이제 queue 기준으로 닫힌 상태로 봐도 된다.

- `must_show = 0`
- `must_hide = 0`
- `must_block = 0`

다음 main residue는 사실상 XAU `upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`다.
