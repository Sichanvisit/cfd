# Product Acceptance PA0 Refreeze After NAS Upper-Reject Probe Promotion Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_211930.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_211930.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T20:55:11`

after generated_at:

- `2026-03-31T21:18:37`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_enter_candidate_count = 12 -> 3`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 0 -> 2`

## 3. target family delta

target:

- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

delta:

- `must_hide 8 -> 7`

## 4. 왜 partial reduction인가

이 축은 `코드/테스트/current-build replay`는 성공했지만,
post-restart fresh exact recurrence가 아직 `0`이라
PA0 queue에서는 old backlog `7`이 그대로 남아 있다.

recent 240-row 안의 exact 5건은 모두 restart 전 old rows였고
chart wait contract는 비어 있었다.

## 5. replacement backlog

latest must-hide composition은 아래다.

- `8 = NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
- `7 = NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

즉 probe-promotion family가 줄어든 자리 일부를
`upper_break_fail_confirm` no-probe family가 채웠다.

## 6. must-show / must-block 관찰

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
  - `must_show 10 -> 13`
  - `must_block 10 -> 10`

즉 현재 chart acceptance main backlog는
NAS must-hide `upper_break_fail_confirm` 축과
NAS must-show/must-block `outer_band` 축으로 더 선명해졌다.

## 7. 결론

이번 refreeze 결론은 아래와 같다.

```text
probe_promotion wait contract 코드는 준비됐다.
representative replay도 맞다.
PA0 queue를 완전히 비우려면 fresh exact recurrence가 한 번 더 필요하다.
다음 PA1 메인축은 NAS upper_break_fail_confirm no-probe family다.
```
