# Product Acceptance PA1 BTC Outer-Band Probe Guard Wait Repeat Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 하위축에서 한 일

이번 PA1 하위축에서는
`BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
family를 다시 열었다.

이번 문제는 새 contract를 만드는 일이 아니라,
이미 build 단계에서 살아 있는
`WAIT + wait_check_repeat + probe_guard_wait_as_wait_checks`
contract를 resolve 단계의 cadence suppression이 다시 지우는 문제를 정리하는 일이었다.

관련 문서:

- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md)

## 2. 변경 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. resolve cadence relief 추가

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`btc_outer_band_probe_guard_wait_repeat_relief`를 추가했다.

고정 조건:

- `symbol = BTCUSD`
- `side = BUY`
- `stage = OBSERVE`
- `display_ready = True`
- `semantic_origin_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

이 relief가 켜지면 repeated row라도
`btc_lower_structural_cadence_suppressed`
에서 제외된다.

### 3-2. build contract는 그대로 유지

이번 축은 새 display reason을 추가하지 않았다.

target family는 계속 아래 contract를 그대로 쓴다.

- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

즉 build는 그대로 두고,
late/runtime resolve만 좁게 풀었다.

## 4. 회귀 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
68 passed
76 passed
19 passed
```

고정한 테스트:

- [test_build_consumer_check_state_marks_btc_structural_rebound_as_double_display](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_repeated_btc_structural_observe_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_btc_outer_band_probe_guard_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_btc_outer_band_probe_guard_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. current-build replay 확인

representative current-build replay 결과는 아래와 같다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = outer_band_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`
- `display_repeat_count = 2`
- `display_strength_level = 5`
- `display_score = 0.82`

즉 이번 축은 current-build 기준으로
`repeated BTC structural wait가 cadence suppression에 다시 죽지 않는다`
까지 확인됐다.

## 6. live/runtime 확인

`main.py`를 재시작했다.

- restart log: [cfd_main_restart_20260331_220633.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_220633.out.log)
- restart err log: [cfd_main_restart_20260331_220633.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_220633.err.log)

post-restart recent watch를 약 90초 진행했지만,
exact target family fresh recurrence는 이번 watch window 안에는 다시 들어오지 않았다.

즉 이번 축은
`fresh exact row live 직접 증빙`
은 아직 없고,
current-build replay와 PA0 queue delta로 먼저 확인된 상태다.

## 7. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_220633.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_220633.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T22:10:15`

target family delta:

- `must_show 5 -> 0`
- `must_block 2 -> 0`

total summary는 그대로다.

- `must_show_missing_count = 15 -> 15`
- `must_block_candidate_count = 12 -> 12`
- `must_hide_leakage_count = 0 -> 0`

즉 이번 결과는
`전체 queue가 줄었다`가 아니라
`BTC outer-band target family는 queue에서 빠졌고, 다른 family가 자리를 채웠다`
로 해석하는 것이 맞다.

## 8. 남은 queue composition

after latest main residue:

- `must_show`
  - `12 = XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
  - `1 = BTCUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
  - `1 = BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait +`
- `must_block`
  - `9 = NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
  - `1 = XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
  - `1 = BTCUSD + lower_rebound_probe_observe + forecast_guard + probe_not_promoted + btc_lower_buy_conservative_probe`
  - `1 = BTCUSD + outer_band_reversal_support_required_observe + outer_band_guard + observe_state_wait +`

즉 다음 메인축은 더 이상 `BTC outer_band + probe_not_promoted`가 아니다.

## 9. 결론

이번 축의 결론은 아래와 같다.

```text
BTC outer-band structural wait family는 build에서 이미 맞았고,
실제 문제는 resolve cadence suppression이었다.
그 suppression을 좁게 풀었고,
PA0 refreeze에서는 target family must_show 5 -> 0, must_block 2 -> 0까지 확인됐다.
```

## 10. 다음 reopen point

이제 자연스러운 다음 후보는 아래 둘이다.

1. `XAUUSD + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait +`
2. `NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
