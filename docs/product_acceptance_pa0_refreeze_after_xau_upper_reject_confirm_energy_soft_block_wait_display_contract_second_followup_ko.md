# Product Acceptance PA0 Refreeze After XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Second Follow-Up

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `upper_reject_confirm + energy_soft_block` 축이 기존 follow-up에서 `12 -> 5`까지 줄어든 뒤,
추가 runtime row가 쌓인 상태에서 정말 `5 -> 0`까지 닫혔는지 확인한 두 번째 follow-up이다.

관련 문서:

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md)

## 2. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_234617.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_234617.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T23:36:38`

after generated_at:

- `2026-03-31T23:46:17`

## 3. target delta

target family:

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`

delta:

- `must_show 5 -> 0`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

## 4. 해석

이번 follow-up의 결론은 단순하다.

- `upper_reject_confirm` residue는 PA0 recent window에서 더 이상 남아 있지 않다.
- 즉 이 축은 now-closed 상태로 봐도 된다.

중요한 점은:

- 이번 `5 -> 0`은 fresh exact row 증빙으로 닫힌 것이 아니라
- additional runtime turnover로 old hidden backlog가 recent window 밖으로 빠지면서 닫힌 것이다.

그래도 PA0 기준선에서는 target family가 `0`이므로,
실무 해석상 이 하위축은 닫혔다고 봐도 무방하다.

## 5. 이후 상태

같은 시점 must-show는 아래 family들로 교체됐다.

- `7 = XAUUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`
- `6 = XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
- `2 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`

즉 다음 XAU 메인 residue는 이제 `upper_reject_probe forecast wait` 축이다.
