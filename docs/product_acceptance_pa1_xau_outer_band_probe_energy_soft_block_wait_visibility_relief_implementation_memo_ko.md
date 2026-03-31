# Product Acceptance PA1 XAU Outer-Band Probe Energy Soft-Block Wait Visibility Relief Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 하위축에서 한 일

이번 PA1 하위축에서는
`XAUUSD + outer_band_reversal_support_required_observe + energy_soft_block + execution_soft_blocked + xau_upper_sell_probe`
family를 `WAIT + repeated checks` contract로 올렸다.

이 family는 probe scene이 이미 있고 execution soft block 때문에 막힌 상태라서,
숨길 대상이라기보다 `지켜봐야 하는 blocked probe wait`로 surface하는 편이 맞다고 판단했다.

관련 문서:

- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. policy entry 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`xau_outer_band_probe_energy_soft_block_as_wait_checks`를 추가했다.

조건:

- `symbol = XAUUSD`
- `side = SELL`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = energy_soft_block`
- `action_none_reason = execution_soft_blocked`
- `probe_scene_id = xau_upper_sell_probe`
- `stage_allow = PROBE, BLOCKED`

반환:

- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = xau_outer_band_probe_energy_soft_block_as_wait_checks`

### 3-2. build-stage wait relief

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`xau_outer_band_probe_energy_wait_relief`를 추가하고,
target family가 `probe_ready_but_blocked` blanket hide로 떨어지지 않게 조정했다.

### 3-3. blocked reason carry / PA0 skip

same file에서 resolve surface가 `blocked_display_reason`를 carry할 수 있게 열었고,
[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
새 display reason을 accepted wait-check 이유로 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
71 passed
78 passed
21 passed
```

고정된 테스트:

- [test_build_consumer_check_state_keeps_xau_outer_band_probe_energy_soft_block_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_xau_outer_band_probe_energy_soft_block_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_xau_outer_band_probe_energy_soft_block_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_xau_outer_band_probe_energy_soft_block_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. representative current-build replay

latest representative replay (`2026-03-31T22:38:53`)에서는 아래처럼 바뀌었다.

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `check_side = SELL`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = xau_outer_band_probe_energy_soft_block_as_wait_checks`
- `display_repeat_count = 1`
- `display_strength_level = 5`
- `display_score = 0.75`

resolve replay에서도:

- `display_ready = True`
- `stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_display_reason = xau_outer_band_probe_energy_soft_block_as_wait_checks`

가 유지됐다.

## 6. live/runtime 확인

cfd `main.py`는 아래 로그 기준으로 재시작했다.

- out log: [cfd_main_restart_20260331_230452.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_230452.out.log)
- err log: [cfd_main_restart_20260331_230452.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_230452.err.log)

post-restart fresh watch에서:

- cutoff 이후 exact target row = `0`
- 새 reason이 찍힌 fresh exact row도 `0`

즉 이번 축은 `fresh exact row 증빙`보다
`current-build replay + PA0 queue turnover`
근거가 더 강한 상태로 기록한다.

## 7. 판단

이번 축은 구현 자체는 닫혔다고 본다.

이유:

- tests 전부 통과
- representative replay가 WAIT contract로 바뀜
- PA0 queue에서 target family가 `must_show / must_block` main residue에서 빠짐

다만 live fresh exact row 증빙은 아직 다시 쌓이지 않았으므로,
다음 follow-up에서는 이 점을 계속 분리해서 봐야 한다.
