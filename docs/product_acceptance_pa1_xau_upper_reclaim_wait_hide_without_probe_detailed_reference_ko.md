# Product Acceptance PA1 XAU Upper-Reclaim Wait Hide Without Probe Detailed Reference

작성일: 2026-04-01 (KST)

## 1. 이번 하위축

이번 축은 `XAUUSD + upper_reclaim_strength_confirm + forecast_guard + observe_state_wait` family를 `WAIT relief`가 아니라 `BUY-side hidden suppression`으로 닫는 작업이다.

대상 조건:

- `symbol = XAUUSD`
- `observe_reason = upper_reclaim_strength_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- importance source 없음

## 2. 왜 이 축이 필요했는가

직전 PA0 latest 기준 이 family가 그대로 남아 있었다.

- `must_hide_leakage = 5`
- `must_block_candidates = 5`

대표 live row:

- `2026-04-01T16:36:21`
- `2026-04-01T16:36:26`
- `2026-04-01T16:36:32`
- `2026-04-01T16:36:34`
- `2026-04-01T16:36:38`

저장 상태는 공통적으로 아래와 같았다.

- `consumer_check_display_ready = True`
- `consumer_check_stage = PROBE`
- `chart_event_kind_hint = ""`
- `chart_display_mode = ""`
- `chart_display_reason = ""`

즉 차트에 보여줄 구조가 아니라, guard가 걸린 upper reclaim observe를 숨겨야 하는 family가 visible residue로 남아 있었다.

## 3. 이번에 고정한 해석

이 family는 다음으로 본다.

- `probe-scene structural wait`가 아님
- `forecast_guard`가 걸린 upper reclaim observe
- `probe_scene`도 없고 importance source도 없음
- 따라서 directional visibility relief가 아니라 hidden suppression이 맞음

mirror 기준:

- NAS existing reason: `nas_upper_reclaim_wait_hide_without_probe`
- XAU new mirror reason: `xau_upper_reclaim_wait_hide_without_probe`

## 4. owner

- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_painter.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)
- [test_consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_consumer_check_state.py)
- [test_chart_painter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_chart_painter.py)
- [test_product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_product_acceptance_pa0_baseline_freeze.py)

## 5. acceptance target

- current-build replay에서 target family가 `check_display_ready = False`로 내려갈 것
- `modifier_primary_reason = xau_upper_reclaim_wait_hide_without_probe`가 남을 것
- painter hidden suppression 목록에서 이 reason을 숨길 것
- PA0 accepted hidden suppression reason 목록에서 이 reason을 skip할 것
- live exact fresh row가 다시 뜨면 같은 reason이 CSV flat surface에 기록될 것
- exact fresh row가 바로 안 떠도, recent window turnover 뒤 PA0 `must_hide 5 / must_block 5`가 0으로 수렴할 것

## 6. 연결 문서

- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md)
