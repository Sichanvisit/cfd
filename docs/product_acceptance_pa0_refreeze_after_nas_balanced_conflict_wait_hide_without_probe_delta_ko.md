# PA0 Refreeze After NAS Balanced Conflict Hidden Suppression Delta

## 비교 기준

- previous snapshot:
  [product_acceptance_pa0_baseline_snapshot_20260401_181638.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_181638.json)
- latest baseline:
  [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

## delta

- `must_show_missing_count: 2 -> 0`
- `must_hide_leakage_count: 0 -> 0`
- `must_enter_candidate_count: 0 -> 0`
- `must_block_candidate_count: 0 -> 0`

## 해석

- 남아 있던 두 seed는 모두
  `NAS100 + conflict_box_upper_bb20_lower_lower_dominant_observe + observe_state_wait`
  family였다.
- 이번 refreeze에서 해당 family가 accepted hidden suppression으로 빠지면서
  chart acceptance queue가 `0`이 됐다.

## 잔여 queue

- chart 쪽:
  - `must_show=0`
  - `must_hide=0`
  - `must_enter=0`
  - `must_block=0`
- 남은 것은 exit 계열이다.
  - `must_hold=2`
  - `must_release=10`
  - `bad_exit=10`
