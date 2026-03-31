# Product Acceptance PA1 NAS Upper-Reject Probe Promotion Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
family를 `WAIT + wait_check_repeat` 계약으로 올렸다.

관련 문서:

- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_promotion_wait_display_contract_delta_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. wait-check policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`nas_upper_reject_probe_promotion_wait_as_wait_checks` policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = SELL`
- `observe_reason_allow = upper_reject_probe_observe`
- `blocked_by_allow = probe_promotion_gate`
- `action_none_allow = probe_not_promoted`
- `probe_scene_allow = nas_clean_confirm_probe`
- `require_probe_scene_present = true`
- `stage_allow = PROBE`

### 3-2. common modifier wait contract 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
target family를 `WAIT + wait_check_repeat`로 surface 하도록 연결했다.

대표 current-build surface:

- `check_display_ready = True`
- `check_stage = PROBE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_promotion_wait_as_wait_checks`
- `blocked_display_reason = probe_promotion_gate`

### 3-3. PA0 wait relief allow-list 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`nas_upper_reject_probe_promotion_wait_as_wait_checks`를 accepted wait-check relief로 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
65 passed
73 passed
16 passed
```

고정된 테스트:

- [test_build_consumer_check_state_keeps_nas_upper_reject_probe_promotion_wait_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_nas_upper_reject_probe_promotion_wait_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_nas_upper_reject_probe_promotion_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_nas_upper_reject_probe_promotion_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. live/runtime 확인

`main.py`를 재시작했다.

- restart log: [cfd_main_restart_20260331_211735.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_211735.out.log)
- restart err log: [cfd_main_restart_20260331_211735.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_211735.err.log)

recent 240-row 기준 exact target family는 `5`건 잡혔지만,
이 row들은 모두 restart 전 old rows였고
`chart_event_kind_hint / chart_display_mode / chart_display_reason`는 비어 있었다.

post-restart fresh exact recurrence는 `0`이었다.

대신 representative current-build replay는 아래 contract를 확인했다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `blocked_display_reason = probe_promotion_gate`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_promotion_wait_as_wait_checks`

## 6. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_211930.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_211930.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T21:18:37`

핵심 변화:

- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
  - `must_hide 8 -> 7`

이 값이 바로 `0`이 되지 않은 이유는
fresh exact row가 아직 새 contract로 다시 기록되지 않았기 때문이다.
현재 남아 있는 `7`은 old backlog로 읽는 것이 맞다.

동시에 must-hide composition은 아래처럼 바뀌었다.

- `8 = NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
- `7 = NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

즉 이번 축을 넣자
다음 NAS must-hide 메인축이 `upper_break_fail_confirm`으로 더 또렷해졌다.
