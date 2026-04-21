# Current SA4 Scene Candidate Pipeline Detailed Plan

## 목적

`SA4`의 목적은 `SA3`에서 만들어진 `scene dataset / scene eval`을 바탕으로
scene 전용 `candidate / compare / promote` 루프를 여는 것이다.

이번 단계는 두 가지를 같이 한다.

1. `trend_exhaustion / time_decay_risk` hindsight scene 해상도를 조금 더 키운다.
2. scene 전용 candidate pipeline을 state25식 산출물 구조로 만든다.

즉 이번 단계는 아래 흐름을 닫는 단계다.

```text
checkpoint_rows
-> scene dataset
-> hindsight scene resolution boost
-> scene candidate tasks
-> candidate metrics
-> compare report
-> promotion decision
-> summary / manifest
```

중요:

- 아직 runtime action은 바꾸지 않는다.
- 아직 scene model을 live binding 하지 않는다.
- 이번 단계는 끝까지 `offline candidate scaffold`다.

---

## 왜 SA4 전에 hindsight 해상도를 같이 올리나

현재 `SA3`는 scene dataset까지는 열었지만,
resolved hindsight scene이 `breakout_retest_hold` 쪽으로 많이 기울어 있다.

이 상태로 `SA4`로 바로 가면 문제가 생긴다.

- `resolved_scene_task`가 한 label에 치우친다.
- `late_scene_task`가 거의 비게 된다.
- candidate pipeline이 생겨도 실질적으로 배울 게 적다.

그래서 이번 단계에서는 아래를 같이 보강한다.

- late `PARTIAL_THEN_HOLD` 계열에서 `trend_exhaustion` hindsight 해상도 증가
- late `balanced / stalled` 계열에서 `time_decay_risk` hindsight 해상도 증가

핵심은 공격적 relabel이 아니라
`scene bootstrap을 late unresolved row 일부에만 보수적으로 넓히는 것`이다.

---

## 이번 단계에서 만드는 것

### 신규 서비스

- `backend/services/path_checkpoint_scene_candidate_pipeline.py`

### 신규 스크립트

- `scripts/build_checkpoint_scene_candidate_pipeline.py`

### 연동 수정

- `backend/services/path_checkpoint_dataset.py`

### 신규 테스트

- `tests/unit/test_path_checkpoint_scene_candidate_pipeline.py`
- `tests/unit/test_build_checkpoint_scene_candidate_pipeline.py`

### 기존 테스트 보강

- `tests/unit/test_path_checkpoint_dataset.py`

---

## SA4 candidate task 구성

`scene`은 22개 전체를 한 번에 giant classifier로 학습하지 않는다.
지금 데이터 상태에 맞춰 아래 4개 task부터 연다.

### 1. `coarse_family_task`

목적:

- `ENTRY_INITIATION`
- `POSITION_MANAGEMENT`
- `DEFENSIVE_EXIT`
- `NO_TRADE`

같은 큰 family를 구분하는 후보 task

학습 타깃:

- `hindsight_scene_fine_label`이 있으면 그것으로 coarse family를 유도
- gate가 있으면 `NO_TRADE` family로 유도

### 2. `gate_task`

목적:

- `none`
- `low_edge_state`

같은 gate 차단 여부를 분리하는 후보 task

중요:

- v1에서는 runtime gate를 target으로 사용한다.
- 아직 hindsight gate label은 만들지 않는다.

### 3. `resolved_scene_task`

목적:

- 현재 resolved hindsight scene 전체를 대상으로 하는 scene multiclass task

초기 target 후보:

- `breakout_retest_hold`
- `trend_exhaustion`
- `time_decay_risk`

중요:

- min support를 못 넘는 label은 이번 candidate에서 제외한다.
- exclude된 label은 `excluded_labels`에 기록한다.

### 4. `late_scene_task`

목적:

- late checkpoint에서 특히 중요한 장면 분리

초기 target 후보:

- `trend_exhaustion`
- `time_decay_risk`

이 task는 late family 전용이라
`resolved_scene_task`보다 더 보수적인 threshold를 쓴다.

---

## 입력 feature

scene candidate는 action hindsight를 쓰지 않는다.
scene이 action보다 앞축이어야 하기 때문이다.

### categorical

- `symbol`
- `surface_name`
- `checkpoint_type`
- `leg_direction`
- `position_side`
- `unrealized_pnl_state`
- `source`
- `checkpoint_rule_family_hint`
- `exit_stage_family`

### numeric

- `checkpoint_index_in_leg`
- `current_profit`
- `mfe_since_entry`
- `mae_since_entry`
- `giveback_ratio`
- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_scene_confidence`

중요:

- `runtime_proxy_management_action_label`
- `hindsight_best_management_action_label`
- `hindsight_scene_fine_label`

같은 결과축 컬럼은 feature로 쓰지 않는다.

---

## hindsight scene resolution boost 규칙

이번 단계에서 `derive_hindsight_scene_bootstrap()`을 보강한다.

### 1. late unresolved -> trend_exhaustion fallback

대상:

- `runtime_scene_fine_label = unresolved`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`

보수적 fallback 조건:

- `action = PARTIAL_THEN_HOLD`
- `runtime_partial_exit_ev >= 0.58`
- `runtime_continuation_odds >= 0.82`
- `giveback_ratio >= 0.18`
- `current_profit >= 0.08`
- reason blob에 `runner_lock_bias` 또는 `continuation_hold_bias`

의도:

- 건강한 runner 전체를 exhaustion으로 덮지 않고
- late profit-protection 장면만 일부 끌어올린다.

### 2. late unresolved -> time_decay_risk fallback

대상:

- `runtime_scene_fine_label = unresolved`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`

보수적 fallback 조건:

- `action in {WAIT, PARTIAL_EXIT}`
- `abs(current_profit) <= 0.18`
- `max(mfe_since_entry, mae_since_entry) <= 0.35`
- `runtime_hold_quality_score <= 0.44`
- `abs(runtime_continuation_odds - runtime_reversal_odds) <= 0.18`
- reason blob에 `balanced_checkpoint_state`, `wait`, `timeout`, `stalled` 중 하나

의도:

- protective failure와 섞이지 않게
- late stagnant row 일부만 `time_decay_risk`로 확인한다.

---

## candidate 학습 방식

이번 v1은 state25와 같은 철학으로 가되,
scene 데이터량에 맞춘 가벼운 baseline을 쓴다.

### 학습기

- `OneHotEncoder + StandardScaler + LogisticRegression(class_weight="balanced")`

### 분할

- train / val / test
- stratify 가능하면 stratify
- label support가 너무 낮으면 task skip

### metric

- `macro_f1`
- `balanced_accuracy`
- `accuracy`
- `weighted_f1`

### baseline compare

reference가 있으면 task별 delta를 비교한다.

reference가 없으면:

- `shadow_only_first_candidate`

로 둔다.

---

## compare / promote 규칙

### primary tasks

- `coarse_family_task`
- `gate_task`
- `resolved_scene_task`

### secondary task

- `late_scene_task`

### promotion skeleton

#### 1. `shadow_only_first_candidate`

조건:

- reference baseline이 없음

의미:

- 첫 candidate 생성
- 아직 비교 기준 없음
- 다음 단계는 `SA5 log-only bridge review`

#### 2. `hold_regression`

조건:

- primary task 중 하나라도
  - `macro_f1 delta < -0.05`
  - 또는 `balanced_accuracy delta < -0.05`

#### 3. `promote_review_ready`

조건:

- regression blocker 없음
- primary task 중 하나 이상
  - 새로 ready
  - 또는 `macro_f1 delta > 0.03`

#### 4. `hold_no_material_gain`

조건:

- regression도 없고
- 의미 있는 개선도 없음

---

## 산출물

candidate root:

- `models/path_checkpoint_scene_candidates/`

candidate run output:

- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_bundle.joblib`
- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_metrics.json`
- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_compare_report.json`
- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_promotion_decision.json`
- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_summary.md`
- `models/path_checkpoint_scene_candidates/<candidate_id>/checkpoint_scene_candidate_run_manifest.json`
- `models/path_checkpoint_scene_candidates/latest_candidate_run.json`

---

## 구현 순서

### SA4-1

- hindsight scene resolution boost 추가
- dataset 테스트 보강

### SA4-2

- candidate task frame builder 구현
- coarse / gate / resolved / late task 분리

### SA4-3

- task trainer 구현
- metrics / dummy compare / top confusion 저장

### SA4-4

- compare report / promotion decision / summary md 구현

### SA4-5

- builder script 추가
- scene dataset/eval이 비어 있으면 자동 rebuild 연결

### SA4-6

- 실제 artifact 빌드
- task readiness와 recommendation 확인

---

## 완료 기준

- `trend_exhaustion / time_decay_risk` hindsight scene이 기존보다 늘어난다
- `checkpoint_scene_candidate_metrics.json`이 생성된다
- `checkpoint_scene_candidate_compare_report.json`이 생성된다
- `checkpoint_scene_candidate_promotion_decision.json`이 생성된다
- 첫 candidate면 `shadow_only_first_candidate`라도 괜찮다
- task별 `ready / skipped / excluded_labels / metrics`가 보인다

---

## 한 줄 결론

`SA4`는 scene을 바로 live에 넣는 단계가 아니라,
scene dataset을 바탕으로 state25식 candidate / compare / promote 루프를 scene 쪽에도 여는 단계다.
