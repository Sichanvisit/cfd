# R3 Step 4 Split Health Refinement Implementation Checklist

## 1. 목적

이 문서는
[refinement_r3_step4_split_health_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_refinement_spec_ko.md)
의 실행 checklist다.

목표는 split health를

- 문서로 설명 가능하고
- 코드로 surface 가능하고
- preview / audit가 실제로 읽을 수 있는 상태

로 만드는 것이다.

## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- split baseline snapshot 고정
- symbol / regime / label balance casebook 작성
- split health surface 기준 추가 또는 보강
- evaluate report 해석 기준 정리
- 테스트와 문서 동기화

### 하지 않을 것

- timing target 규칙 다시 변경
- entry_quality target 정의 변경
- legacy tier policy 변경
- promotion gate live expansion 결정
- chart / runtime entry rule 조정

## 3. 입력 기준

기준 문서:

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_preview_evaluate_reconfirm_memo_ko.md)
- [refinement_r3_step4_split_health_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_refinement_spec_ko.md)

주 대상 파일:

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

관련 테스트:

- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- [test_semantic_v1_shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_shadow_compare.py)
- [test_semantic_v1_promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_promotion_guard.py)

## 4. 현재 상태

현재 기준선:

- R2 완료
- R3 Step 3 완료
- timing preview AUC 개선 확인
- 다음 active step은 split health refinement

즉 이번 단계는 "target이 맞는가"보다
"이 target을 어떤 split에서 믿을 수 있는가"를 정리하는 단계다.

## 5. 구현 순서

### Step 1. Split Baseline Snapshot 고정

목표:

- 현재 split / evaluate / preview 기준선을 문서와 샘플 결과로 먼저 고정한다.

해야 할 일:

- current split outputs 위치 확인
- latest preview / evaluate에서 읽는 split 관련 수치 확인
- split health에 직접 연결되는 현재 config / defaults 메모화

완료 기준:

- Step 4 시작 시점 baseline을 문서로 설명할 수 있다.

### Step 2. Split Health Casebook 작성

목표:

- split 문제를 실제 샘플 단위로 분리한다.

해야 할 일:

- symbol coverage casebook
- regime coverage casebook
- label balance casebook
- minority collapse / holdout weakness 예시 수집

완료 기준:

- split issue를 추상 문장이 아니라 row / count / report 기준으로 설명할 수 있다.

### Step 3. dataset_splits Refinement

목표:

- [dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_splits.py)가 split health를 더 직접 surface하게 만든다.

해야 할 일:

- split summary 보강
- symbol / regime / label counts surface 보강
- warning / failure 후보를 잡을 수 있는 최소 metric 추가

완료 기준:

- split helper만 읽어도 coverage health를 파악할 수 있다.

### Step 4. evaluate Report Refinement

목표:

- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)에서 split health를 preview / audit와 연결해 읽게 만든다.

해야 할 일:

- split health section 추가 또는 보강
- metric interpretation과 split weakness를 같이 surface
- leakage / stale / minority weakness 경고 기준 정리

완료 기준:

- preview / evaluate 결과만으로 split weakness를 해석할 수 있다.

### Step 5. 테스트 보강

목표:

- split health contract가 회귀로 잠기게 만든다.

최소 대상:

- [test_semantic_v1_dataset_splits.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_splits.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- 필요 시
  - [test_semantic_v1_shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_shadow_compare.py)
  - [test_semantic_v1_promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_promotion_guard.py)

완료 기준:

- split health 관련 경고 / 실패 / pass 기준이 테스트로 잠긴다.

### Step 6. Preview / Audit 재확인

목표:

- split health refinement 후 preview / evaluate를 다시 보고 해석한다.

해야 할 일:

- explicit baseline pair로 preview 재실행
- split health report 확인
- Step 3 timing improvement가 split weakness 때문에 착시가 아닌지 확인

완료 기준:

- split health를 반영한 preview 해석 메모가 남는다.

### Step 7. 문서 동기화

목표:

- Step 4 spec / checklist / memo / 마스터 문서를 현재 상태에 맞춘다.

완료 기준:

- 문서만 읽어도 Step 4가 어디까지 됐는지 보인다.

## 6. Done Definition

아래를 만족하면 Step 4를 닫을 수 있다.

- split baseline snapshot이 있다.
- split health casebook이 있다.
- `dataset_splits`와 `evaluate`가 split weakness를 surface한다.
- split health 테스트가 추가 또는 보강됐다.
- preview / audit 재확인 메모가 있다.
- 다음 active step을 `Step 5 entry_quality target refinement`로 넘길 수 있다.

## 7. 다음 단계

이 checklist 기준으로 구현이 끝나면
R3의 다음 active step은
`Step 5 entry_quality target refinement`가 된다.
