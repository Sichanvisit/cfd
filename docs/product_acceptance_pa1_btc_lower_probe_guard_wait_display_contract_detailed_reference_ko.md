# Product Acceptance PA1 BTC Lower-Probe Guard Wait Display Contract Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는 PA1 chart acceptance 하위축 중
`BTCUSD + lower_rebound_probe_observe + {forecast_guard | barrier_guard} + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 `must-show / must-hide / must-block` 문제 queue에서 제거하기 위해,
이 family를 `WAIT + wait_check_repeat` contract로 올린 이유와 구현 경계를 고정한다.

관련 문서:

- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)

## 2. 문제 family

이번 축의 target family는 두 갈래였지만, 둘 다 같은 lower-rebound probe family로 묶는다.

- `symbol = BTCUSD`
- `observe_reason = lower_rebound_probe_observe`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `blocked_by = forecast_guard`
- `blocked_by = barrier_guard`

직전 PA0 baseline 기준으로 이 family는 아래처럼 queue를 채우고 있었다.

- `forecast_guard` family: `must_show_missing = 8`
- `forecast_guard` family: `must_block_candidates = 6`
- `barrier_guard` family: `must_hide_leakage = 15`

## 3. 해석

이 family의 핵심 질문은 아래였다.

```text
BTC lower rebound probe가 이미 구조적으로는 보이는데
forecast_guard 또는 barrier_guard 때문에 아직 promote되지 않은 상태를
차트에서 숨길 것인가, WAIT 체크 surface로 보여줄 것인가?
```

이번 축의 결론은 `WAIT 체크 surface로 보여준다`이다.

이유:

- `probe_scene_id = btc_lower_buy_conservative_probe`가 이미 붙어 있다.
- `probe_not_promoted`는 진입 금지보다는 추가 확인 대기 성격이 강하다.
- `forecast_guard`와 `barrier_guard`는 현재 진입만 막는 guard이지, 구조 인지 자체를 숨길 이유는 아니다.
- 이전 lower-probe promotion 축과 lower-probe energy-soft-block 축도 같은 방향으로 정리되었다.

즉 이 family는 `leakage`가 아니라 `guarded wait probe`로 보는 것이 맞다.

## 4. representative replay 기준

대표 row:

- `2026-04-01T00:00:12` (`forecast_guard`)
- `2026-04-01T00:00:46` (`barrier_guard`)

current build replay 결과:

- `check_display_ready = True`
- `entry_ready = False`
- `check_side = BUY`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard` 또는 `barrier_guard`
- `display_importance_tier = medium`
- `display_importance_source_reason = btc_lower_recovery_start`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_probe_guard_wait_as_wait_checks`

resolve replay에서도 같은 contract가 유지되어 cadence suppression으로 다시 숨겨지지 않았다.

## 5. 목표 contract

이번 축에서 고정하는 목표 contract는 아래와 같다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = forecast_guard | barrier_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = btc_lower_probe_guard_wait_as_wait_checks`

즉 `guarded lower rebound probe`를 directional ready가 아니라
`WAIT + repeated checks`로 표기하는 것이 목표다.

## 6. 구현 방향

1. [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에 `btc_lower_probe_guard_wait_as_wait_checks` policy를 추가한다.
2. [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에 `btc_lower_probe_guard_wait_relief`를 추가한다.
3. same file에서 `blocked_display_reason = forecast_guard | barrier_guard` carry를 보장한다.
4. resolve 단계에서 `btc_lower_probe_cadence_suppressed`가 새 contract를 다시 숨기지 않도록 `btc_lower_probe_guard_wait_repeat_relief`를 둔다.
5. [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에 accepted wait-check reason으로 등록한다.

## 7. 이번 축에서 하지 않는 것

- BTC middle-anchor no-probe residue 정리
- BTC upper sell probe residue 정리
- XAU mixed energy-soft-block residue 정리
- entry / hold / exit acceptance 조정

## 8. 완료 기준

1. representative replay에서 target family가 `WAIT + wait_check_repeat`로 보인다.
2. resolve replay에서도 같은 contract가 유지된다.
3. PA0 baseline script가 이 reason을 problem seed queue에서 제외한다.
4. live exact recurrence가 없더라도 delta 문서에 `replay 완료 + queue turnover로 닫힘` 상태를 명시한다.
