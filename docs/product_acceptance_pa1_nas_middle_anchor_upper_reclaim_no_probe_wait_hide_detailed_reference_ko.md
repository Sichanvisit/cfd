# Product Acceptance PA1 NAS Middle-Anchor and Upper-Reclaim No-Probe Wait Hide Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 이 문서의 목적

이 문서는 PA1 chart acceptance 하위축 중
아래 NAS no-probe visible family를 왜 `accepted hidden suppression`으로 처리해야 하는지 고정하는 상세 reference다.

- `NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
- `NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe`

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md)

## 2. 문제 family

latest PA0 baseline 기준 must-hide leakage `15/15`를 채우는 대상 family는 아래다.

1. middle-anchor sell wait

- `symbol = NAS100`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = SELL`
- representative surface = `OBSERVE + display_ready=True + score=0.75 + repeat=1 + no importance`

2. upper-reclaim buy wait

- `symbol = NAS100`
- `observe_reason = upper_reclaim_strength_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `check_side = BUY`
- representative surface = `PROBE/OBSERVE + display_ready=True + no importance`

공통점은 아래다.

- 둘 다 probe scene이 없다
- 둘 다 importance source가 없다
- 둘 다 guard 아래 wait 상태다
- 그런데 chart에는 directional row로 계속 보인다

## 3. 왜 leakage인가

이 family는 earlier accepted wait-check relief와 성격이 다르다.

- `scene_probe`가 없다
- `probe_not_promoted` 반복 체크도 아니다
- importance source가 없다
- 사실상 guard 아래 no-probe wait surface다

즉 의미는 아래에 더 가깝다.

```text
아직 방향성을 차트에 보여줄 만큼 구조가 성숙하지 않았고,
guard 때문에 그냥 observe/wait 중인 초기 약신호
```

이런 row를 directional NAS signal로 계속 보이면
chart acceptance에서는 과표시가 되고,
PA0에서는 must-hide leakage가 누적된다.

## 4. 목표 contract

이 family의 목표 contract는 아래다.

- directional BUY/SELL row로 보이지 않는다
- wait-check relief로도 승격하지 않는다
- common modifier에서 hidden suppression으로 정리한다
- PA0에서도 accepted hidden suppression으로 분리한다

즉 이 축의 목적은
“보여주는 방식 변경”이 아니라
“애초에 보여주지 않는 것이 맞는 no-probe wait row를 baseline queue에서도 문제로 재집계하지 않게 정리”하는 것이다.

## 5. 구현 방향

구현 방향은 아래다.

1. `middle-anchor sell no-probe wait hide` policy 추가
2. `upper-reclaim buy no-probe wait hide` policy 추가
3. build path에서 두 family가 `display_ready = False`와 새 suppress reason으로 surface되게 만든다
4. painter는 hidden consumer suppression row를 top-level directional fallback으로 다시 그리지 않게 한다
5. PA0 baseline freeze script는 두 reason을 accepted hidden suppression으로 분리한다
6. unit test, live restart, fresh row verify, PA0 refreeze로 닫는다

## 6. 이번 하위축에서 하지 않는 것

이번 하위축에서 일부러 하지 않는 것은 아래다.

- NAS probe-scene family 수정
- BTC energy-soft-block backlog 정리
- XAU backlog 정리
- entry / wait / hold / exit acceptance 수정

즉 이번 문서는 NAS must-hide no-probe main axis만 닫는 상세 기준이다.

## 7. 완료 기준

이 하위축의 완료 기준은 아래다.

1. fresh NAS row에서 nested state가 실제로 `display_ready = False`와 new suppress reason으로 찍힌다
2. painter가 top-level directional fallback을 그리지 않는다
3. fresh row가 PA0 queue overlap `0`이 된다
4. 이전 NAS no-probe must-hide main family가 queue에서 빠지고, 다음 main backlog가 더 선명해진다

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 reopen point는 아래다.

- `BTCUSD + lower_rebound_confirm + energy_soft_block + execution_soft_blocked + no_probe`
- `BTCUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`

즉 NAS no-probe must-hide leakage를 닫은 뒤에는
BTC energy-soft-block must-show / must-block backlog가 다음 메인축으로 올라온다.
