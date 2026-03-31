# Product Acceptance PA1 Structural Wait Visibility Boundary Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
`structural wait visibility boundary`를 코드로 실제로 잘랐다.

즉 아래 두 family를 분리했다.

1. 숨길 family

- no-probe structural observe wait
- 대표 예:
  - `BTCUSD`
  - `middle_sr_anchor_required_observe`
  - `middle_sr_anchor_guard`
  - `observe_state_wait`
  - `probe_scene_id = (blank)`

2. 보호할 family

- probe_scene structural probe_wait
- 대표 예:
  - `BTCUSD + btc_lower_buy_conservative_probe`
  - `XAUUSD + xau_second_support_buy_probe`

관련 기준 문서:

- [product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md)

## 2. owner 변경 범위

이번 단계에서 직접 건드린 파일:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

이번 단계에서 일부러 안 건드린 파일:

- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- entry / wait / hold / exit owner 전체
- symbol override policy 전체 재정리

## 3. 실제 구현 내용

### 3-1. BTC structural importance boundary 축소

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서
BTC structural rebound importance tier / source reason 규칙을 조정했다.

변경 전:

- `middle_sr_anchor_required_observe`가
  probe_scene 없이도 `btc_structural_rebound`로 uplift될 수 있었다

변경 후:

- BTC structural rebound uplift는
  `probe_scene_id = btc_lower_buy_conservative_probe`가 있는 family에만 부여된다

즉 no-probe structural observe wait는
더 이상 BTC structural importance source를 먹지 않는다.

### 3-2. common modifier soft cap 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
아래 policy를 추가했다.

- `display_modifier.soft_caps.structural_wait_hide_without_probe`

적용 조건:

- `side = BUY`
- `observe_reason in {outer_band_reversal_support_required_observe, middle_sr_anchor_required_observe}`
- `blocked_by in {outer_band_guard, middle_sr_anchor_guard}`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = (blank)`
- `display_importance_source_reason = (blank)`

적용 효과:

- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = structural_wait_hide_without_probe`

### 3-3. probe-scene structural visibility 보호

이번 단계에서 숨김 조건은
`probe_scene_id absent`에만 걸리게 제한했다.

그래서 아래 family는 그대로 유지된다.

- BTC structural probe_wait
- XAU second-support structural probe_wait
- NAS clean-confirm structural probe_wait

즉 “structural family 전체 suppression”이 아니라
`no-probe observe wait leakage`만 따로 자른 것이다.

## 4. quick replay 확인

이번 구현 이후 quick replay 결과는 아래처럼 정리된다.

1. `BTC no-probe hidden`

- `check_side = BUY`
- `check_stage = OBSERVE`
- `check_display_ready = False`
- `display_importance_source_reason = ""`
- `modifier_primary_reason = structural_wait_hide_without_probe`

2. `BTC probe-scene visible`

- `check_side = BUY`
- `check_stage = OBSERVE`
- `check_display_ready = True`
- `display_importance_source_reason = btc_structural_rebound`
- `display_importance_tier = medium`
- `display_repeat_count = 2`

3. `XAU SELL cadence path untouched`

- `check_side = SELL`
- `check_stage = OBSERVE`
- `check_display_ready = True`
- `modifier_primary_reason = ""`

즉 이번 boundary는 BUY-side structural reclaim family에만 걸리고,
기존 XAU SELL cadence path는 건드리지 않았다.

## 5. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
```

결과:

```text
45 passed
59 passed
```

추가/갱신된 포인트:

- BTC probe-scene structural probe_wait가 여전히 double display로 남는지
- BTC no-probe structural observe wait가 hidden으로 내려가는지
- modifier debug surface에 새 reason이 남는지

## 6. 이번 단계에서 일부러 안 한 것

아래는 이번 단계에서 보류했다.

- structural cadence suppression family 재정리
- middle-anchor leakage를 symbol override 쪽으로 옮기는 작업
- PA0 baseline refreeze 재실행
- entry / wait / hold / exit acceptance 수정

즉 이번 단계는 visibility boundary 하나만 자른 구현이다.

## 7. 다음 reopen point

다음 자연스러운 순서는 아래와 같다.

1. 새 runtime row가 더 쌓인 뒤 PA0 baseline을 다시 얼린다
2. `BTC middle anchor observe wait` leakage가 실제로 줄었는지 본다
3. 남아 있으면 그다음은 cadence suppression vs visibility relief 경계를 더 자른다

## 8. 한 줄 요약

```text
이번 PA1 하위 구현으로
BTC no-probe structural observe wait는 숨기고,
probe-scene structural probe_wait는 계속 살리는 visibility boundary가 코드와 테스트에 고정됐다.
```

## 9. 다음 하위축 연결

이 단계 다음에는
`probe_scene + guard + probe_not_promoted`
family를 chart에서 `WAIT + repeated checks`로 읽히게 만드는
하위축으로 이어진다.

관련 문서:

- [product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md)
