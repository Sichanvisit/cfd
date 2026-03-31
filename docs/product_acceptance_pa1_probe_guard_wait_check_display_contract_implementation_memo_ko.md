# Product Acceptance PA1 Probe-Guard Wait Check Display Contract Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`probe_scene + guard + probe_not_promoted`
structural family를
`leakage suppression` 대상으로 더 누르지 않고,
`WAIT + repeated checks`
chart contract로 올리는 구현을 묶었다.

관련 기준 문서:

- [product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_fresh_runtime_followup_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md)

## 2. 직접 건드린 owner 범위

이번 단계에서 직접 건드린 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 일부러 건드리지 않은 owner:

- entry / wait / hold / exit acceptance 로직 전체
- symbol override policy 전체 재정리
- cadence suppression family 재설계

## 3. 실제 구현 내용

### 3-1. policy에 chart wait relief contract 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
아래 policy axis를 추가했다.

- `display_modifier.chart_wait_reliefs.probe_guard_wait_as_wait_checks`

이 policy는 아래 경계를 묶는다.

- `observe_reason`
- `blocked_by`
- `action_none_reason = probe_not_promoted`
- `probe_scene required`
- `stage = OBSERVE`
- `event_kind_hint = WAIT`
- `display_mode = wait_check_repeat`
- `display_reason = probe_guard_wait_as_wait_checks`

즉 이번 단계는 hard suppression이 아니라
chart 표현 계약을 policy 축으로 올린 것이다.

### 3-2. consumer_check_state에 chart hint surface 추가

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서는
modifier 계산 중 위 policy를 읽어
아래 chart hint surface를 채우게 했다.

- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

대표 적용 family:

- `BTCUSD`
- `middle_sr_anchor_required_observe`
- `middle_sr_anchor_guard`
- `probe_not_promoted`
- `btc_lower_buy_conservative_probe`

적용 시 의미:

- `check_display_ready`는 유지
- `check_stage = OBSERVE`는 유지
- `display_repeat_count`는 유지
- 차트에서만 `WAIT + repeated checks`로 읽히게 한다

late suppression으로 final display가 꺼지면
chart hint도 함께 비우도록 정리했다.

### 3-3. chart_painter가 neutral wait repeated checks를 렌더

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 에서는
아래를 정리했다.

1. `chart_event_kind_hint = WAIT`를 stage 번역보다 먼저 읽는다
2. neutral wait event에서도 explicit `repeat_count`를 존중한다
3. neutral marker pair를 repeat index 기준으로 반복 렌더한다
4. event signature에 chart hint/display mode를 포함한다

즉 이제 이 family는 chart에서
방향성 `BUY/SELL` 강조가 아니라
중립 `WAIT` 표기와 여러 check로 남는다.

### 3-4. PA0 script가 accepted wait-check relief를 seed에서 제외

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py) 는
`consumer_check_state_v1` nested payload에서 아래 필드를 읽도록 확장했다.

- `chart_event_kind_hint`
- `chart_display_mode`
- `chart_display_reason`

그리고 아래 helper를 추가했다.

- accepted wait-check relief 판별 helper

판별 조건:

- `display_ready = True`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

이 helper가 참이면 아래 queue에서 skip한다.

- `must-show missing`
- `must-hide leakage`
- `must-block`

## 4. quick verification

단위 테스트와 synthetic replay 기준으로
fresh contract는 아래처럼 동작한다.

1. consumer state

- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_score = 0.82`
- `display_repeat_count = 2`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = probe_guard_wait_as_wait_checks`

2. chart history / overlay

- final history event kind = `WAIT`
- side = `""`
- repeat_count = `2`
- neutral marker pair가 repeat index까지 포함해 반복 생성된다

즉 "기다림인 차트에 기다림인 표기와 체크 여러 개" 방향이
코드 surface로는 연결된 상태다.

## 5. refreeze 결과와 해석

코드 반영 뒤
[product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)
을 다시 얼렸고,
직전 snapshot은
[product_acceptance_pa0_baseline_snapshot_20260331_155445.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_155445.json)
으로 보존했다.

결과 요약:

- 이전 snapshot generated_at = `2026-03-31T15:54:45`
- 이번 refreeze generated_at = `2026-03-31T16:19:38`
- `must_show_missing_count = 15`
- `must_hide_leakage_count = 15`
- `must_block_candidate_count = 12`

즉 baseline 숫자는 그대로였다.

하지만 이건 구현이 안 먹은 것이 아니라,
recent stored row가 아직 old contract라는 뜻이다.

실제 확인 결과:

- `BTCUSD` recent 120 row 중 hint row `0`
- `NAS100` recent 120 row 중 hint row `0`
- `XAUUSD` recent 120 row 중 hint row `0`

즉 `entry_decisions.csv` recent window에는
새 `chart_event_kind_hint / chart_display_mode / chart_display_reason`
가 기록된 row가 아직 없다.

그래서 PA0 script alignment는 이미 들어가 있지만,
artifact는 아직 그 혜택을 받지 못한다.

## 6. 테스트

실행한 테스트:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
45 passed
60 passed
3 passed
```

추가로 고정된 확인 포인트:

- consumer wait hint surface가 정확히 남는지
- painter가 neutral wait repeated checks를 실제로 렌더하는지
- PA0 script가 accepted wait-check relief를 seed queue에서 빼는지

## 7. 이번 단계에서 일부러 안 한 것

아래는 이번 단계에서 일부러 보류했다.

- fresh runtime row 생성 자체
- entry / wait / hold / exit acceptance 로직 수정
- must-show / must-hide 전체 heuristic 재설계
- probe-scene structural family score ladder 재튜닝

즉 이번 단계는
`contract wiring + painter rendering + PA0 alignment`
까지를 닫은 구현이다.

## 8. 다음 reopen point

다음 순서는 아래가 가장 자연스럽다.

1. 새 contract가 기록된 fresh runtime row를 조금 더 쌓는다
2. PA0 baseline을 다시 얼린다
3. accepted wait-check relief family가 problem seed queue에서 실제로 빠졌는지 본다
4. 그래도 남는 queue만 다시 PA1 follow-up 대상으로 좁힌다

## 9. 한 줄 요약

```text
이번 PA1 하위 구현으로
probe_scene + guard + probe_not_promoted structural family는
코드상에서 이미 WAIT + repeated checks chart contract로 연결됐고,
이제 남은 건 fresh runtime row가 쌓인 뒤 PA0 artifact가 그 계약을 따라오게 확인하는 일이다.
```

## 10. fresh runtime follow-up

contract 연결 이후 fresh runtime row가 실제로 더 쌓인 상태를 확인한 follow-up은 아래 문서에 남긴다.

- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_fresh_runtime_followup_ko.md)

## 11. post-runtime-restart follow-up

live `cfd main.py`를 새 코드로 재시작한 뒤,
actual WAIT + repeated checks row 생성과
PA0 queue 제외 여부를 다시 확인한 follow-up은 아래 문서에 남긴다.

- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_post_runtime_restart_followup_ko.md)

## 12. linked XAU follow-up

BTC probe-guard wait-check contract를 닫은 뒤
같은 PA1 chart-acceptance 축에서 이어진 XAU mixed guard-wait visibility relief는 아래 문서 체인으로 남긴다.

- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md)
