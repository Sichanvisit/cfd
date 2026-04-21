# SA5.5 Scene Candidate Disagreement Audit

## 목적

- `SA5` log-only bridge 결과에서 왜 `scene candidate`가 `time_decay_risk / trend_exhaustion` 쪽으로 과하게 끌리는지 케이스북 형태로 분석한다
- `heuristic runtime scene`과 `candidate selected scene`이 충돌하는 row를 모아, 단순 mismatch 수치가 아니라 어떤 `symbol / surface / checkpoint_type / action family`에서 문제가 집중되는지 본다
- `SA6` 전에 어떤 scene은 그대로 bias 후보로 유지하고, 어떤 scene은 보수적으로 묶어야 하는지 판단 근거를 만든다

## 핵심 질문

- `time_decay_risk`는 진짜 scene overpull인가, 아니면 defensive action을 먼저 포착한 것인가
- `trend_exhaustion`은 late runner row에서 유의미한 설명력을 가지는가
- mismatch의 대부분이 `runtime_scene=unresolved` 때문인지, 아니면 heuristic과 candidate가 실제로 다른 scene을 말하고 있는지

## 신규 파일

- `backend/services/path_checkpoint_scene_disagreement_audit.py`
- `scripts/build_checkpoint_scene_disagreement_audit.py`
- `tests/unit/test_path_checkpoint_scene_disagreement_audit.py`
- `tests/unit/test_build_checkpoint_scene_disagreement_audit.py`

## 입력 데이터

- 기본 입력은 `checkpoint_dataset_resolved.csv`
- scene runtime / hindsight / action / bridge candidate를 모두 같이 보기 위해 `resolved dataset` 기준으로 분석
- 필요 시 audit 내부에서 bridge prediction을 replay

## 분석 범위

### 1. high-confidence disagreement row

다음 조건 row를 모은다

- `scene_candidate_available = true`
- `scene_candidate_selected_confidence >= 0.70`
- `scene_candidate_runtime_scene_match = false`

### 2. label pull profile

후보 scene별로 아래를 계산

- disagreement row count
- `runtime_scene_fine_label = unresolved` 비율
- `hindsight_scene_fine_label = unresolved` 비율
- expected action alignment rate
- top slice
  - `symbol`
  - `surface_name`
  - `checkpoint_type`
  - `source`

### 3. casebook examples

각 후보 scene별로 대표 사례를 저장

- `symbol`
- `checkpoint_id`
- `surface_name`
- `checkpoint_type`
- `runtime_scene_fine_label`
- `hindsight_scene_fine_label`
- `candidate_selected_label`
- `candidate_selected_confidence`
- `runtime_proxy_management_action_label`
- `hindsight_best_management_action_label`
- `checkpoint_rule_family_hint`
- `exit_stage_family`
- `current_profit`
- `giveback_ratio`
- `scene_candidate_reason`

## expected action alignment

scene이 action과 완전히 같지는 않지만, 다음 정도의 정합성은 본다

- `time_decay_risk`
  - `FULL_EXIT`, `PARTIAL_EXIT`, `WAIT`
- `trend_exhaustion`
  - `PARTIAL_THEN_HOLD`, `HOLD`, `PARTIAL_EXIT`
- `breakout_retest_hold`
  - `REBUY`, `HOLD`, `PARTIAL_THEN_HOLD`

이 정합성이 높으면 scene mismatch라도 “action bias 후보로는 의미 있음”으로 볼 수 있다

## 산출물

- `data/analysis/shadow_auto/checkpoint_scene_disagreement_audit_latest.json`

## summary에서 볼 것

- `high_conf_scene_disagreement_count`
- `candidate_selected_label_counts`
- `runtime_unresolved_disagreement_share`
- `hindsight_unresolved_disagreement_share`
- `expected_action_alignment_rate`
- `label_pull_profiles`
- `top_slice_counts`
- `casebook_examples`
- `recommended_next_action`

## 추천 해석 규칙

- `hindsight unresolved` 비율이 매우 높고 `runtime unresolved`도 높으면
  - `scene overpull watch`
- `hindsight resolved` 비율은 낮아도 `expected_action_alignment_rate`가 높으면
  - `action proxy useful, scene bias는 watch-only 유지`
- `trend_exhaustion`처럼 hindsight resolved가 꽤 있고 action 정합성도 높으면
  - `SA6 후보로 검토 가능`

## 완료 기준

- `time_decay_risk / trend_exhaustion / breakout_retest_hold`에 대한 pull profile이 artifact에서 보인다
- top mismatch slice가 `symbol / surface / checkpoint_type` 기준으로 바로 읽힌다
- representative casebook examples가 남는다
- `SA6` 전에 어떤 scene을 바로 bias 후보로 쓰면 안 되는지 설명 가능하다
