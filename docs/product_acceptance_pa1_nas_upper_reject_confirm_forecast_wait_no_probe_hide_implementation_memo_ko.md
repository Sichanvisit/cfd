# Product Acceptance PA1 NAS Upper-Reject Confirm Forecast Wait No-Probe Hide Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe`
family를 `accepted hidden suppression`으로 정리했다.

관련 문서:

- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_confirm_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_confirm_forecast_wait_no_probe_hide_delta_ko.md)

## 2. 변경 owner

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 3. 구현 내용

### 3-1. hide policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`nas_upper_reject_wait_hide_without_probe` policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = SELL`
- `observe_reason_allow = upper_reject_confirm`
- `blocked_by_allow = forecast_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = true`
- `require_importance_source_absent = true`

### 3-2. common modifier suppression 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
target family가 걸리면 아래 surface로 내리도록 맞췄다.

- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_reject_wait_hide_without_probe`

### 3-3. painter fallback 차단

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에
위 reason을 hidden suppression set으로 추가했다.

### 3-4. PA0 hidden suppression allow-list 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
`nas_upper_reject_wait_hide_without_probe`를 accepted hidden suppression으로 추가했다.

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

- [test_build_consumer_check_state_hides_nas_upper_reject_wait_without_probe_scene](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_skips_hidden_nas_upper_reject_wait_without_probe](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_hidden_nas_upper_reject_wait_without_probe_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. live/runtime 확인

`main.py`를 새 코드로 재시작했다.

- restart log: [cfd_main_restart_20260331_205251.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_205251.out.log)
- restart err log: [cfd_main_restart_20260331_205251.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_205251.err.log)

post-restart fresh row에서는 exact target family recurrence가 `0`이었다.
그래서 live 증빙은 historical representative row를 current build에 replay한 결과로 닫았다.

representative row:

- `time = 2026-03-31T20:26:58`
- expected current-build surface = `display_ready=False + stage=OBSERVE + modifier_primary_reason=nas_upper_reject_wait_hide_without_probe`

## 6. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_205531.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_205531.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T20:55:11`

핵심 변화:

- `NAS100 + upper_reject_confirm + forecast_guard + observe_state_wait + no_probe`
  - `must_hide 5 -> 0`

total `must_hide = 15`가 그대로인 이유는 실패가 아니라
같은 upper-reject 축의 probe family가 자리를 채웠기 때문이다.

current upper-reject must-hide composition:

- `7 = NAS100 + upper_reject_probe_observe + forecast_guard + probe_not_promoted + nas_clean_confirm_probe`
- `8 = NAS100 + upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`

즉 이번 confirm no-probe 축은 닫혔고,
이제 남은 upper-reject backlog가 더 선명하게 분리됐다.
