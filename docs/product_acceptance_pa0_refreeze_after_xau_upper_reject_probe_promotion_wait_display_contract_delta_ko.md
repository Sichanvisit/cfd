# Product Acceptance PA0 Refreeze After XAU Upper-Reject Probe Promotion Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_011221.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_011221.json)
- `generated_at = 2026-04-01T01:00:33`

after latest:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T01:16:40`

target family:

- `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`

## 2. Fresh Runtime Confirm

cutoff:

- `2026-04-01T01:12:23`

fresh exact row:

- `2026-04-01T01:16:23`

fresh exact row state:

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_upper_reject_probe_promotion_wait_as_wait_checks`

## 3. Target Delta

- `must_show 15 -> 12`
- `must_hide 0 -> 0`
- `must_block 5 -> 0`

핵심 해석:

- `must_block`는 이번 refreeze에서 실제로 닫혔다.
- `must_show`는 fresh row 반영으로 줄었지만, 같은 family old hidden backlog `12`가 recent window에 남아 있다.

## 4. Latest Queue Composition

latest summary:

- `must_show_missing_count = 15`
- `must_hide_leakage_count = 1`
- `must_enter_candidate_count = 5`
- `must_block_candidate_count = 12`
- `divergence_seed_count = 0`

latest top queue:

- `must_show 12`: `XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
- `must_show 2`: `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
- `must_show 1`: `BTCUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
- `must_hide 1`: `XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `must_block 9`: `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`
- `must_block 2`: `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
- `must_block 1`: `BTCUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

## 5. 결론

이번 축은 `구현 완료 + fresh live 확인 완료 + must_block 제거 확인 완료` 상태다.

남은 일은 두 갈래다.

1. 같은 XAU promotion family의 old backlog turnover가 더 진행돼 `must_show 12 -> 0`으로 내려가는지 follow-up
2. 동시에 현재 큰 block residue인 `NAS upper_break_fail energy_soft_block` 축으로 이어가기
