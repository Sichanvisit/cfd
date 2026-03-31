# Product Acceptance PA0 Refreeze After NAS Sell Outer-Band No-Probe Wait Hide Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_182700.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_182700.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T17:57:59`
- latest generated_at = `2026-03-31T18:30:11`

관련 구현 문서:

- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 5 -> 0
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count만 보면 must-show / must-hide / must-block는 여전히 꽉 차 있다.

## 3. target NAS family는 실제로 15 -> 0이 됐다

이전 must-hide main family:

```text
NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe
```

이 family는 previous baseline에서 `15/15`를 채우고 있었지만,
latest baseline에서는 `0`이 됐다.

즉 이번 하위축의 목표였던
“NAS sell outer-band no-probe visible leakage 제거”
자체는 성공이다.

## 4. fresh hidden rows도 queue overlap 0이었다

restart 이후 fresh NAS hidden target rows는 아래였다.

- `2026-03-31T18:29:46`
- `2026-03-31T18:29:56`

전체 fresh hidden row count:

```text
fresh target row count = 4
queue overlap count = 0
```

즉 accepted hidden suppression과 PA0 skip logic은 live/fresh row 기준으로 실제로 먹었다.

## 5. 왜 total must-hide는 그대로인가

latest must-hide queue는 새 family가 `15/15`를 채운다.

```text
BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe
```

즉 NAS must-hide leakage가 사라진 자리를
BTC forecast-wait no-probe family가 채운 것이다.

이건 “NAS fix 실패”가 아니라
“기존 main family를 닫으니 다음 main family가 드러난 상태”로 보는 게 맞다.

## 6. must-show / must-block current composition

latest must-show:

- `14/15 = XAU outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `1/15 = NAS outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

latest must-block:

- `11/12 = XAU outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `1/12 = NAS outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

즉 현재 남은 visible problem은 probe-scene family와 XAU energy-soft-block backlog 쪽으로 이동했다.

## 7. 결론

```text
이번 refreeze의 결론은 “NAS no-probe leakage 축이 실제로 닫혔다”는 것이다.
target family는 15 -> 0이 됐고 fresh row도 queue overlap 0이었다.
지금 must-hide가 그대로인 이유는 새 BTC forecast-wait no-probe family가 다음 main leakage axis로 올라왔기 때문이다.
```
