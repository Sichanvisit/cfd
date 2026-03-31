# Product Acceptance PA1 NAS Outer-Band Probe Guard Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`NAS100 + outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + nas_clean_confirm_probe`
family 안에서 `probe_against_default_side` 때문에 hidden으로 떨어지던 row를
다시 `WAIT + wait_check_repeat` contract로 올렸다.

관련 문서:

- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

## 2. 변경 owner

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. against-default-side structural wait relief 추가

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에
`nas_outer_band_probe_against_default_side_wait_relief`를 추가했다.

고정 조건:

- `symbol = NAS100`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `entry_probe_plan_v1.reason = probe_against_default_side`

### 3-2. display_blocked 예외 연결

기존에는 `probe_against_default_side`가 있으면 structural wait도 hidden으로 떨어졌는데,
이번엔 target family에서는 그 예외를 풀었다.

결과적으로 current-build surface는 아래처럼 유지된다.

- `check_display_ready = True`
- `check_stage = OBSERVE`
- `blocked_display_reason = outer_band_guard`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
68 passed
75 passed
18 passed
```

고정된 테스트:

- [test_build_consumer_check_state_keeps_nas_outer_band_probe_against_default_side_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_nas_outer_band_probe_against_default_side_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_nas_outer_band_probe_guard_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_nas_outer_band_probe_guard_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. live/runtime 확인

`main.py`를 재시작했다.

- restart log: [cfd_main_restart_20260331_214248.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_214248.out.log)
- restart err log: [cfd_main_restart_20260331_214248.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_214248.err.log)

patch 전 recent row 분석으로 아래가 확인됐다.

- visible row: `probe_forecast_not_ready` -> `WAIT + probe_guard_wait_as_wait_checks`
- hidden row: `probe_against_default_side` -> `BLOCKED + hidden`

patch 후 current-build 해석은 against-default-side row도
`WAIT + probe_guard_wait_as_wait_checks`로 올라가는 것을 확인했다.

다만 post-restart recent 120-row 안에는 exact target family가 아직 다시 안 들어왔다.
즉 live direct fresh row 증빙은 아직 대기 상태다.

## 6. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_214406.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_214406.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T21:43:43`

현재 baseline 해석:

- `must_hide = 0`
- `must_show = 15`
- `must_block = 12`

그리고 남은 `must_show/must_block`는 여전히 target outer-band family가 채우고 있다.

이 값이 바로 줄지 않은 이유는
post-restart recent 120-row에 exact target family fresh recurrence가 아직 없고,
latest queue가 여전히 old hidden backlog를 포함하고 있기 때문이다.

## 7. 결론

이번 축의 결론은 아래와 같다.

```text
outer-band against-default-side hidden path는 current build에서 wait checks로 복구됐다.
회귀도 모두 통과했다.
다만 baseline queue 감소를 확정하려면 fresh exact row가 한 번 더 필요하다.
```

## 8. fresh runtime follow-up

이후 exact target family fresh row가 실제로 다시 쌓인 다음
PA0 baseline을 다시 얼려서 live queue 감소까지 확인했다.

follow-up 문서:

- [product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

핵심 결과:

- fresh exact row 시각:
  - `2026-03-31T21:48:30`
  - `2026-03-31T21:48:42`
- target family delta:
  - `must_show 15 -> 8`
  - `must_block 12 -> 8`

즉 이 축은 이제 current-build replay 수준이 아니라
live runtime fresh row와 PA0 queue 감소까지 확인된 상태다.
