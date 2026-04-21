# Product Acceptance PA0 Refreeze After XAU Outer-Band Probe Guard Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 비교 기준

- before baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T14:06:54` 기준 해석
- after baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T14:21:26` 기준 해석

## target family

`XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

## delta

- `must_show_missing: 4 -> 2`
- `must_block_candidate: 2 -> 2`

## 해석

- current build replay는 이미 `WAIT + probe_guard_wait_as_wait_checks`로 해결됐다.
- post-restart fresh exact row는 아직 다시 안 떠서 `must_block`은 그대로 남아 있다.
- `must_show`가 `4 -> 2`로 줄어든 것은 recent window turnover가 진행된 결과로 본다.
