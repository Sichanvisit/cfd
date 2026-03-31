# R3 Step 3 Timing Target Refinement Implementation Checklist

## 1. 목적

이 문서는 [refinement_r3_step3_timing_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_spec_ko.md)의 실행 checklist다.

Step 3의 목적은
`timing_now_vs_wait` target이 실제 의미에 맞게 접히는지 다시 확인하고,
필요하면 fold rule과 테스트를 함께 조정하는 것이다.


## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- 현재 timing fold 규칙 분해
- representative sample row casebook 작성
- positive / negative / ambiguous 경계 고정
- 필요 시 `_resolve_timing_target`, `_resolve_timing_margin` 조정
- 관련 테스트 보강
- preview 또는 evaluate 기준으로 후속 영향 확인

### 하지 않을 것

- split health 기준 변경
- `entry_quality` target 조정
- promotion gate 조정
- chart / execution / runtime owner 변경


## 3. 입력 기준

- 상위 spec: [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- Step 3 spec: [refinement_r3_step3_timing_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_refinement_spec_ko.md)
- 구조 변경 기준: [semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md)
- 실행 계획 기준: [semantic_ml_v1_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_execution_plan_ko.md)

주 대상 파일:

- `ml/semantic_v1/dataset_builder.py`
- `tests/unit/test_semantic_v1_dataset_builder.py`
- 필요 시
  - `ml/semantic_v1/evaluate.py`
  - `ml/semantic_v1/train_timing.py`


## 4. 현재 기준선

현재 기준선은 아래다.

- `_resolve_timing_target`가 count delta 우선, quality tie-break 보조 규칙을 쓴다.
- tie-break threshold는 `TIMING_TIE_QUALITY_THRESHOLD = 0.0005`
- 기존 timing 관련 테스트는 이미 일부 잠겨 있다.
- 다음 목표는 `사람이 timing target을 설명 가능한 상태`로 올리는 것이다.


## 5. 구현 순서

### Step 1. Current Fold Rule Snapshot

목표:

- 현재 timing target fold 규칙을 문장과 표로 다시 적는다.

최소 확인 항목:

- `same_side_positive_count`
- `adverse_positive_count`
- `transition_positive_count`
- `transition_negative_count`
- `transition_quality_score`
- `semantic_target_source`
- `_resolve_timing_target`
- `_resolve_timing_margin`

완료 기준:

- 현재 규칙을 코드 안 열고도 설명 가능하다.


### Step 2. Sample Row Casebook 작성

목표:

- representative sample row를 positive / negative / ambiguous / fallback-heavy로 분류한다.

최소 분류:

- clear positive
- clear negative
- tie but quality agrees
- tie and quality weak
- fallback-heavy disagreement

완료 기준:

- 사람이 봐도 납득 가능한 row 사례표가 있다.


### Step 3. Timing Target Interpretation Rule 확정

목표:

- 지금 진입 vs 조금 기다림의 경계를 문서로 잠근다.

최소 확인 항목:

- positive의 의미
- negative의 의미
- ambiguous의 의미
- fallback-heavy row 처리 원칙
- censored / unknown row 제외 기준

완료 기준:

- positive / negative / ambiguous 경계가 문서로 고정된다.


### Step 4. Dataset Builder Rule 조정

목표:

- 필요하면 실제 fold rule을 코드에 반영한다.

최소 작업:

- `_resolve_timing_target`
- `_resolve_timing_margin`
- 필요 시 tie-break threshold 또는 fallback rule 조정

주의:

- 이 단계에서 `entry_quality`나 `exit_management` 규칙은 건드리지 않는다.

완료 기준:

- Step 3에서 정한 해석이 코드와 일치한다.


### Step 5. 테스트 보강

목표:

- timing target 해석이 테스트로 잠기게 한다.

권장 최소 테스트:

- tie-break positive
- tie-break negative
- weak quality -> `None`
- clear count delta positive
- fallback-heavy disagreement
- semantic source 없는 row fallback 동작

완료 기준:

- timing target 관련 회귀 테스트가 새 규칙을 고정한다.


### Step 6. Preview / Evaluate 영향 확인

목표:

- timing target 조정이 preview 관점에서 의미가 있는지 확인한다.

최소 확인 항목:

- preview 결과가 최소 무작위보다 낫거나
- 아직 약해도 target 정의가 더 설명 가능해졌는지
- 다음 owner가 split인지 model인지 분리 가능한지

완료 기준:

- Step 4 결과를 다음 단계로 넘길 수 있다.


### Step 7. 문서 동기화

목표:

- Step 3 spec, Step 3 checklist, R3 전체 문서가 현재 상태와 맞게 유지되게 한다.

완료 기준:

- Step 3 문서만 읽어도 현재 상태와 다음 착수점이 보인다.


## 6. Done Definition

아래가 모두 만족되면 Step 3을 닫을 수 있다.

- timing target fold 규칙이 문서와 코드로 설명 가능하다.
- representative sample row casebook이 있다.
- positive / negative / ambiguous 경계가 문서화돼 있다.
- timing 관련 테스트가 현재 규칙을 잠근다.
- preview / evaluate 기준으로 다음 owner를 분리할 수 있다.


## 7. 다음 단계

Step 3이 닫히면 다음은
`Step 4 split health refinement`
전용 spec / checklist로 넘어간다.
