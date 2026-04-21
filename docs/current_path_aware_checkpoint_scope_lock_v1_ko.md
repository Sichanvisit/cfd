# Current Path-Aware Checkpoint Scope Lock v1

## 목적

이 문서는 path-aware checkpoint decision 구조의 `PA0 Scope Lock / KPI Freeze` 결과를 고정하기 위한 문서다.

이 문서의 목적은 세 가지다.

1. v1에서 `무엇을 바꾸고 무엇을 안 바꾸는지`를 고정한다
2. 기존 runtime / dataset / eval / activation 흐름과 충돌하지 않는 경계를 명시한다
3. 앞으로 checkpoint layer가 사용할 KPI 정의와 계산 기준을 먼저 고정한다

즉 이 문서는 구현 전에 범위 흔들림을 막기 위한 `계약 문서`다.

---

## 한 줄 요약

> v1의 checkpoint layer는 기존 4개 surface를 대체하지 않는다.
> `follow_through / continuation_hold / protective_exit` 위에 공통 path context를 추가하는 계층으로 시작하며,
> 기존 entry/exit 실전 동작과 surface dataset은 바로 덮어쓰지 않는다.

---

## 1. v1에서 바꾸는 것

아래는 v1의 직접 범위다.

### 1-1. 새로 추가하는 것

- `leg_id` 기반 흐름 식별
- `checkpoint_id` 기반 판단 시점 식별
- `checkpoint_type` 분류
- `runtime_*` checkpoint score
- `management_action_label`
- hindsight 기준의 `hindsight_best_management_action_label`
- checkpoint harvest / eval / dataset

### 1-2. 우선 적용 대상

checkpoint layer는 아래 3개 surface에 우선 적용한다.

- `follow_through_surface`
- `continuation_hold_surface`
- `protective_exit_surface`

### 1-3. v1의 핵심 질문

v1에서 푸는 문제는 다음이다.

- 지금 눌림이 건강한가
- 지금 일부 익절 후 runner 유지가 맞는가
- 지금 full exit가 정말 thesis break인가
- 지금 다시 size를 늘리거나 재진입할 가치가 있는가

즉 `포지션 운영` 문제를 푸는 것이 핵심이다.

---

## 2. v1에서 바꾸지 않는 것

아래는 v1에서 의도적으로 건드리지 않는다.

### 2-1. initial entry taxonomy

`initial_entry_surface`는 기존 taxonomy를 유지한다.

- `ENTER_LONG`
- `ENTER_SHORT`
- `WAIT`

checkpoint layer는 `initial_entry_surface`에 context를 제공할 수는 있지만,
v1의 주 action taxonomy는 아니다.

### 2-2. broker finality / hard risk guard finality

아래는 그대로 유지한다.

- broker 최종 실행 권한
- hard risk guard 최종 차단 권한
- 기존 exit orchestrator의 최종 실행 구조

### 2-3. 기존 surface preview dataset schema

아래 dataset의 기존 컬럼은 v1에서 직접 바꾸지 않는다.

- `follow_through_dataset_augmented.csv`
  - `continuation_positive_binary`
- `continuation_hold_dataset_augmented.csv`
  - `hold_runner_binary`
- `protective_exit_dataset_augmented.csv`
  - `protect_exit_binary`

즉 checkpoint layer는 별도 dataset으로 시작한다.

### 2-4. 기존 preview eval pipeline

아래는 v1 초반에 그대로 유지한다.

- `backend/services/symbol_surface_preview_evaluation.py`
- 기존 `symbol_surface_preview_evaluation_latest.json`

checkpoint eval은 별도 artifact로 추가한다.

---

## 3. entry action과 management action 경계

이 경계는 v1에서 절대 흔들지 않는다.

### 3-1. entry action

진입 여부를 판단하는 label.

- `ENTER_LONG`
- `ENTER_SHORT`
- `WAIT`

주 대상:

- `initial_entry_surface`

### 3-2. management action

이미 열린 leg / position을 운영하는 label.

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`
- `WAIT`

주 대상:

- `follow_through_surface`
- `continuation_hold_surface`
- `protective_exit_surface`

### 3-3. 경계 규칙

- v1에서는 `ENTER_LONG`과 `HOLD`를 같은 resolver로 합치지 않는다
- entry resolver와 management resolver는 별도로 유지한다
- `REBUY`는 same-leg rebuild 또는 size re-expansion에만 사용한다

---

## 4. 기존 코드와 충돌하지 않기 위한 고정 규칙

### 4-1. 현재 실전 행동을 바로 덮어쓰지 않는다

PA1~PA7까지는 기본 원칙이 `log-only`다.

즉:

- row 저장
- score 저장
- hindsight label 저장
- eval / harvest 저장

은 하되, 기존 실전 action을 바로 바꾸지 않는다.

### 4-2. 기존 파일을 덮어쓰지 않는다

checkpoint layer는 아래 기존 핵심 파일을 `교체`하지 않고 `연동`한다.

- `backend/services/entry_try_open_entry.py`
- `backend/services/exit_manage_positions.py`
- `backend/services/failure_label_harvest.py`
- `backend/services/symbol_surface_preview_evaluation.py`
- `backend/services/hold_exit_augmentation_apply.py`
- `backend/services/follow_through_negative_expansion_apply.py`

### 4-3. 기존 artifact 이름을 재사용하지 않는다

checkpoint layer는 별도 artifact를 사용한다.

신규 예약 artifact:

- `data/analysis/shadow_auto/path_leg_snapshot_latest.json`
- `data/analysis/shadow_auto/checkpoint_distribution_latest.json`
- `data/analysis/shadow_auto/checkpoint_action_eval_latest.json`
- `data/analysis/shadow_auto/checkpoint_harvest_latest.json`

기존 artifact는 그대로 유지한다.

### 4-4. 기존 dataset을 직접 덮어쓰지 않는다

checkpoint layer는 아래 신규 dataset으로만 시작한다.

- `data/datasets/path_checkpoint/checkpoint_dataset.csv`
- `data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv`

즉 기존 multi-surface preview dataset에 바로 checkpoint label을 섞지 않는다.

### 4-5. manual truth / calibration watch와는 단계적으로 연결한다

`manual_truth_calibration_watch.py` 같은 주기적 빌더 루프에는
checkpoint artifact가 `PA5` 이후에만 들어간다.

이유:

- PA1~PA4는 아직 스키마와 score 안정화 단계
- 너무 이른 자동화 연결은 artifact churn을 만든다

---

## 5. 필드 네이밍 고정

### 5-1. runtime 전용 prefix

runtime 시점에 계산 가능한 필드는 아래 prefix를 사용한다.

- `runtime_`

예:

- `runtime_continuation_odds`
- `runtime_reversal_odds`
- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`
- `runtime_rebuy_readiness`

### 5-2. hindsight 전용 prefix

사후 평가 전용 필드는 아래 prefix를 사용한다.

- `hindsight_`

예:

- `hindsight_best_management_action_label`
- `hindsight_leg_outcome`
- `hindsight_mfe_after_checkpoint`

### 5-3. checkpoint id 계열

- `leg_id`
- `checkpoint_id`
- `checkpoint_index_in_leg`
- `checkpoint_type`

### 5-4. management output 계열

- `management_action_label`
- `management_action_confidence`
- `management_action_reason`

### 5-5. 금지 규칙

아래 기존 컬럼 이름을 checkpoint layer 의미로 재사용하지 않는다.

- `action`
- `outcome`
- `enter_now_binary`
- `continuation_positive_binary`
- `hold_runner_binary`
- `protect_exit_binary`

이 값들은 기존 pipeline 의미를 유지해야 한다.

---

## 6. position state 최소 계약

checkpoint layer가 학습과 runtime에서 모두 의미 있으려면
아래 필드를 최소 계약으로 본다.

- `position_side`
- `position_size_fraction`
- `avg_entry_price`
- `realized_pnl_state`
- `unrealized_pnl_state`
- `runner_secured`
- `mfe_since_entry`
- `mae_since_entry`

이 필드가 없으면:

- `HOLD`
- `PARTIAL_EXIT`
- `PARTIAL_THEN_HOLD`
- `FULL_EXIT`
- `REBUY`

판단이 실제 포지션 관리가 아니라 차트 분류로만 남게 된다.

---

## 7. KPI Freeze

v1 KPI는 아래 6개로 고정한다.

### 7-1. `premature_full_exit_rate`

의미:

- full exit를 너무 빨리 한 비율

정의:

- 분자:
  - runtime `management_action_label = FULL_EXIT`
  - hindsight `hindsight_best_management_action_label`이
    `HOLD`, `PARTIAL_THEN_HOLD`, `REBUY` 중 하나인 row
- 분모:
  - runtime `management_action_label = FULL_EXIT` row 전체

해석:

- 낮을수록 좋다

### 7-2. `runner_capture_rate`

의미:

- 추세가 더 이어지는 구간에서 runner를 잘 남긴 비율

정의:

- 분자:
  - hindsight가 `HOLD` 또는 `PARTIAL_THEN_HOLD`
  - runtime action도 runner를 남기는 쪽
    - `HOLD`
    - `PARTIAL_THEN_HOLD`
- 분모:
  - hindsight가 `HOLD` 또는 `PARTIAL_THEN_HOLD`인 row 전체

해석:

- 높을수록 좋다

### 7-3. `missed_rebuy_rate`

의미:

- 다시 늘리거나 재진입할 기회를 놓친 비율

정의:

- 분자:
  - hindsight `hindsight_best_management_action_label = REBUY`
  - runtime action이 `REBUY`가 아닌 row
- 분모:
  - hindsight `REBUY` row 전체

해석:

- 낮을수록 좋다

### 7-4. `hold_precision`

의미:

- hold라고 판단한 것 중 실제로 hold 쪽이 맞았던 비율

정의:

- 분자:
  - runtime `management_action_label = HOLD`
  - hindsight도 `HOLD`
- 분모:
  - runtime `management_action_label = HOLD` row 전체

해석:

- 높을수록 좋다

### 7-5. `partial_then_hold_quality`

의미:

- 일부 익절 후 runner 유지 판단의 품질

정의:

- 분자:
  - runtime `management_action_label = PARTIAL_THEN_HOLD`
  - hindsight도 `PARTIAL_THEN_HOLD`
- 분모:
  - runtime `management_action_label = PARTIAL_THEN_HOLD` row 전체

해석:

- 높을수록 좋다

### 7-6. `full_exit_precision`

의미:

- full exit라고 판단한 것 중 실제로 thesis break exit가 맞았던 비율

정의:

- 분자:
  - runtime `management_action_label = FULL_EXIT`
  - hindsight도 `FULL_EXIT`
- 분모:
  - runtime `management_action_label = FULL_EXIT` row 전체

해석:

- 높을수록 좋다

---

## 8. KPI 계산 시점 고정

### PA0 시점

- KPI 공식만 고정
- 숫자 baseline은 아직 비어 있어도 됨

### PA5 시점

- 첫 checkpoint dataset / resolved dataset 생성
- 첫 checkpoint eval artifact 생성
- 이때부터 KPI baseline 값을 채운다

### PA8 시점

- bounded runtime adoption 전후 비교
- KPI delta를 승격 판단의 핵심 근거로 사용

---

## 9. KPI source of truth

checkpoint KPI의 source of truth는 아래로 고정한다.

### runtime source

- `checkpoint_rows.csv`
- `checkpoint_rows.detail.jsonl`

### hindsight / resolved source

- `checkpoint_dataset_resolved.csv`

### eval artifact

- `checkpoint_action_eval_latest.json`

즉 v1에서는 기존 surface eval artifact를 checkpoint KPI source로 직접 쓰지 않는다.

---

## 10. 기존 학습 흐름과의 연결 방식

### 10-1. 현재 surface dataset은 그대로 유지

현재 dataset:

- `follow_through_dataset_augmented.csv`
- `continuation_hold_dataset_augmented.csv`
- `protective_exit_dataset_augmented.csv`

은 기존 surface 학습용 source로 그대로 유지한다.

### 10-2. checkpoint dataset은 별도 병행

checkpoint layer는 별도 dataset을 사용한다.

이유:

- v1 초반에는 schema가 자주 변할 수 있음
- 기존 surface eval readiness를 깨지 않기 위함
- 학습 continuity를 보장하기 위함

### 10-3. 나중에 연결하는 방식

checkpoint layer는 먼저 `shadow / eval / harvest`로 검증하고,
이후 필요한 경우에만 기존 surface dataset과 feature bridge를 만든다.

즉 초기에는:

- `기존 학습 체인 유지`
- `checkpoint 체인 병렬 구축`

구조로 간다.

---

## 11. 구현 게이트

아래 조건을 만족해야 다음 단계로 넘어간다.

### PA0 -> PA1

- 범위 문서 고정
- KPI 정의 고정
- entry / management 경계 고정

### PA4 -> PA5

- runtime score 필드가 안정적으로 저장됨
- hindsight 필드와 섞이지 않음

### PA7 -> PA8

- checkpoint eval artifact에서 KPI가 계산 가능함
- obvious auto-apply와 manual-exception 경계가 분리됨

---

## 12. 현재 결론

v1에서 가장 중요한 결론은 아래다.

1. checkpoint layer는 `새 surface`가 아니다
2. checkpoint layer는 기존 4 surface 위의 `공통 context layer`다
3. v1은 `follow_through / continuation_hold / protective_exit` 우선이다
4. 기존 surface dataset / preview eval / activation 흐름은 직접 덮어쓰지 않는다
5. checkpoint dataset / eval / harvest는 별도 체인으로 먼저 안정화한다
6. KPI 공식은 지금 고정하고, 숫자 baseline은 PA5부터 채운다

---

## 쉬운 말로 다시 설명하면

이 문서가 하는 일은 간단하다.

- 지금 있는 엔진을 갑자기 다 바꾸지 말자
- 먼저 “같은 큰 흐름 안의 체크포인트”를 따로 기록하자
- 그 기록을 기반으로 나중에 hold / partial / full exit / rebuy를 배우자
- 하지만 기존 진입 엔진과 기존 학습 데이터는 바로 깨지 않게 하자

즉 가장 중요한 건:

> 새 구조를 붙이되, 기존 구조를 부수지 않는 것

이다.

---

## 최종 한 줄 결론

> PA0의 완료 상태는
> `checkpoint layer가 기존 runtime과 학습 파이프라인을 덮어쓰지 않고,
> 별도 context / dataset / eval 체인으로 병렬 구축된다`
> 는 경계가 문서로 고정된 상태다.
