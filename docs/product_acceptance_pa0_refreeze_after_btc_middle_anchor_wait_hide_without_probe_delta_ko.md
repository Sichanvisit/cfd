# Product Acceptance PA0 Refreeze After BTC Middle-Anchor Wait Hide Without Probe Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_003508.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_003508.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T00:24:43`

after generated_at:

- `2026-04-01T00:38:54`

## 2. target family

- `symbol = BTCUSD`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

## 3. delta

- `must_show 13 -> 0`
- `must_hide 5 -> 12`
- `must_block 12 -> 0`

baseline total은 그대로 유지되었다.

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`

## 4. 해석

이 delta는 실패가 아니라 queue composition이 바뀐 결과다.

이번 refreeze에서는:

1. `BUY` no-probe row는 `structural_wait_hide_without_probe` accepted hidden으로 정리됐다.
2. `SELL` no-probe row는 current build replay에서 `btc_sell_middle_anchor_wait_hide_without_probe`로 정리된다.
3. 다만 live restart 이후 fresh exact middle-anchor recurrence는 없었다.
4. 그래서 old sell backlog가 recent window에 남아 `must-hide`를 계속 채운다.

즉 상태를 한 줄로 정리하면:

```text
must-show/must-block cleanup 완료 + must-hide old sell backlog 잔존 + fresh exact recurrence pending
```

## 5. after queue composition

after latest 기준 main queue는 아래로 바뀌었다.

- `must_show_missing`
  - `14 = XAUUSD + upper_reject_probe_observe + clustered_entry_price_zone + xau_upper_sell_probe`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

- `must_hide_leakage`
  - `12 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait`
  - `3 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

- `must_block_candidates`
  - `11 = NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

## 6. 다음 체크 포인트

- fresh BTC middle-anchor exact row가 새 hidden reason으로 실제 기록되는지 재확인
- 그 뒤 PA0를 다시 얼려 `must-hide 12 -> 0`이 되는지 확인
- 병행 메인 residue로는 `XAU upper_reject_probe + clustered_entry_price_zone`와 `NAS upper_break_fail + energy_soft_block`를 볼 수 있다
