# Product Acceptance PA0 Refreeze After NAS Outer-Band Probe Guard Wait Display Contract Fresh Runtime Follow-Up

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `nas_outer_band_probe_against_default_side_wait_relief` 반영 이후,
exact target family fresh row가 실제로 다시 쌓인 다음
PA0 baseline을 한 번 더 얼려서
남아 있던 `must-show / must-block` queue가 실제로 줄어드는지 확인한 기록이다.

이번 follow-up의 질문은 아래와 같다.

```text
fresh runtime row가 실제로 WAIT + wait_check_repeat로 찍히는가?
그리고 그 이후 PA0 latest에서 NAS outer-band must-show / must-block가 실제로 줄어드는가?
```

## 2. 비교 기준

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_214930.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_214930.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

before generated_at:

- `2026-03-31T21:43:43`

after generated_at:

- `2026-03-31T21:49:05`

## 3. fresh runtime row 확인

post-restart recent row에서 exact target family fresh recurrence가 실제로 확인됐다.

대표 row 시각:

- `2026-03-31T21:48:30`
- `2026-03-31T21:48:42`

공통 surface:

- `symbol = NAS100`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `check_display_ready = True`
- `check_stage = OBSERVE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`
- `blocked_display_reason = outer_band_guard`

즉 이 family가 live runtime에서도 더 이상 hidden backlog surface가 아니라
`WAIT + repeated checks` contract로 기록되기 시작한 것이 확인됐다.

## 4. target family delta

target:

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

delta:

- `must_show 15 -> 8`
- `must_block 12 -> 8`

이 결과는 exact fresh row 유입 이후
target outer-band family가 PA0 queue에서 실제로 줄기 시작했다는 뜻이다.

## 5. 전체 summary가 그대로인 이유

baseline total summary는 아래처럼 그대로다.

- `must_show_missing_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`
- `must_hide_leakage_count = 0 -> 0`

즉 이번 follow-up의 결론은
`전체 queue가 다 비워졌다`가 아니라
`target family는 실제로 줄었지만, 그 자리를 다른 symbol family가 채웠다`에 가깝다.

after latest composition:

- `must_show`
  - `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe` = `8`
  - `BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe` = `5`
  - `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe` = `2`
- `must_block`
  - `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe` = `8`
  - `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe` = `2`
  - `BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe` = `2`

## 6. 해석

이번 follow-up으로 확인된 것은 세 가지다.

1. NAS outer-band exact family fresh row가 live runtime에서 실제로 다시 나왔다.
2. 그 fresh row는 `WAIT + wait_check_repeat + probe_guard_wait_as_wait_checks`로 기록됐다.
3. 그 이후 PA0 latest에서 target family의 `must-show / must-block`가 실제로 줄었다.

즉 이 축은 이제
`코드 replay상 맞다` 수준을 넘어
`live fresh row와 PA0 queue 감소까지 확인됐다`로 볼 수 있다.

## 7. 다음 축

이제 chart acceptance에 남은 메인은
`outer-band guard + probe_not_promoted` residue가 다른 symbol로 옮겨간 상태다.

자연스러운 다음 후보:

- `BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
- `XAUUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + xau_upper_sell_probe`

## 8. 한 줄 요약

```text
fresh NAS outer-band row가 실제로 WAIT + repeated checks로 찍힌 뒤,
PA0 latest에서 target family must-show 15 -> 8, must-block 12 -> 8로 줄어드는 것까지 확인됐다.
```
