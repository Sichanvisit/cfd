# SA5.6 Time-Decay Overpull Patch

## 목적

- `SA5.5` audit에서 확인된 `time_decay_risk` 과잉 선택을 줄인다
- 특히 `protective_exit_surface + RUNNER_CHECK + runtime_scene=unresolved` late row에서 `time_decay_risk`가 너무 쉽게 선택되는 문제를 selection guard로 막는다
- 모델 재학습보다 먼저, runtime bridge 선택 규칙에서 보수적으로 방어한다

## 핵심 문제

현재 `time_decay_risk`는 아래 조합에 과도하게 끌린다.

- `surface_name = protective_exit_surface`
- `checkpoint_type = RUNNER_CHECK`
- `unrealized_pnl_state = OPEN_LOSS`
- `management_action_label = FULL_EXIT`
- `giveback_ratio ~= 0.99`
- `runtime_full_exit_risk` 높음

이 조합은 실제로는 `time_decay`보다 `protective risk / thesis break`에 가깝다.

## 수정 원칙

- `time_decay_risk`는 late/stalled management 설명으로만 남긴다
- strong defensive 문맥에서는 선택 단계에서 suppress한다
- raw candidate prediction은 `scene_candidate_fine_label`에 남겨도 되지만,
  `scene_candidate_selected_label`은 `unresolved`로 강등할 수 있다

## 구현 대상

- `backend/services/path_checkpoint_scene_runtime_bridge.py`
- `tests/unit/test_path_checkpoint_scene_runtime_bridge.py`

## selection guard 규칙

### 1. late checkpoint 요구

`time_decay_risk`는 아래가 아니면 선택하지 않음

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`

### 2. strong defensive suppression

다음 중 하나라도 강하면 suppress

- `surface_name = protective_exit_surface` 이면서
  - `unrealized_pnl_state = OPEN_LOSS`
  - 또는 `management_action_label = FULL_EXIT`
  - 또는 `checkpoint_rule_family_hint in {active_open_loss, open_loss_protective}`
  - 또는 `runtime_full_exit_risk >= 0.65`
  - 또는 `giveback_ratio >= 0.60`
  - 또는 `runtime_reversal_odds >= runtime_continuation_odds + 0.10`

### 3. non-flat profit guard

`time_decay`는 원래 “안 가는 포지션” 쪽 설명이므로

- `unrealized_pnl_state != FLAT`
- 그리고 `abs(current_profit) > 0.12`

이면 suppress

## suppress 방식

- raw `scene_candidate_fine_label` / `scene_candidate_late_label`은 그대로 둔다
- 하지만 `scene_candidate_selected_label = unresolved`
- `scene_candidate_selected_confidence = 0.0`
- `scene_candidate_selected_source = suppressed_time_decay_guard`
- `scene_candidate_reason`에 suppress reason 추가

## 기대 효과

- `time_decay_risk`가 `protective_exit_surface + RUNNER_CHECK`에서 덜 빨린다
- `trend_exhaustion`과 `breakout_retest_hold`의 상대 분포가 더 정상화된다
- `SA5.5` audit에서 `time_decay_risk overpull_watch` 비중이 줄어든다

## 완료 기준

- 전용 test에서 strong defensive row가 `time_decay_risk`로 선택되지 않음
- `checkpoint_scene_log_only_bridge_latest.json`에서 `time_decay_risk` selected count가 감소
- `checkpoint_scene_disagreement_audit_latest.json`에서 `time_decay_risk` top slice가 완화되거나 overpull share가 줄어듦
