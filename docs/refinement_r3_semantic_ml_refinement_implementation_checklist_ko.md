# R3 Semantic ML Step 3~7 Refinement Implementation Checklist

## 1. 목적

이 문서는 [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)의 실행 checklist다.

R3의 목적은 semantic ML v1을
`dataset은 만들어지지만 숫자를 아직 완전히 믿기 어려움` 상태에서
`target / split / preview / audit를 근거로 다음 gate 판단이 가능함` 상태로 올리는 것이다.


## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- timing target 정의를 다시 본다
- split 건강도 기준을 코드와 문서로 맞춘다
- entry_quality target을 execution 의미와 다시 맞춘다
- legacy / mixed / modern feature tier를 정리한다
- preview / evaluate / shadow compare 기준을 다시 묶는다

### 하지 않을 것

- 규칙 엔진 owner인 `side / setup / invalidation` 의미 변경
- chart flow / Stage E 미세조정 재착수
- promotion gate 숫자 자체의 확장 결정
- bounded live rollout 실제 활성화


## 3. 입력 기준

- 마스터 계획: [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- R3 spec: [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- 구조 변경 기준: [semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md)
- 실행 계획 기준: [semantic_ml_v1_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_execution_plan_ko.md)
- promotion gate 기준: [semantic_ml_v1_promotion_gates_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_promotion_gates_ko.md)
- storage handoff 기준: [storage_semantic_flow_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\storage_semantic_flow_handoff_ko.md)
- R2 compatibility 기준: [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)

주 대상 파일:

- `ml/semantic_v1/dataset_builder.py`
- `ml/semantic_v1/dataset_splits.py`
- `ml/semantic_v1/evaluate.py`
- `ml/semantic_v1/shadow_compare.py`
- `ml/semantic_v1/train_timing.py`
- `ml/semantic_v1/train_entry_quality.py`
- `ml/semantic_v1/train_exit_management.py`


## 4. 현재 상태

현재 기준선은 아래다.

- Step 1 구조 감사: 완료
- Step 2 key 전략: 완료
- R2 storage / export / replay 정합성: 완료
- semantic ML 테스트 baseline: `27 passed`
- Step 2 `Step 3 timing target` 전용 spec / checklist: 완료
- Step 3 timing target 1차 rule refinement / casebook: 완료
- Step 3 preview / evaluate 재확인: 완료
- preview 기준 timing AUC: `0.610649 -> 0.633218` (`+0.02257`)
- 다음 active step: `Step 4 split health refinement`
- 관련 semantic 회귀:
  - `pytest tests/unit/test_semantic_v1_contracts.py tests/unit/test_semantic_v1_dataset_builder.py tests/unit/test_semantic_v1_dataset_splits.py tests/unit/test_semantic_v1_promotion_guard.py tests/unit/test_semantic_v1_runtime_adapter.py tests/unit/test_semantic_v1_shadow_compare.py tests/unit/test_check_semantic_canary_rollout.py tests/unit/test_promote_semantic_preview_to_shadow.py`
  - `27 passed`

즉 R3는 `처음부터 다시 설계`가 아니라,
이미 있는 semantic ML v1 구조를 refinement하는 단계다.


## 5. 구현 순서

### Step 1. R3 Baseline Snapshot 고정

목표:

- 현재 semantic ML baseline을 문서와 테스트 기준으로 다시 고정한다.

확인 포인트:

- 현재 target family
  - `timing_now_vs_wait`
  - `entry_quality`
  - `exit_management`
- 현재 split / evaluate / shadow owner
- 현재 promotion gate 연결 관계
- 현재 테스트 기준선

완료 기준:

- R3 시작 시점 baseline이 문서로 남는다.
- 다음 step에서 무엇이 target 문제이고 무엇이 split 문제인지 구분 가능하다.


### Step 2. Step 3 Timing Target 전용 spec / checklist 작성

목표:

- R3 전체 중 첫 active step인 `timing target refinement`를 별도 문서로 세분화한다.

최소 포함 항목:

- 현재 timing target fold 규칙
- 대표 positive / negative / ambiguous row 샘플
- fallback-heavy / clean row 구분
- 사람이 해석 가능한 casebook

완료 기준:

- `Step 3 timing`만 떼어 구현 가능한 문서가 있다.

전용 문서:

- [refinement_r3_step3_timing_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_spec_ko.md)
- [refinement_r3_step3_timing_target_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_implementation_checklist_ko.md)


### Step 3. Timing Target Refinement 구현

목표:

- `timing_now_vs_wait` 정의를 실제 의미에 맞게 다시 고정한다.

최소 작업:

- 현재 timing target 규칙 분해
- sample row casebook 정리
- 필요 시 target fold rule 조정
- 관련 테스트 보강
- preview 재확인

완료 기준:

- timing target을 사람이 row 단위로 설명 가능하다.
- preview가 최소 무작위보다 의미 있게 동작한다.

현재 1차 반영:

- `_resolve_timing_target_reason` 추가
- count 우세와 fallback / quality가 강하게 충돌하는 row를 `conflict_veto`로 `None` 처리
- 전용 casebook 작성:
  - [refinement_r3_step3_timing_target_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_casebook_ko.md)
- preview / evaluate 재확인 메모 작성:
  - [refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md)

현재 판정:

- Step 3는 1차 refinement + preview/evaluate reconfirm까지 완료
- 다음 active step은 `Step 4. split health refinement`


### Step 4. Split Health 전용 spec / checklist 작성 후 구현

목표:

- split health를 문서와 코드 기준으로 같이 잠근다.

최소 작업:

- time split 기준 재확인
- symbol holdout / regime holdout 기준 재확인
- validation / test minority health 기준 정의
- 경고와 실패의 경계 정의
- 관련 테스트 / evaluate report 정리

완료 기준:

- split 건강도 기준이 문서와 코드에 같이 반영된다.


### Step 5. Entry Quality Target 전용 spec / checklist 작성 후 구현

목표:

- `entry_quality`가 실제 “좋은 진입”을 설명하게 다시 맞춘다.

최소 작업:

- positive / negative / ambiguous 사례표 정리
- timing과 entry_quality 경계 정리
- leakage 점검
- 관련 target rule 및 테스트 보강

완료 기준:

- 사람이 납득 가능한 entry_quality 정의가 문서와 코드로 고정된다.


### Step 6. Legacy Feature Tier 전용 spec / checklist 작성 후 구현

목표:

- legacy / mixed / modern source tier 처리를 builder 기준으로 설명 가능하게 만든다.

최소 작업:

- `enabled` / `observed_only` 경계 정리
- all-missing feature 처리 기준 정리
- dropped feature reason과 summary 일관성 확인
- 관련 테스트 보강

완료 기준:

- feature tier policy가 문서와 코드로 일치한다.


### Step 7. Preview / Audit 전용 spec / checklist 작성 후 구현

목표:

- Step 3~6을 반영한 preview / audit를 다시 돌려 R4로 넘길 근거를 만든다.

최소 작업:

- 세 target 재학습 또는 preview 실행
- join health 재확인
- split health 재확인
- leakage / calibration 재확인
- shadow compare 기준 정리

완료 기준:

- preview / audit 결과를 기준으로 다음 gate 판단이 가능하다.


### Step 8. 테스트 묶음 확인

권장 최소 테스트:

- `pytest tests/unit/test_semantic_v1_dataset_builder.py`
- `pytest tests/unit/test_semantic_v1_dataset_splits.py`
- `pytest tests/unit/test_semantic_v1_evaluate.py`
- `pytest tests/unit/test_semantic_v1_shadow_compare.py`
- `pytest tests/unit/test_semantic_v1_promotion_guard.py`

상황별 추가:

- `pytest tests/unit/test_check_semantic_canary_rollout.py`
- `pytest tests/unit/test_promote_semantic_preview_to_shadow.py`
- step별 신규 테스트

완료 기준:

- R3 관련 target / split / preview / audit 테스트가 현재 구조를 깨지 않는다는 근거가 있다.


### Step 9. 문서 동기화

목표:

- R3 spec, checklist, 마스터 refinement 문서가 현재 구현 상태와 맞게 유지되게 한다.

완료 기준:

- R3 문서만 읽어도 현재 active step과 다음 착수점이 보인다.


## 6. Done Definition

아래가 모두 만족되면 R3를 닫을 수 있다.

- timing / entry_quality / exit_management target 정의가 설명 가능하다.
- split health가 promotion block 사유 없이 해석 가능하다.
- legacy feature tier 처리가 문서와 코드로 고정된다.
- preview / audit / shadow compare 결과를 다음 gate에 넘길 수 있다.


## 7. 다음 단계

R3 전체 checklist를 고정한 뒤,
실제 첫 구현은 `Step 2 -> Step 3 timing target refinement` 순서로 시작한다.
