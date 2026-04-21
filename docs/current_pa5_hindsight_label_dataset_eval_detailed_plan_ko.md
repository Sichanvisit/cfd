# Current PA5 Hindsight Label Dataset Eval Detailed Plan

## 목적

이 문서는 `PA5. Hindsight Label / Dataset / Eval`을 실제 구현 단위로 내린 상세 계획이다.

이번 단계의 목표는 아래 3개다.

1. checkpoint row마다 `hindsight_best_management_action_label`을 offline에서 분리 생성한다
2. runtime row와 hindsight row를 같은 dataset contract로 묶는다
3. `checkpoint_action_eval_latest.json`으로 KPI와 분포를 요약한다

중요한 점은 이번 단계도 아직 runtime action을 바꾸지 않는다는 것이다.

즉 지금 하는 일은:

- 학습 가능한 hindsight row를 만든다
- runtime score와 hindsight label을 나란히 저장한다
- 어떤 라벨이 강하고 어떤 구간이 부족한지 eval artifact로 본다

이지,

- 실제 `HOLD / PARTIAL / FULL_EXIT / REBUY`를 live에서 바꾸는 일

은 아니다.

---

## 이번 단계의 핵심 원칙

### 1. runtime과 hindsight를 분리한다

이번 단계에서 runtime row는 그대로 유지한다.

- `runtime_*`는 당시 시점 기준의 score
- `hindsight_*`는 offline에서 붙인 사후 label

두 층을 절대 섞지 않는다.

### 2. 지금 붙이는 hindsight는 bootstrap proxy임을 명시한다

현재 checkpoint row가 아직 적고, manual truth나 장기 future join이 붙지 않았다.
그래서 PA5 v1에서는 hindsight label을 만들되 아래를 같이 저장한다.

- `hindsight_label_source`
- `hindsight_label_confidence`
- `hindsight_quality_tier`
- `hindsight_manual_exception_required`

즉 지금 라벨은 “최종 truth”가 아니라 “학습 파이프라인을 열기 위한 bootstrap hindsight”다.

### 3. 기존 dataset/eval과 분리한다

기존 surface preview dataset과 섞지 않는다.

신규 경로만 사용한다.

- `data/datasets/path_checkpoint/checkpoint_dataset.csv`
- `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`
- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`

---

## 이번 단계에서 바꾸는 것

### 1. 신규 서비스

- `backend/services/path_checkpoint_dataset.py`

역할:

- runtime proxy action 추출
- bootstrap hindsight label 생성
- base dataset / resolved dataset 생성
- KPI eval summary 생성

### 2. 신규 builder

- `scripts/build_checkpoint_dataset.py`
- `scripts/build_checkpoint_eval.py`

### 3. 신규 artifact

- `data/datasets/path_checkpoint/checkpoint_dataset.csv`
- `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`
- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`

---

## 이번 단계에서 바꾸지 않는 것

- entry runtime code
- exit runtime code
- `management_action_label` live adoption
- manual calibration watch 연동
- harvest queue

즉 이번 단계는 offline dataset/eval 단계다.

---

## dataset contract

### base dataset

`checkpoint_dataset.csv`에는 아래가 들어간다.

- checkpoint identity
- position state
- runtime score

즉 학습에 필요한 기본 runtime row를 저장한다.

### resolved dataset

`checkpoint_dataset_resolved.csv`에는 아래를 추가한다.

- `runtime_proxy_management_action_label`
- `runtime_proxy_action_confidence`
- `runtime_proxy_score_gap`
- `hindsight_best_management_action_label`
- `hindsight_label_source`
- `hindsight_label_confidence`
- `hindsight_label_reason`
- `hindsight_resolution_state`
- `hindsight_quality_tier`
- `hindsight_manual_exception_required`
- `runtime_hindsight_match`

여기서 `runtime_proxy_*`는 PA6의 resolver가 아니라,
PA5 eval용 비교 기준이다.

---

## hindsight bootstrap 규칙

### flat row

포지션이 없는 row는 관리 행위가 제한된다.

- `REBUY`
- `WAIT`

만 유효하게 본다.

`INITIAL_PUSH`에서 flat이면 대부분 `WAIT`이고,
`FIRST_PULLBACK_CHECK / RECLAIM_CHECK`에서 continuation과 rebuy readiness가 충분히 높을 때만 `REBUY`를 허용한다.

### active position row

포지션이 있는 row는 아래를 본다.

- `FULL_EXIT`
  - `runtime_full_exit_risk`가 높고 reversal이 continuation보다 충분히 강할 때
- `PARTIAL_THEN_HOLD`
  - partial EV가 높고, runner/profit context가 있을 때
- `HOLD`
  - continuation과 hold quality가 모두 강할 때
- `REBUY`
  - reclaim/pullback 이후 size re-expansion 근거가 충분할 때
- `PARTIAL_EXIT`
  - 일부 잠그는 편이 더 유리하지만 full exit까지는 아닐 때
- `WAIT`
  - 확신이 약하거나 애매할 때

### manual exception 규칙

아래 중 하나면 `hindsight_manual_exception_required = true`로 둔다.

- top action gap이 너무 작다
- confidence가 충분히 높지 않다
- `HOLD / PARTIAL_EXIT / PARTIAL_THEN_HOLD` 사이가 특히 애매하다

즉 자동 라벨은 붙이되,
애매한 row는 나중에 manual review로 올릴 수 있게 남겨둔다.

---

## KPI 계산 방식

PA5에서는 아직 live resolver가 없으므로,
`runtime_proxy_management_action_label`과 hindsight label을 비교한 proxy KPI로 계산한다.

### `premature_full_exit_rate`

- runtime proxy가 `FULL_EXIT`였지만 hindsight는 `FULL_EXIT`가 아니었던 비율
- 낮을수록 좋다

### `runner_capture_rate`

- hindsight가 `HOLD` 또는 `PARTIAL_THEN_HOLD`인 row 중
  runtime proxy도 runner 쪽으로 갔던 비율
- 높을수록 좋다

### `missed_rebuy_rate`

- hindsight가 `REBUY`인 row 중 runtime proxy가 `REBUY`가 아니었던 비율
- 낮을수록 좋다

### `hold_precision`

- runtime proxy가 `HOLD`인 row 중 hindsight도 `HOLD`였던 비율

### `partial_then_hold_quality`

- runtime proxy가 `PARTIAL_THEN_HOLD`인 row 중 hindsight도 동일했던 비율

### `full_exit_precision`

- runtime proxy가 `FULL_EXIT`인 row 중 hindsight도 `FULL_EXIT`였던 비율

---

## 상세 구현 순서

### PA5-A. dataset helper 서비스 추가

`path_checkpoint_dataset.py`에서 아래를 제공한다.

- `derive_runtime_proxy_management_action(...)`
- `derive_hindsight_bootstrap_label(...)`
- `build_checkpoint_dataset_artifacts(...)`
- `build_checkpoint_action_eval(...)`

### PA5-B. dataset builder 추가

`build_checkpoint_dataset.py`는 checkpoint row를 읽어

- base dataset
- resolved dataset

2개 csv를 만든다.

### PA5-C. eval builder 추가

`build_checkpoint_eval.py`는 resolved dataset을 읽어

- KPI
- label 분포
- quality tier 분포
- per-symbol recommended focus

를 포함한 `checkpoint_action_eval_latest.json`을 만든다.

### PA5-D. sparse-data 정직성 유지

현재 checkpoint row가 적거나 대부분 flat row면,
artifact는 그 사실을 그대로 보여준다.

즉 억지로 라벨 균형을 만들지 않고,

- `position_side_row_count`
- `manual_exception_count`
- `recommended_next_action`

으로 부족한 축을 그대로 드러낸다.

---

## 완료 기준

- `backend/services/path_checkpoint_dataset.py`가 생성된다
- dataset csv 2종이 생성된다
- `checkpoint_action_eval_latest.json`이 생성된다
- hindsight label과 runtime score가 분리된 채 저장된다
- manual-exception row를 표시할 수 있다
- 신규 테스트와 기존 영향권 테스트가 통과한다

---

## 다음 단계로 넘어가는 기준

PA5가 닫히면 다음은 `PA6 Best Action Resolver`다.

즉 그 다음부터는

- runtime proxy 비교용 label

에서

- 실제 `management_action_label / confidence / reason`

으로 넘어간다.
