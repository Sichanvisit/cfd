# Product Acceptance PA0 Refreeze After XAU Upper-Reject Probe Forecast Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_235008.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_235008.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T23:46:17`

after generated_at:

- `2026-03-31T23:50:08`

## 2. target family

- `symbol = XAUUSD`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = forecast_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_upper_sell_probe`

## 3. delta

- `must_show 7 -> 7`
- `must_hide 0 -> 0`
- `must_block 0 -> 0`

## 4. 해석

이 delta는 구현 실패가 아니다.

이번 턴에서는:

1. representative replay가 이미 `WAIT + wait_check_repeat + xau_upper_reject_probe_forecast_wait_as_wait_checks`로 바뀌었다.
2. cfd live를 재시작해 fresh row를 봤지만 exact target recurrence는 아직 없었다.
3. 그래서 PA0 latest는 새 reason row를 아직 recent window에서 소비하지 못했고, old hidden backlog `7`이 그대로 남아 있다.

즉 상태를 한 줄로 정리하면:

```text
구현 완료 + replay 확인 완료 + live recurrence pending
```

## 5. 현재 must-show main queue

latest 기준 main must-show는 아래다.

- `7 = XAUUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe`
- `6 = XAUUSD + upper_reject_mixed_confirm + forecast_guard + observe_state_wait +`
- `2 = BTCUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + probe_not_promoted + btc_upper_sell_probe`

## 6. 다음 체크 포인트

- exact `upper_reject_probe_observe + forecast_guard + probe_not_promoted + xau_upper_sell_probe` fresh row가 새 reason으로 한 번이라도 찍히는지 재확인
- fresh row가 들어온 뒤 PA0 refreeze 재실행
