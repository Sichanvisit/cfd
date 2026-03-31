# Product Acceptance PA0 Refreeze After BTC Lower-Rebound Forecast-Wait No-Probe Hide Delta

작성일: 2026-03-31 (KST)

## 1. 비교 대상

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_190640.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_190640.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

기준 시각:

- snapshot generated_at = `2026-03-31T18:30:11`
- latest generated_at = `2026-03-31T19:06:40`

관련 구현 문서:

- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md)

## 2. baseline summary delta

```text
must_show_missing_count: 15 -> 15
must_hide_leakage_count: 15 -> 15
must_enter_candidate_count: 0 -> 12
must_block_candidate_count: 12 -> 12
divergence_seed_count: 0 -> 0
```

즉 total count만 보면 must-show / must-hide / must-block는 여전히 꽉 차 있다.

## 3. target BTC family는 실제로 15 -> 0이 됐다

이전 must-hide main family:

```text
BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe
```

이 family는 previous baseline에서 `15/15`를 채우고 있었지만,
latest baseline에서는 `0`이 됐다.

즉 이번 하위축의 목표였던
“BTC forecast-wait no-probe visible leakage 제거”
자체는 성공이다.

## 4. 왜 total must-hide는 그대로인가

latest must-hide queue는 NAS family가 새로 `15/15`를 채운다.

```text
13 = NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe
2  = NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe
```

즉 BTC must-hide leakage가 사라진 자리를
NAS no-probe family가 채운 것이다.

이건 “BTC fix 실패”가 아니라
“기존 main family를 닫으니 다음 main family가 드러난 상태”로 보는 게 맞다.

## 5. must-show / must-block current composition

latest must-show:

- `11/15 = BTC lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `4/15 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

latest must-block:

- `8/12 = BTC lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `4/12 = BTC outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

즉 현재 남은 visible problem은
BTC energy-soft-block backlog와
NAS no-probe must-hide family 쪽으로 이동했다.

## 6. live restart observation

`main.py`는 `2026-03-31T19:00:02`에 재시작했다.

post-restart fresh BTC rows에서는
exact target family가 재발생하지 않았고,
대신 아래 family가 쌓였다.

- `lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `lower_rebound_probe_observe + probe_promotion_gate + probe_not_promoted + btc_lower_buy_conservative_probe`
- `outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`

즉 live window 자체가 이미 다음 backlog family로 이동한 상태였다.

## 7. 결론

```text
이번 refreeze의 결론은 “BTC forecast-wait no-probe leakage 축이 실제로 닫혔다”는 것이다.
target family는 15 -> 0이 됐고,
이제 PA1 메인 문제는 NAS must-hide no-probe family와
BTC energy-soft-block must-show / must-block backlog로 이동했다.
```
