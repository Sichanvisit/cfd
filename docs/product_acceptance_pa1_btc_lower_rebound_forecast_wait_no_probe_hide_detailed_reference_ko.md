# Product Acceptance PA1 BTC Lower-Rebound Forecast-Wait No-Probe Hide Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 이 문서의 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`
family를 왜 visible leakage가 아니라
`accepted hidden suppression`으로 처리해야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md)

## 2. 문제 family

latest PA0 baseline 기준 must-hide leakage `15/15`를 채우는 대상 family는 아래다.

- `symbol = BTCUSD`
- `observe_reason = lower_rebound_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = BUY`

대표 visible surface는 아래처럼 고정돼 있었다.

- `check_stage = PROBE`
- `check_display_ready = True`
- `display_score = 0.91`
- `display_repeat_count = 3`
- `display_importance_tier = high`
- `display_importance_source_reason = btc_lower_recovery_start`
- `box_state = LOWER`
- `bb_state = BREAKDOWN`

즉 probe scene은 없는데도 lower breakdown confirm row가
strong probe처럼 반복 노출되고 있었다.

## 3. 왜 leakage인가

이 family는 earlier accepted wait-check relief와 성격이 다르다.

- probe scene이 없다
- `probe_not_promoted`가 아니라 `forecast_guard + observe_state_wait`다
- chart에 `WAIT + checks`로 살려야 할 contract가 아니라
  아직 forecast guard 때문에 방향성을 보여주면 안 되는 confirm 대기다
- 그런데 importance source가 `btc_lower_recovery_start`로 붙으면서
  visible `PROBE/high/0.91/repeat=3`로 과상승한다

즉 의미는 아래에 더 가깝다.

```text
아직 lower recovery 구조를 계속 봐야 하는 건 맞지만,
forecast guard가 풀리지 않은 no-probe confirm wait를
directional BUY probe로 보여주는 건 과표시다.
```

이 family를 차트에 계속 보이면
PA0에서는 must-hide leakage가 누적되고,
chart acceptance에서도 “지금 보여줄 signal”과
“나중에 다시 볼 wait” 경계가 흐려진다.

## 4. 목표 contract

이 family의 목표 contract는 아래다.

- directional BUY probe로 보이지 않는다
- wait-check relief로도 올리지 않는다
- common modifier에서 hidden suppression으로 정리한다
- PA0에서도 accepted hidden suppression으로 분리한다

즉 이 축의 목적은
“가려서 덜 보이게”가 아니라
“애초에 visible probe로 surface되면 안 되는 row를
queue와 chart 양쪽에서 같이 정리”하는 것이다.

## 5. 구현 방향

구현 방향은 아래다.

1. common modifier soft-cap에 `btc_lower_rebound_forecast_wait_hide_without_probe` policy를 추가한다
2. 조건을 `BTCUSD + BUY + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe + btc_lower_recovery_start`로 고정한다
3. build path에서 이 family가 `display_ready = False`와 새 suppress reason으로 surface되게 만든다
4. painter는 hidden consumer suppression row를 top-level directional fallback으로 다시 그리지 않게 한다
5. PA0 baseline freeze script는 이 reason을 accepted hidden suppression으로 분리한다
6. unit test, live restart, fresh row verify, PA0 refreeze로 닫는다

## 6. 이번 하위축에서 하지 않는 것

이번 하위축에서 일부러 하지 않는 것은 아래다.

- BTC probe-scene wait-check relief family 수정
- XAU energy-soft-block backlog 정리
- NAS probe-scene visible family 수정
- entry / wait / hold / exit acceptance 수정

즉 이번 문서는 BTC forecast-wait no-probe visible leakage 하나만 닫는 상세 기준이다.

## 7. 완료 기준

이 하위축의 완료 기준은 아래다.

1. fresh BTC row에서 nested state가 실제로 `display_ready = False`와 new suppress reason으로 찍힌다
2. painter가 top-level BUY fallback을 다시 그리지 않는다
3. fresh row가 PA0 queue overlap `0`이 된다
4. 이전 must-hide main family가 queue에서 빠지고, 다음 problem family가 더 선명해진다

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 reopen point는 refreeze 결과로 다시 잡는다.

현재 기준으로는 아래 두 축이 다음 후보에 가깝다.

- `XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`

즉 BTC must-hide main leakage를 닫은 뒤에는
must-show / must-block backlog 쪽이 다시 전면으로 올라올 가능성이 높다.
