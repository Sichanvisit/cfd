# Product Acceptance PA0 Refreeze After XAU Upper-Reject Confirm Energy Soft-Block Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_231838.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_231838.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T23:09:10`

after generated_at:

- `2026-03-31T23:22:40`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 1 -> 1`

## 3. target family delta

target:

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`

delta:

- `must_show 12 -> 12`
- `must_block 0 -> 0`
- `must_hide 0 -> 0`

즉 target family는 latest PA0에서도 아직 그대로 남아 있다.

## 4. fresh runtime 메모

post-restart cutoff (`2026-03-31T23:18:40`) 이후:

- exact target fresh row = `0`
- `xau_upper_reject_confirm_energy_soft_block_as_wait_checks` fresh row = `0`

즉 이번 delta는
`코드가 안 먹었다`
가 아니라
`새 contract가 찍힌 fresh row가 아직 recent window에 없음`
을 의미한다.

## 5. replacement queue

after latest 기준 queue는 아래와 같다.

- `must_show = 15`
  - `12 = XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
  - `3 = XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
- `must_block = 12`
  - `12 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
- `must_hide = 15`
  - `9 = BTCUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait +`
  - `3 = BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`
  - `3 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`

## 6. 해석

이번 delta는 아래 의미로 본다.

1. 구현 자체는 current-build replay에서 확인됐다.
2. 그러나 fresh exact row가 아직 다시 나오지 않아서 PA0 old hidden backlog는 그대로 남아 있다.
3. 따라서 이번 축은 `implementation complete, live recurrence pending` 상태다.

## 7. 다음 메인축

현재 자연스러운 다음 선택지는 아래 둘 중 하나다.

- fresh XAU upper-reject-confirm exact row 재발을 조금 더 기다린 뒤 refreeze 재확인
- `XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +` mirror family를 바로 같이 정리
