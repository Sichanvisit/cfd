# Product Acceptance PA0 Refreeze After NAS Upper-Reject Confirm Forecast Wait No-Probe Hide Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_205531.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_205531.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T20:47:40`

after generated_at:

- `2026-03-31T20:55:11`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 15`
- `must_enter_candidate_count = 11 -> 12`
- `must_block_candidate_count = 12 -> 12`

## 3. target family delta

target:

- `NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe`

delta:

- `must_hide 5 -> 0`

이 하위축의 목표였던 confirm no-probe visible leakage는 latest queue에서 사라졌다.

## 4. replacement backlog

같은 upper-reject 축 안에서 replacement must-hide가 더 또렷해졌다.

- `NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
  - `9 -> 7`
- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
  - `0 -> 8`

즉 confirm no-probe를 닫자
남은 문제는 probe-scene upper-reject backlog로 재집중됐다.

## 5. must-show / must-block 관찰

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
  - `must_show 12 -> 10`
  - `must_block 12 -> 10`

latest queue는 NAS upper-reject must-hide와 NAS outer-band hidden backlog가 함께 남아 있는 상태다.

## 6. 결론

이번 refreeze 결론은 아래와 같다.

```text
NAS upper_reject_confirm no-probe visible leakage는 닫혔다.
다음 PA1 메인축은 upper_reject probe family다.
```
