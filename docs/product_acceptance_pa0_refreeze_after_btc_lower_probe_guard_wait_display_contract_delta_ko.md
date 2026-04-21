# Product Acceptance PA0 Refreeze After BTC Lower-Probe Guard Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_002104.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_002104.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T00:06:37`

after generated_at:

- `2026-04-01T00:24:43`

## 2. target family

- `symbol = BTCUSD`
- `observe_reason = lower_rebound_probe_observe`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `blocked_by = forecast_guard`
- `blocked_by = barrier_guard`

## 3. delta

- `forecast_guard must_show 8 -> 0`
- `forecast_guard must_block 6 -> 0`
- `barrier_guard must_hide 15 -> 0`

baseline total은 그대로 유지되었다.

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`

## 4. 해석

이번 delta는 `live exact recurrence가 없어서 미확인` 상태가 아니다.

이번 refreeze에서는:

1. representative replay가 이미 `WAIT + wait_check_repeat + btc_lower_probe_guard_wait_as_wait_checks`로 바뀌었다.
2. live restart 후 fresh BTC row를 11개 관찰했지만 exact target recurrence는 없었다.
3. 그 사이 recent window turnover가 진행되면서 target lower-rebound probe family가 queue에서 모두 빠졌다.

즉 상태를 한 줄로 정리하면:

```text
replay 확인 완료 + fresh exact recurrence 없음 + queue turnover로 target family 종료
```

## 5. after queue composition

after latest 기준 main queue는 아래로 바뀌었다.

- `must_show_missing`
  - `13 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`
  - `2 = NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait`

- `must_hide_leakage`
  - `10 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
  - `5 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`

- `must_block_candidates`
  - `12 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`

## 6. 다음 체크 포인트

- BTC main residue를 `middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait` 축으로 이동
- XAU mixed energy-soft-block residue와 병행 비교
- fresh lower-rebound exact row가 다시 뜨면 새 reason으로 기록되는지만 후행 확인
