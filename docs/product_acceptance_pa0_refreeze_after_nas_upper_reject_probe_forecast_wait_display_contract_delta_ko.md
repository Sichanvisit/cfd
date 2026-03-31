# Product Acceptance PA0 Refreeze After NAS Upper-Reject Probe Forecast Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_205531.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_205531.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T20:47:40`

after generated_at:

- `2026-03-31T20:55:11`

## 2. target family delta

target:

- `NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`

delta:

- `must_hide 9 -> 7`

## 3. 왜 partial reduction인가

이번 delta는 `current-build replay는 성공`인데 `PA0 queue는 일부만 감소`한 케이스다.

이유:

- PA0 freeze는 row에 저장된 `consumer_check_state_v1`를 기준으로 본다
- old backlog row에는 새 `WAIT + wait_check_repeat` 계약이 아직 기록되지 않았다
- post-restart recent 240-row에서 exact target family recurrence가 `0`이었다

즉 fresh row가 실제로 다시 찍히기 전까지는
old backlog 일부가 must-hide queue에 남아 있을 수 있다.

## 4. 같은 upper-reject 축의 최신 composition

latest must-hide upper-reject composition:

- `7 = NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
- `8 = NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

즉 probe forecast family가 줄어든 자리 일부를
`probe_promotion_gate` family가 채웠다.

## 5. 결론

이번 refreeze 결론은 아래와 같다.

```text
probe forecast wait contract 코드는 준비됐다.
대표 row replay는 맞다.
PA0 queue를 완전히 비우려면 exact fresh recurrence가 한 번 더 필요하다.
현재 다음 메인축은 probe_promotion_gate family다.
```
