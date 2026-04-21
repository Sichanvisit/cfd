# PA1 NAS Balanced Conflict Hidden Suppression Detailed Reference

## 목적

- 남아 있던 PA1 마지막 chart residue인
  `NAS100 + conflict_box_upper_bb20_lower_lower_dominant_observe + observe_state_wait`
  family를 accepted hidden suppression으로 닫는다.

## 관찰 사실

- latest PA0 snapshot [product_acceptance_pa0_baseline_snapshot_20260401_181638.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_snapshot_20260401_181638.json) 기준 `must_show_missing_count=2`였다.
- 두 row 모두 공통 shape는 아래였다.
  - `observe_reason=conflict_box_upper_bb20_lower_lower_dominant_observe`
  - `action_none_reason=observe_state_wait`
  - `probe_scene_id=(blank)`
  - `consumer_check_display_ready=False`
  - `consumer_check_stage=(blank)`
  - `chart_event_kind_hint/chart_display_mode/chart_display_reason/modifier_primary_reason=(blank)`

## 판단

- 이 family는 `보여야 하는 wait-check`가 아니라 `균형 conflict라서 숨기는 것이 맞는 hidden suppression`이다.
- 이미 [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py) baseline에는 `balanced_conflict_display_suppressed`가 있었고, 빠져 있던 것은 그 suppression을 acceptance artifact에 남기는 reason/log contract였다.

## 반영 축

1. `consumer_check_state_v1` replay에서
   `balanced_conflict_wait_hide_without_probe` reason을 명시한다.
2. painter는 modifier reason이 있거나, live flat payload가 아직 blank여도 raw balanced-conflict shape를 hidden suppression으로 본다.
3. PA0 baseline freeze도 같은 raw-family fallback을 accepted hidden으로 처리한다.

## 기대 결과

- fresh row flat payload에 reason이 아직 blank여도 PA0 `must_show_missing 2 -> 0`이 가능하다.
- 이후 live logging path가 나중에 reason까지 채워도, acceptance 판정은 이미 안정적으로 유지된다.
