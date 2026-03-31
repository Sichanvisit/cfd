# Product Acceptance PA0 Refreeze After NAS Outer-Band Probe Guard Wait Display Contract Delta

작성일: 2026-03-31 (KST)

## 1. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_214406.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_214406.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T21:27:08`

after generated_at:

- `2026-03-31T21:43:43`

## 2. baseline summary delta

- `must_show_missing_count = 15 -> 15`
- `must_hide_leakage_count = 13 -> 0`
- `must_enter_candidate_count = 0 -> 0`
- `must_block_candidate_count = 12 -> 12`

## 3. target family delta

target:

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

delta:

- `must_show 15 -> 15`
- `must_block 12 -> 12`

## 4. 왜 그대로인가

이번 구현은 current-build 기준으로
`probe_against_default_side` hidden row를 `WAIT + probe_guard_wait_as_wait_checks`로 복구한다.

하지만 post-restart recent 120-row에는 exact target family가 아직 다시 안 들어왔다.
그래서 latest PA0 queue는 여전히 old hidden backlog 기준으로 남아 있다.

## 5. 주변 queue 변화

동시에 must-hide는 전부 비워졌다.

- `NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
  - `8 -> 0`
- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
  - `5 -> 0`

즉 chart acceptance에서 남은 메인은 이제 must-show/must-block outer-band backlog로 완전히 집중됐다.

## 6. 결론

이번 refreeze 결론은 아래와 같다.

```text
must-hide는 0이 됐다.
남은 chart acceptance 메인은 NAS outer-band must-show/must-block 하나로 수렴했다.
이 축의 queue 감소를 확정하려면 fresh exact row가 한 번 더 필요하다.
```
