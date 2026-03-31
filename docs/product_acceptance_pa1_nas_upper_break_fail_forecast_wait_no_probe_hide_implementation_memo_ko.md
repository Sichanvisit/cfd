# Product Acceptance PA1 NAS Upper-Break-Fail Forecast Wait No-Probe Hide Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`NAS100 + upper_break_fail_confirm + forecast_guard + observe_state_wait + no_probe`
family를 `accepted hidden suppression`으로 정리했다.

관련 문서:

- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_break_fail_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_break_fail_forecast_wait_no_probe_hide_delta_ko.md)

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
`nas_upper_break_fail_wait_hide_without_probe` policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = SELL`
- `observe_reason_allow = upper_break_fail_confirm`
- `blocked_by_allow = forecast_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = true`
- `require_importance_source_absent = true`

### 3-2. common modifier suppression 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)에서
target family를 hidden suppression으로 내리도록 연결했다.

current-build representative surface:

- `check_stage = OBSERVE`
- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_break_fail_wait_hide_without_probe`

### 3-3. painter / PA0 연결

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에
새 hidden suppression reason을 추가했고,
[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에도
accepted hidden suppression allow-list를 추가했다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
66 passed
74 passed
17 passed
```

고정된 테스트:

- [test_build_consumer_check_state_hides_nas_upper_break_fail_wait_without_probe_scene](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_add_decision_flow_overlay_skips_hidden_nas_upper_break_fail_wait_without_probe](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_pa0_baseline_skips_hidden_nas_upper_break_fail_wait_without_probe_from_problem_seed_queues](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

## 5. live/runtime 확인

`main.py`를 재시작했다.

- restart log: [cfd_main_restart_20260331_212604.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_212604.out.log)
- restart err log: [cfd_main_restart_20260331_212604.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_212604.err.log)

recent 240-row 기준 exact target family는 `5`건 잡혔지만,
이 row들은 모두 restart 전 old rows였고 chart contract는 비어 있었다.

post-restart fresh exact recurrence는 `0`이었다.

대신 current-build replay는 아래처럼 맞게 내려갔다.

- `check_stage = OBSERVE`
- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_break_fail_wait_hide_without_probe`

## 6. PA0 refreeze 해석

비교 기준:

- before snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_212752.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_212752.json)
- after latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest generated_at:

- `2026-03-31T21:27:08`

핵심 해석:

- target family `must_hide 8 -> 8`
- total `must_hide 15 -> 13`

즉 이번 축은 `코드/테스트/current-build replay`는 완료됐지만,
target family 자체는 fresh exact row가 아직 새 contract로 다시 기록되지 않아
queue에서 바로 줄지 않았다.

반면 recent window 이동으로
`NAS upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
는 `7 -> 5`로 줄었다.

## 7. 결론

이번 축의 결론은 아래와 같다.

```text
upper_break_fail no-probe hide contract 코드는 준비됐다.
current-build replay도 맞다.
하지만 exact fresh recurrence가 아직 없어 target queue 8은 그대로 남아 있다.
지금 다음 PA1 메인축은 NAS outer-band must-show/must-block backlog다.
```
