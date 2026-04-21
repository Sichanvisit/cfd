# Product Acceptance PA0 Refreeze After XAU Upper-Reject Confirm Forecast Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_014137.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_014137.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T01:41:37`

after generated_at:

- `2026-04-01T12:56:57`

## 2. 대상 family

- `XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
- `XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
- follow-up check: `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`

## 3. delta

### confirm forecast

- `must_show 9 -> 5`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

### mixed forecast

- `must_show 6 -> 6`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

### NAS energy exact-row recheck

- `must_show 0 -> 0`
- `must_hide 0 -> 0`
- `must_block 12 -> 0`

## 4. live watch 메모

이번 재시작 뒤 fresh runtime row는 실제로 쌓이지 않았다.

- restart log: [cfd_main_restart_20260401_125318.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_125318.err.log)
- 핵심 증상: `MT5 connection unavailable`
- watch cutoff 이후 fresh symbol row count: `BTC=0 / NAS=0 / XAU=0`

즉 이번 delta는 `fresh exact row 재발`이 아니라 `persisted recent window turnover` 기준으로 해석해야 한다.

## 5. 해석

1. confirm forecast wait contract는 representative replay 기준으로는 이미 완전히 살아 있다.
2. live fresh row는 없었지만, recent persisted window가 앞으로 밀리면서 confirm backlog는 `9 -> 5`로 줄었다.
3. mixed forecast는 current build에서 이미 WAIT contract였고, 이번 refreeze에서는 아직 `6`이 그대로 남아 있다.
4. NAS energy exact row는 fresh 재발은 없었지만, PA0 must-block은 이번 latest 기준으로 `12 -> 0`이 확인됐다.

## 6. 현재 남은 메인 residue

latest must-show는 아래 세 family가 채우고 있다.

- `6 = XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
- `5 = XAUUSD + upper_reject_confirm + forecast_guard + observe_state_wait +`
- `4 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`
