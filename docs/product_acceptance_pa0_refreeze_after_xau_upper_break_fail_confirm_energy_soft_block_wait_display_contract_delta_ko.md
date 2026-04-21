# Product Acceptance PA0 Refreeze After XAU Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_232942.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_232942.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T23:22:40`

after generated_at:

- `2026-03-31T23:33:36`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 1 -> 1`

## 3. target family delta

target:

- `XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`

delta:

- `must_show 3 -> 0`
- `must_block 0 -> 0`
- `must_hide 0 -> 0`

즉 mirror residue였던 target family는 latest queue에서 빠졌다.

## 4. fresh runtime 메모

post-restart cutoff (`2026-03-31T23:29:45`) 이후:

- exact target fresh row = `0`
- `xau_upper_break_fail_confirm_energy_soft_block_as_wait_checks` fresh row = `0`

즉 이번 delta는
`fresh exact row 증빙`
이 아니라
`current-build replay + recent window turnover`
결과를 기록한 것이다.

## 5. replacement queue

after latest 기준 queue는 아래와 같다.

- `must_show = 15`
  - `13 = XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
  - `2 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
- `must_block = 12`
  - `6 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
  - `6 = BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`
- `must_hide = 15`
  - `12 = BTCUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait +`
  - `3 = BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`

## 6. 해석

이번 delta는 아래 의미로 본다.

1. XAU upper-break-fail confirm mirror residue는 latest queue에서 빠졌다.
2. 그러나 fresh exact row 증빙이 없으므로, live 확정 근거는 replay 쪽이 더 강하다.
3. 현재 main residue는 다시 `XAU upper_reject_confirm`으로 수렴했다.

## 7. 다음 메인축

현재 자연스러운 다음 선택지는 아래 둘이다.

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +` fresh 재확인
- `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
