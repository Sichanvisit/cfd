# Product Acceptance PA0 Refreeze After Sell Entry-Gate Wait Display Contract Follow-Up Delta

작성일: 2026-04-01 (KST)

## 기준

- latest baseline: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- snapshot freeze: [product_acceptance_pa0_baseline_snapshot_20260401_165208.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_165208.json)

## 이번 refreeze 해석

이번 refreeze는 `second restart 이후 exact recurrence가 다시 안 뜬 상태`를 고정한 freeze다.

baseline summary:

- `must_show_missing_count = 15`
- `must_hide_leakage_count = 5`
- `must_enter_candidate_count = 12`
- `must_block_candidate_count = 5`

## entry-gate residue

`must_show_missing` 안에서 이번 축 residue는 이렇게 남아 있다.

- `NAS100 + upper_break_fail_confirm + pyramid_not_in_drawdown` `4`
- `NAS100 + upper_break_fail_confirm + pyramid_not_progressed` `2`
- `NAS100 + upper_break_fail_confirm + clustered_entry_price_zone` `2`
- `XAUUSD + upper_reject_mixed_confirm + pyramid_not_in_drawdown` `3`
- `XAUUSD + upper_reject_mixed_confirm + clustered_entry_price_zone` `1`

합치면:

- NAS entry-gate residue `8`
- XAU entry-gate residue `4`

이 값은 새 policy가 안 먹어서가 아니라, first blank fresh row와 old blank backlog가 recent window에 아직 남아 있기 때문으로 해석한다.

## 나머지 queue

이번 refreeze에서 entry-gate 축 바깥의 메인 residue는 이 family다.

- `must_hide`: `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait` `5`
- `must_block`: `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait` `5`
- `must_show`: `NAS upper_edge_observe` `3`

## 결론

이번 delta의 의미는 “sell entry-gate 축이 실패했다”가 아니다.

정확한 해석은:

- code / replay 기준으로는 닫힘
- live first blank row를 보고 hidden-restore follow-up까지 추가함
- second restart short watch에선 exact recurrence가 다시 안 떠서
- current PA0에는 old blank residue가 아직 남아 있음

다음 확인 포인트는 exact fresh `NAS/XAU entry-gate` row가 다시 뜰 때 새 reason이 실제 기록되는지 보는 것이다.
