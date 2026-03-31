# Product Acceptance PA1 NAS Upper-Reject Probe Forecast Wait Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

confirm no-probe hidden 축을 닫은 뒤,
곧바로 남은 upper-reject probe forecast family를
`WAIT + wait_check_repeat` 계약으로 올렸다.

target family:

- `NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`

관련 문서:

- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_forecast_wait_display_contract_delta_ko.md)

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
`nas_upper_reject_probe_forecast_wait_as_wait_checks` policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = SELL`
- `observe_reason_allow = upper_reject_probe_observe`
- `blocked_by_allow = forecast_guard`
- `action_none_allow = probe_not_promoted`
- `probe_scene_allow = nas_clean_confirm_probe`
- `require_probe_scene_present = true`
- `stage_allow = PROBE`

### 3-2. common modifier wait contract 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
target family가 걸리면 아래 surface를 유지하도록 맞췄다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_forecast_wait_as_wait_checks`
- `blocked_display_reason = forecast_guard`

### 3-3. PA0 accepted wait-check allow-list 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`nas_upper_reject_probe_forecast_wait_as_wait_checks`를 accepted wait-check relief로 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
63 passed
72 passed
15 passed
```

고정된 테스트:

- [test_build_consumer_check_state_keeps_nas_upper_reject_probe_forecast_wait_visible_as_wait](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_resolve_effective_consumer_check_state_keeps_nas_upper_reject_probe_forecast_wait_visible](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_renders_nas_upper_reject_probe_forecast_wait_relief_as_neutral_wait_checks](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_nas_upper_reject_probe_forecast_wait_relief_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. live/runtime 확인

`main.py`를 재시작한 뒤 fresh recent row를 확인했다.

- restart log: [cfd_main_restart_20260331_205251.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_205251.out.log)
- restart err log: [cfd_main_restart_20260331_205251.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_205251.err.log)

post-restart recent 240-row 기준 exact target family recurrence는 `0`이었다.
즉 live에서 바로 새 wait-contract row를 다시 잡진 못했다.

대신 representative historical row `2026-03-31T20:42:33`를 current build 해석으로 보면
아래 contract가 맞다.

- `check_display_ready = True`
- `check_stage = PROBE`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_upper_reject_probe_forecast_wait_as_wait_checks`
- `blocked_display_reason = forecast_guard`

## 6. PA0 refreeze 해석

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-03-31T20:55:11`

target family delta:

- `must_hide 9 -> 7`

이 값이 바로 `0`이 되지 않은 이유는
PA0 freeze가 row에 이미 기록된 `consumer_check_state_v1`를 기준으로 보기 때문이다.
즉 old backlog row에는 아직 새 chart wait contract가 기록돼 있지 않다.

그래서 이번 축의 결론은 아래처럼 읽는 것이 맞다.

```text
코드와 테스트는 끝났다.
current-build replay도 wait contract를 확인했다.
하지만 exact fresh row recurrence가 아직 없어
PA0 queue에서는 old backlog 7개가 남아 있다.
```

## 7. 다음 reopen point

다음 upper-reject must-hide main family는 아래다.

- `NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
