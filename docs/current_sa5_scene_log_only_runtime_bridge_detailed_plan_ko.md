# SA5. Scene Log-Only Runtime Bridge

## 목적

- `SA4`에서 만든 scene candidate를 실제 runtime decision에 바로 반영하지 않고, 먼저 `log-only`로 관찰한다
- heuristic scene과 candidate scene이 live/runtime row에서 얼마나 자주 일치하는지 본다
- `scene candidate`가 `action resolver`를 흔들기 전에, disagreement 패턴과 high-confidence mismatch를 먼저 점검한다

## 핵심 원칙

- `scene candidate`는 아직 행동을 바꾸지 않는다
- `active_candidate_state.json`이 있어야만 bridge가 활성화된다
- `latest_candidate_run.json`만 있다고 자동 활성화되면 안 된다
- runtime에서는 `heuristic scene`, `candidate scene`, `match 여부`만 기록한다
- `SA6` 전까지는 `management_action_label`에 영향 주지 않는다

## 신규 파일

- `backend/services/path_checkpoint_scene_runtime_bridge.py`
- `scripts/build_checkpoint_scene_log_only_bridge_report.py`
- `tests/unit/test_path_checkpoint_scene_runtime_bridge.py`
- `tests/unit/test_build_checkpoint_scene_log_only_bridge_report.py`

## 연동 파일

- `backend/services/path_checkpoint_context.py`
- `backend/services/path_checkpoint_dataset.py`

## 구현 내용

### 1. active state contract

- `ensure_checkpoint_scene_active_candidate_state()`로 최신 candidate를 `log_only` active state로 승격
- `build_checkpoint_scene_log_only_bridge_v1()`는 `active_candidate_state.json`이 없으면 비활성 상태로 남음
- `latest_candidate_run.json`만 보고 암묵 활성화하지 않음

### 2. runtime bridge payload

checkpoint row마다 아래를 기록

- `scene_candidate_available`
- `scene_candidate_candidate_id`
- `scene_candidate_binding_mode`
- `scene_candidate_coarse_family`
- `scene_candidate_gate_label`
- `scene_candidate_gate_block_level`
- `scene_candidate_fine_label`
- `scene_candidate_late_label`
- `scene_candidate_selected_label`
- `scene_candidate_selected_source`
- `scene_candidate_runtime_scene_match`
- `scene_candidate_runtime_gate_match`
- `scene_candidate_reason`

### 3. log-only bridge report

artifact에서 아래를 본다

- `bridge_available_row_count`
- `candidate_selected_label_counts`
- `candidate_gate_label_counts`
- `runtime_candidate_scene_match_rate`
- `runtime_candidate_gate_match_rate`
- `high_confidence_scene_disagreement_count`
- `high_confidence_gate_disagreement_count`
- `disagreement_examples`

### 4. runtime 영향 범위

- `path_checkpoint_context.py`는 bridge 결과를 runtime latest row에 prefixed key로만 기록
- `action resolver`는 아직 bridge 결과를 읽지 않음
- `SA6`에서만 scene bias를 제한적으로 연결

## 산출물

- `models/path_checkpoint_scene_candidates/active_candidate_state.json`
- `data/analysis/shadow_auto/checkpoint_scene_log_only_bridge_latest.json`

## 테스트

- bridge가 active state 없이 자동 활성화되지 않는지
- latest manifest에서 active state를 안전하게 생성하는지
- late checkpoint에서 `late_scene_task`가 선택 우선권을 갖는지
- bridge report가 disagreement와 match rate를 올바르게 집계하는지
- 기존 checkpoint context/runtime sync가 깨지지 않는지

## 검증 포인트

- `candidate_selected_label`이 runtime row에 실제로 기록되는가
- `scene_candidate_available=false`와 `reason`이 inactive 상황에서 명확한가
- active state 생성 후 report summary가 `selected_label / gate_label / disagreement`를 제대로 보여주는가
- log-only 단계에서 `management_action_label`이 변하지 않는가

## 완료 기준

- active state 생성과 bridge report가 모두 동작
- runtime row에 bridge prefixed key가 안정적으로 기록
- high-confidence disagreement를 artifact에서 바로 읽을 수 있음
- `SA6` 전까지는 action 영향이 0임이 테스트로 확인됨
