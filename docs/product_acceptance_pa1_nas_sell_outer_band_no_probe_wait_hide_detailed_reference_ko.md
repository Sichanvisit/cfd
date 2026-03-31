# Product Acceptance PA1 NAS Sell Outer-Band No-Probe Wait Hide Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 이 문서의 목적

이 문서는 PA1 chart acceptance 하위축 중
`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`
family를 왜 visible observe leakage가 아니라
`accepted hidden suppression`으로 처리해야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 문제 family

대상 family는 아래 조건이 동시에 붙는 NAS structural wait row다.

- `symbol = NAS100`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = SELL`

latest PA0에서 이 family는 must-hide leakage를 `15/15` 채우고 있었다.

대표 row surface:

- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_score = 0.75`
- `display_repeat_count = 1`
- `display_importance_source_reason = ""`
- `blocked_display_reason = outer_band_guard`

즉 probe scene도 없고 importance source도 없는데
directional SELL observe가 계속 보이는 상태였다.

## 3. 왜 leakage인가

이 family는 earlier accepted wait-check relief family와 성격이 다르다.

- probe scene이 없다
- promote 직전 반복 체크도 아니다
- importance source가 없다
- `outer_band_guard + observe_state_wait`만 남아 있다

즉 의미는 아래에 더 가깝다.

```text
아직 방향성을 보여줄 만큼 구조가 성숙하지 않았고,
guard 때문에 그냥 observe 대기 중인 초기 약신호
```

이런 row를 차트에 directional observe로 보이면
chart acceptance에서는 과표시가 되고,
PA0에서는 must-hide leakage로 계속 누적된다.

## 4. 목표 contract

이 family의 목표 contract는 아래다.

- directional SELL observe로 보이지 않는다
- wait-check relief로도 승격하지 않는다
- 그냥 hidden suppression으로 처리한다
- PA0에서도 accepted hidden suppression으로 분리한다

즉 이 축의 목적은
“보여주는 방식 변경”이 아니라
“애초에 보여주지 않는 것이 맞는 row를 baseline queue에서도 문제로 재집계하지 않게 정리”하는 것이다.

## 5. 구현 방향

구현 방향은 아래다.

1. common modifier soft-cap에 `SELL outer-band no-probe wait hide` policy를 추가한다
2. build path에서 이 family가 `display_ready = False`가 되도록 suppress한다
3. painter는 hidden consumer state가 있으면 top-level observe fallback도 그리지 않게 한다
4. PA0 baseline freeze script는 이 suppress reason을 accepted hidden suppression으로 분리한다
5. unit test, live restart, fresh row verify, PA0 refreeze로 닫는다

## 6. 이번 하위축에서 하지 않는 것

이번 하위축에서 일부러 하지 않는 것은 아래다.

- probe scene이 있는 NAS family 수정
- XAU energy-soft-block backlog 정리
- BTC new must-hide family 수정
- entry / wait / hold / exit acceptance 수정

즉 이번 문서는 NAS SELL outer-band no-probe leakage 하나만 닫는 상세 기준이다.

## 7. 완료 기준

이 하위축의 완료 기준은 아래다.

1. fresh NAS row에서 nested state가 실제로 `display_ready = False`와 new suppress reason으로 찍힌다
2. painter가 top-level observe fallback을 그리지 않는다
3. fresh row가 PA0 queue overlap `0`이 된다
4. 이전 must-hide main family가 queue에서 빠지고, 다음 main family가 더 선명해진다

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 PA1 메인 reopen point는 아래다.

- `BTCUSD + lower_rebound_confirm + forecast_guard + observe_state_wait + no_probe`

즉 NAS no-probe leakage를 닫은 뒤에는 must-hide main axis가 BTC forecast-wait no-probe family로 이동한다.
