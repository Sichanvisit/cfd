# Product Acceptance PA0 Refreeze After XAU Upper-Reject Mixed Confirm Energy Soft-Block Wait Display Contract Delta

작성일: 2026-04-01 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260401_005624.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_005624.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-04-01T00:46:32`

after generated_at:

- `2026-04-01T01:00:33`

## 2. target family

- `symbol = XAUUSD`
- `observe_reason = upper_reject_mixed_confirm`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = (blank)`

## 3. delta

- `must_show 9 -> 0`
- `must_hide 15 -> 3`
- `must_block 11 -> 3`

baseline total도 같이 움직였다.

- `must_hide_leakage_count = 15 -> 3`
- `must_enter_candidate_count = 6 -> 12`

## 4. 해석

이번 delta는 구현이 실제로 live와 PA0 queue에 먹었다는 뜻이다.

이번 턴에서는:

1. representative replay가 `WAIT + wait_check_repeat + xau_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`로 바뀌었다.
2. fresh live exact row `2026-04-01T01:00:11`에서 같은 reason이 실제로 찍혔다.
3. 그 뒤 PA0 refreeze에서 target family가 `must_show / must_hide / must_block` 모두 크게 줄었다.

즉 상태를 한 줄로 정리하면:

```text
replay 확인 완료 + fresh live 확인 완료 + PA0 queue 대폭 감소
```

## 5. after queue composition

after latest 기준 main queue는 아래처럼 바뀌었다.

- `must_show_missing`
  - `15 = XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`

- `must_hide_leakage`
  - `3 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

- `must_block_candidates`
  - `5 = XAUUSD + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`
  - `4 = XAUUSD + outer_band_reversal_support_required_observe + opposite_position_lock + opposite_position_lock + xau_upper_sell_probe`
  - `3 = XAUUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

## 6. 다음 체크 포인트

- 남은 `upper_reject_mixed_confirm + energy_soft_block` old backlog `3`이 turnover로 사라지는지 확인
- 다음 main XAU 축인 `upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + xau_upper_sell_probe`로 이동
