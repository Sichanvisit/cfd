# Product Acceptance PA0 Refreeze After XAU Upper-Reclaim Wait Hide Without Probe Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- 이전 baseline snapshot:
  - [product_acceptance_pa0_baseline_snapshot_20260401_165208.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_165208.json)
- 최신 baseline:
  - [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- latest generated_at:
  - `2026-04-01T17:16:41`

## 2. target family delta

target:

- `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe`

queue 변화:

- `must_hide 5 -> 0`
- `must_block 5 -> 0`

## 3. 해석

이번 축은 `wait relief`가 아니라 `hidden suppression mirror`였다.

direct exact fresh row recurrence는 short watch 안에서 `0`건이었지만:

- representative replay는 새 hidden reason으로 정상 resolve됐고
- recent window turnover 이후 PA0 queue에서는 target family가 사라졌다

즉 이번 축은 `live exact row proof pending`이 남아 있어도, PA0 queue 기준으로는 닫힌 상태로 봐도 된다.

## 4. latest queue 이동

최신 baseline 기준 residue는 XAU upper reclaim에서 다른 family로 이동했다.

- `must_show_missing = 15`
- `must_hide_leakage = 0`
- `must_block_candidates = 0`
- `must_enter_candidates = 12`

주요 잔여축:

- `XAU outer_band_reversal_support_required_observe + clustered_entry_price_zone / pyramid_not_in_drawdown + xau_upper_sell_probe`
- `NAS upper_edge_observe + observe_state_wait`

## 5. 연결 문서

- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md)
