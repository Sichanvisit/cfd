# Product Acceptance PA1 BTC Lower Rebound Probe Energy Soft Block Wait Visibility Relief Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 이 문서의 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + lower_rebound_probe_observe + energy_soft_block + execution_soft_blocked + btc_lower_buy_conservative_probe`
family를 왜 `hidden blocked scene`이 아니라
`WAIT + repeated checks`로 보여줘야 하는지 고정하는 상세 reference다.

관련 기준 문서:

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 문제 family

대상 family는 아래 조건이 동시에 붙는 BTC lower rebound probe scene이다.

- `symbol = BTCUSD`
- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = btc_lower_buy_conservative_probe`

이 family는 recent PA0 queue에서 다음처럼 남아 있었다.

- `must_show_missing 15/15`
- `must_block_candidates 12/12`

즉 차트에는 거의 안 보이는데, 내부 의미는 완전히 빈 장면도 아닌 상태였다.

## 3. 왜 숨김이 아니라 wait-style visibility인가

이 family는 no-probe leakage와 다르다.

- probe scene이 분명히 있다
- probe plan이 `ready_for_entry = true`까지 올라온 row가 반복된다
- scene importance도 낮지 않다
- 다만 `energy_soft_block`가 걸려 있어서 entry만 못 가는 상태다

즉 의미는 아래에 가깝다.

```text
아직 들어가면 안 되지만,
계속 체크해야 하는 구조적 wait scene
```

그래서 이 family를 완전히 숨기면
chart acceptance 기준에서는 “중요한 구조적 대기”가 사라지고,
product acceptance 기준에서는 must-show / must-block queue에 계속 쌓이는 왜곡이 남는다.

## 4. 목표 contract

이 family의 목표 chart contract는 아래와 같다.

- 진입 신호 승격은 하지 않는다
- directional BUY marker로 밀어붙이지 않는다
- 대신 `WAIT + wait_check_repeat`로 보이게 한다
- blocked 이유는 `energy_soft_block`로 surface에 남긴다

대표 fresh row에서 기대한 nested contract:

- `check_stage = PROBE`
- `check_display_ready = True`
- `display_score ~= 0.91`
- `display_repeat_count = 3`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_rebound_probe_energy_soft_block_as_wait_checks`

## 5. 구현 방향

구현 방향은 XAU energy-soft-block 하위축과 같은 축을 따른다.

1. chart flow policy에 BTC wait relief policy를 추가한다
2. probe-ready but blocked blanket hide 예외로 이 family를 빼낸다
3. blocked reason을 carry해서 “왜 기다림인지” surface에 남긴다
4. PA0 baseline freeze script에서 accepted wait relief로 분류한다
5. unit test, live restart, fresh row verify, PA0 refreeze로 닫는다

## 6. 이 하위축에서 하지 않는 것

이번 하위축에서 일부러 하지 않는 것은 아래다.

- NAS no-probe leakage 수정
- XAU old hidden backlog 정리
- entry / wait / hold / exit acceptance 수정
- broad threshold retune

즉 이번 문서는 BTC lower rebound energy-soft-block mirror family 하나만 닫는 상세 기준이다.

## 7. 완료 기준

이 하위축의 완료 기준은 아래다.

1. fresh BTC row에서 nested state가 실제로 `WAIT + wait_check_repeat`로 찍힌다
2. 같은 fresh row가 PA0 queue에서 빠진다
3. total queue가 그대로여도, 그 이유가 old hidden backlog라는 해석이 가능해야 한다

## 8. 다음 reopen point

이 하위축을 닫고 나면 다음 PA1 메인 reopen point는 아래다.

- `NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait + no_probe`

즉 BTC mirror family를 닫은 뒤에는 must-hide leakage 메인축이 NAS no-probe family로 더 선명해진다.
