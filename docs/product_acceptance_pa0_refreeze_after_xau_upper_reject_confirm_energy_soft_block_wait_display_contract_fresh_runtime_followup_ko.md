# Product Acceptance PA0 Refreeze After XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-03-31 (KST)

## 1. 재확인 범위

이 문서는
[product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
이후 fresh runtime row를 조금 더 쌓은 뒤 다시 PA0를 얼린 follow-up이다.

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_232942.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_232942.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

## 2. fresh exact row 재확인

cutoff:

- `2026-03-31T23:18:40`

재확인 결과:

- exact target fresh row = `0`
- `WAIT + wait_check_repeat + xau_upper_reject_confirm_energy_soft_block_as_wait_checks` fresh row = `0`

즉 live에서 새 contract가 찍힌 exact row는 아직 recent window에 없다.

## 3. PA0 delta

before generated_at:

- `2026-03-31T23:22:40`

after generated_at:

- `2026-03-31T23:36:38`

target:

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`

delta:

- `must_show 12 -> 5`
- `must_block 0 -> 0`
- `must_hide 0 -> 0`

즉 fresh exact row는 없었지만,
recent window turnover만으로도 old hidden backlog가 일부 빠졌다.

## 4. 현재 queue

after latest 기준 main queue는 아래와 같다.

- `must_show = 15`
  - `5 = XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
  - `5 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
  - `5 = XAUUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`
- `must_block = 12`
  - `8 = BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`
  - `4 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
- `must_hide = 15`
  - `12 = BTCUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait +`
  - `3 = BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`

## 5. 해석

이번 follow-up은 아래 의미로 본다.

1. XAU upper-reject confirm target family는 fresh exact row 증빙 없이도 `12 -> 5`로 줄었다.
2. 즉 이 축은 old hidden backlog가 recent window에서 자연스럽게 빠지고 있는 상태다.
3. 아직 `0`이 아니므로 live fresh recurrence 확인 또는 추가 turnover가 더 필요하다.

## 6. 다음 자연스러운 순서

다음은 아래 두 개를 같이 보면 된다.

- XAU upper-reject confirm target이 `5 -> 0`으로 더 줄어드는지 재확인
- 새 must-show로 올라온 `XAU upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe` 축 검토
