# Product Acceptance Common State-Aware Display Modifier v1 Casebook Review Follow-Up

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 PA1 1차 구현 직후,
PA0 latest artifact를 다시 읽고 raw row replay 기준으로
무엇이 아직 살아 있는 문제인지 좁힌 follow-up memo다.

즉 이번 문서는 아래를 기록한다.

- static casebook artifact에서 보이는 seed
- 같은 raw row를 현재 `build_consumer_check_state_v1(...)`로 다시 태웠을 때의 결과
- 그래서 실제로 남은 live gap이 무엇이었는지
- 그 gap을 어떤 공통 modifier rule로 닫았는지

## 2. 이번 follow-up에서 확인한 핵심

이번 review에서 가장 중요한 확인은 아래였다.

```text
PA0 latest artifact는 entry_decisions.csv 안에 이미 기록된 consumer_check_state_v1을 읽는다.
즉 코드가 바뀐 직후에는 artifact seed와 현재 build-time 재계산 결과가 잠시 어긋날 수 있다.
```

따라서 must-show / must-hide seed는 그대로 참고하되,
실제 수정 대상을 고를 때는 raw row replay로 현재 코드를 다시 태워보는 확인이 필요했다.

## 3. raw row replay로 다시 확인한 결과

### 3-1. 이미 current build에서 살아난 must-show missing

아래 family는 static artifact에서는 hidden seed로 남아 있었지만,
같은 raw row를 current build로 다시 태우면 이미 visible로 복원됐다.

1. `BTCUSD`

- `middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`

current replay 결과:

- `check_side = BUY`
- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_importance_source_reason = btc_structural_rebound`
- `display_importance_tier = medium`
- `display_repeat_count = 2`

2. `XAUUSD`

- `middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = xau_second_support_buy_probe`

current replay 결과:

- `check_side = BUY`
- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_importance_source_reason = xau_second_support_reclaim`
- directional visibility가 다시 살아 있음

즉 PA1 1차 구현 이후에는
probe wait structural reclaim family의 hidden 문제는 current build 기준으로 상당 부분 정리된 상태로 봐도 됐다.

### 3-2. 실제로 남아 있던 live gap

반대로 아래 family는 current build replay에서도 여전히 directional leakage가 남아 있었다.

- `symbol = BTCUSD`
- `observe_reason` prefix = `conflict_`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`

대표 raw row replay 결과:

- `check_side = BUY`
- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_score = 0.75`
- `display_repeat_count = 1`

즉 PA1 1차 구현에서 이미
예전 embedded state의 `PROBE / 0.82 / 2-check` 누수는 `OBSERVE / 0.75 / 1-check`로 내려왔지만,
casebook 관점에서는 여전히 `directional visibility`가 남아 있는 상태였다.

## 4. 그래서 이번 follow-up에서 실제로 한 일

이번 follow-up 구현에서는
`common_state_aware_display_modifier_v1` policy에
공통 `conflict soft cap`을 추가했다.

추가한 policy 축:

- `display_modifier.soft_caps.conflict_wait_hide`

적용 조건:

- `observe_reason`가 `conflict_` prefix를 가질 때
- `blocked_by`가 structural/forecast guard family일 때
- `action_none_reason = observe_state_wait`
- probe scene이 비어 있을 때
- entry-ready가 아닌 directional candidate일 때

적용 효과:

- `effective_display_ready = False`
- `modifier_primary_reason = conflict_wait_hide`
- `modifier_stage_adjustment = visibility_suppressed`

즉 scene meaning을 바꾸지 않고,
`conflict + wait + guard + no_probe`를 chart에서 directional leakage로 보이지 않게 눌렀다.

## 5. 이번 follow-up에서 일부러 안 한 것

아래는 이번 follow-up에서 일부러 보류했다.

- static `entry_decisions.csv` 전체를 current build 기준으로 재생성하는 작업
- entry / wait / hold / exit acceptance 쪽 owner 수정
- symbol override policy 구조 재정리
- cadence suppression family 재배치

즉 이번 follow-up은
current build replay 기준으로 남은 live gap 하나를 공통 modifier rule로 닫는 데만 집중했다.

## 6. 관련 코드/테스트

변경 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

추가 확인 테스트:

- conflict wait leakage가 `modifier_primary_reason = conflict_wait_hide`로 숨겨지는지
- structural probe wait visibility는 그대로 유지되는지

## 7. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
```

결과:

```text
44 passed
59 passed
```

## 8. 다음 reopen point

다음에는 아래 순서가 자연스럽다.

1. 새 runtime row가 쌓인 뒤 PA0 baseline artifact를 다시 읽는다
2. must-show / must-hide seed가 current build 기준으로 실제로 줄었는지 확인한다
3. 남아 있으면 `continuation / chop soft cap` 축과 symbol relief 축을 분리해서 다음 PA1 follow-up으로 간다

## 9. 한 줄 요약

```text
PA1 follow-up review 결과, hidden structural probe family는 current build에서 이미 상당 부분 복원돼 있었고,
실제 남은 live gap은 BTC conflict wait leakage였기 때문에 공통 conflict soft cap으로 그 한 축을 먼저 눌렀다.
```

추가 refreeze delta 기록:

- [product_acceptance_pa0_refreeze_after_conflict_soft_cap_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_conflict_soft_cap_delta_ko.md)

이번 follow-up 이후 이어진 PA1 하위축 기록:

- [product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md)
