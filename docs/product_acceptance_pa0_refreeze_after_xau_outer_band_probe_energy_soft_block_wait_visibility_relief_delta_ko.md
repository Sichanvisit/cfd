# Product Acceptance PA0 Refreeze After XAU Outer-Band Probe Energy Soft-Block Wait Visibility Relief Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_230452.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_230452.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T22:47:06`

after generated_at:

- `2026-03-31T23:09:10`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 4 -> 15`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 0 -> 1`

## 3. target family delta

target:

- `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`

delta:

- `must_show 15 -> 0`
- `must_block 12 -> 0`
- `must_hide 0 -> 0`

즉 직전 PA0 main residue였던 target family는 latest queue에서 빠졌다.

## 4. fresh runtime 메모

post-restart cutoff (`2026-03-31T23:04:52`) 이후:

- exact target fresh row = `0`
- `WAIT + wait_check_repeat + xau_outer_band_probe_energy_soft_block_as_wait_checks` fresh row = `0`

즉 이번 delta는 `fresh exact row 확인`이 아니라
`current-build replay + recent window turnover` 결과를 기록한 것이다.

## 5. replacement queue

after latest main queue는 아래처럼 바뀌었다.

- `must_show = 15`
  - `12 = XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
  - `3 = XAUUSD + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
- `must_block = 12`
  - `12 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`
- `must_hide = 15`
  - `13 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked +`
  - `2 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`

## 6. 해석

이번 delta는 아래 의미로 본다.

1. XAU outer-band probe energy-soft-block family는 PA0 main residue에서 빠졌다.
2. total `must_show / must_block`가 유지된 건 구현 실패가 아니라 replacement family 이동 때문이다.
3. must-hide가 `4 -> 15`로 커진 건 recent window가 완전히 다른 XAU/BTC family로 바뀌었기 때문이다.

## 7. 다음 메인축

현재 latest 기준 다음 자연스러운 PA1 메인축은 아래 둘이다.

- `XAUUSD + upper_reject_confirm + energy_soft_block + execution_soft_blocked +`
- `BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`

한 줄로 줄이면,

```text
XAU outer-band probe energy-soft-block main residue는 latest PA0에서 15/12 -> 0/0으로 빠졌고,
queue의 메인은 XAU no-probe confirm energy family와 BTC upper probe blocked family로 이동했다.
```
