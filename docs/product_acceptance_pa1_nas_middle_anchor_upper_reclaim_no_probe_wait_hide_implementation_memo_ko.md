# Product Acceptance PA1 NAS Middle-Anchor and Upper-Reclaim No-Probe Wait Hide Implementation Memo

작성일: 2026-03-31 (KST)

## 1. 이번 단계에서 한 일

이번 PA1 하위축에서는
아래 NAS no-probe visible family를 accepted hidden suppression으로 정리했다.

- `NAS100 + middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`
- `NAS100 + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait + no_probe`

관련 기준 문서:

- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md)

## 2. 직접 건드린 owner 범위

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_product_acceptance_pa0_baseline_freeze.py)

이번 단계에서 일부러 건드리지 않은 범위:

- NAS probe-scene family
- BTC energy-soft-block backlog
- XAU backlog
- entry / wait / hold / exit acceptance

## 3. 구현 내용

### 3-1. NAS middle-anchor sell no-probe hide policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`nas_sell_middle_anchor_wait_hide_without_probe`
policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = SELL`
- `observe_reason_allow = middle_sr_anchor_required_observe`
- `blocked_by_allow = middle_sr_anchor_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = true`
- `require_importance_source_absent = true`

### 3-2. NAS upper-reclaim buy no-probe hide policy 추가

[chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)에
`nas_upper_reclaim_wait_hide_without_probe`
policy를 추가했다.

고정 조건:

- `symbol_allow = NAS100`
- `side_allow = BUY`
- `observe_reason_allow = upper_reclaim_strength_confirm`
- `blocked_by_allow = forecast_guard`
- `action_none_allow = observe_state_wait`
- `require_probe_scene_absent = true`
- `require_importance_source_absent = true`

즉 probe scene도 없고 importance source도 없는 NAS no-probe wait row만 숨긴다.

### 3-3. common modifier suppression 연결

[consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) modifier path에
두 soft-cap을 연결했다.

이 family가 걸리면:

- `check_display_ready = False`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_sell_middle_anchor_wait_hide_without_probe` 또는 `nas_upper_reclaim_wait_hide_without_probe`

로 surface가 바뀐다.

### 3-4. painter top-level fallback 차단

[chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)에서
두 hidden suppression reason이 붙은 row는
top-level directional fallback도 다시 그리지 않게 했다.

### 3-5. PA0 accepted hidden suppression 추가

[product_acceptance_pa0_baseline_freeze.py](C:\Users\bhs33\Desktop\project\cfd\scripts\product_acceptance_pa0_baseline_freeze.py)에
두 reason을 accepted hidden suppression set에 추가했다.

그래서 must-show / must-hide / must-block builder가
이 reason이 붙은 hidden row를 queue에서 다시 문제로 세지 않는다.

## 4. 테스트

실행:

```text
pytest -q tests/unit/test_consumer_check_state.py
pytest -q tests/unit/test_chart_painter.py
pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py
```

결과:

```text
55 passed
67 passed
10 passed
```

고정한 확인 포인트:

- middle-anchor sell no-probe row가 build 단계에서 숨는지
- upper-reclaim buy no-probe row가 build 단계에서 숨는지
- painter가 nested hidden row를 top-level fallback으로 다시 그리지 않는지
- PA0 script가 두 hidden suppression reason을 문제 queue에서 skip하는지

## 5. live runtime 확인

`main.py`를 새 코드로 다시 시작했다.

- restart log: [cfd_main_restart_20260331_191814.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_191814.out.log)
- restart err log: [cfd_main_restart_20260331_191814.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260331_191814.err.log)
- live process: `PID 12732`
- start time: `2026-03-31T19:18:17`

fresh middle-anchor hidden rows는 live에서 직접 확인됐다.

대표 row:

- `2026-03-31T19:19:04`
- `observe_reason = middle_sr_anchor_required_observe`
- `blocked_by = middle_sr_anchor_guard`
- `check_display_ready = False`
- `check_stage = OBSERVE`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_sell_middle_anchor_wait_hide_without_probe`

post-restart fresh middle-anchor hidden row count:

```text
fresh_hidden_count = 60
queue_overlap_count = 0
```

즉 fresh hidden row는 live에서도 문제 queue에 다시 들어가지 않았다.

upper-reclaim direct fresh row는 post-restart window에서 재발생하지 않았지만,
historical representative row `2026-03-31T19:00:48`을 current build로 다시 태우면
아래처럼 바뀐다.

- `check_display_ready = False`
- `check_stage = OBSERVE`
- `check_side = BUY`
- `display_score = 0.0`
- `display_repeat_count = 0`
- `modifier_primary_reason = nas_upper_reclaim_wait_hide_without_probe`

즉 upper-reclaim family도 current build contract는 hidden suppression이 맞다.

## 6. PA0 refreeze 해석

비교 기준:

- 이전 snapshot: [product_acceptance_pa0_baseline_snapshot_20260331_192035.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260331_192035.json)
- 새 latest: [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

latest baseline generated_at:

- `2026-03-31T19:26:54`

핵심 해석:

- previous must-hide main family였던 NAS no-probe bundle은 `15 -> 7`로 줄었다
- 세부적으로는
  - `middle-anchor sell no-probe = 13 -> 7`
  - `upper-reclaim buy no-probe = 2 -> 0`
- total `must_hide = 15`가 그대로인 이유는
  probe-scene NAS family가 새로 올라왔기 때문이다

current must-hide composition:

- `8/15 = NAS upper_reject_probe_observe + probe_promotion_gate + probe_not_promoted + nas_clean_confirm_probe`
- `7/15 = NAS middle_sr_anchor_required_observe + middle_sr_anchor_guard + observe_state_wait + no_probe`

즉 이번 하위축의 결론은 아래다.

```text
NAS must-hide no-probe main axis는 실제로 줄었다.
upper-reclaim은 queue에서 빠졌고,
middle-anchor는 fresh hidden row가 누적되면서 13 -> 7까지 감소했다.
이제 next visible axis는 NAS probe-scene family와 BTC energy-soft-block backlog다.
```
