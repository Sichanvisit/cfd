# Product Acceptance PA0 Refreeze After NAS Upper-Break-Fail Forecast Wait No-Probe Hide Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_212752.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_212752.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T21:18:37`

after generated_at:

- `2026-03-31T21:27:08`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 15 -> 13`
- `must_enter_candidate_count = 3 -> 0`
- `must_block_candidate_count = 12 -> 12`
- `divergence_seed_count = 2 -> 2`

## 3. target family delta

target:

- `NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`

delta:

- `must_hide 8 -> 8`

## 4. 왜 target이 그대로인가

이 축은 코드와 current-build replay는 성공했지만,
post-restart fresh exact recurrence가 아직 `0`이라
target family old backlog가 recent window에 그대로 남아 있다.

recent 240-row의 exact 5건은 모두 restart 전 old rows였다.

## 5. 주변 queue 변화

동시에 다른 must-hide family는 줄었다.

- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
  - `7 -> 5`

그래서 total `must_hide`는 `15 -> 13`으로 내려갔다.

must-show / must-block는 NAS outer-band family로 더 집중됐다.

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
  - `must_show 13 -> 15`
  - `must_block 10 -> 12`

## 6. 결론

이번 refreeze 결론은 아래와 같다.

```text
upper_break_fail hide contract는 구현 완료다.
다만 target queue를 실제로 줄였다고 확정하려면 fresh exact row가 한 번 더 필요하다.
현재 chart acceptance의 다음 메인축은 NAS outer-band must-show/must-block backlog다.
```
