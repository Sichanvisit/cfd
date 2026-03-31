# R3 Step 5 Entry Quality Target Refinement Implementation Checklist

## 1. 목적

이 문서는
[refinement_r3_step5_entry_quality_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_entry_quality_target_refinement_spec_ko.md)
의 실행 checklist다.

목표는 `entry_quality` target이

- timing과 구분되고
- row 단위로 설명 가능하며
- preview / audit에서 해석 가능한 형태

가 되게 만드는 것이다.

## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- current entry_quality baseline snapshot 고정
- positive / negative / ambiguous casebook 작성
- hold-best / fallback-heavy conflict 규칙 반영
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py) target fold refinement
- 테스트 보강
- preview / evaluate 재확인
- 문서 동기화

### 하지 않을 것

- timing target 다시 변경
- split health 기준 다시 변경
- legacy feature tier 변경
- promotion gate live 확장
- chart / runtime execution rule 변경

## 3. 입력 기준

기준 문서:

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_step4_split_health_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_reconfirm_memo_ko.md)
- [refinement_r3_step5_entry_quality_target_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_entry_quality_target_refinement_spec_ko.md)

주 대상 파일:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [train_entry_quality.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_entry_quality.py)

관련 테스트:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)
- 필요 시
  - [test_semantic_v1_shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_shadow_compare.py)
  - [test_semantic_v1_promotion_guard.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_promotion_guard.py)

## 4. 현재 상태

현재 baseline은 아래와 같다.

- `support_delta = transition_same_side_positive_count - transition_adverse_positive_count`
- `quality = transition_quality_score`
- positive:
  - `support_delta >= 1`
  - `quality >= threshold`
- negative:
  - `support_delta < 0 and quality <= 0`
  - 또는 `support_delta <= 0 and quality <= negative_threshold`
- 그 외는 `None`

즉 아직 `hold-best conflict`, `fallback-heavy`, `ambiguous quality conflict` 처리가 약한 상태다.

## 5. 구현 순서

### Step 1. Entry Quality Baseline Snapshot 고정

목표:

- 현재 target fold 규칙과 preview baseline을 문서로 먼저 고정한다.

해야 할 일:

- current `_resolve_entry_quality_target(...)` 메모화
- 현재 threshold와 regime 예외 정리
- current preview metrics 위치 고정

완료 기준:

- Step 5 시작 시점 baseline을 문장으로 설명할 수 있다.

### Step 2. Entry Quality Casebook 작성

목표:

- 어떤 row가 positive / negative / ambiguous 후보인지 실제 예시로 묶는다.

해야 할 일:

- support_delta 우세 positive 예시
- adverse 우세 negative 예시
- quality conflict 예시
- fallback-heavy 예시
- hold-best conflict 예시

완료 기준:

- casebook만 봐도 어떤 row를 어디로 접어야 하는지 설명 가능하다.

### Step 3. dataset_builder Target Fold Refinement

목표:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)의 `entry_quality` fold를 더 설명 가능하게 만든다.

해야 할 일:

- helper reason 분리
- ambiguous conflict 처리
- fallback-heavy / hold-best conflict 처리
- margin 계산도 target 의미와 맞게 정리

완료 기준:

- `entry_quality` target fold가 reason 단위로 설명 가능하다.

### Step 4. 테스트 보강

목표:

- 새 fold 규칙을 회귀로 잠근다.

최소 대상:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)

완료 기준:

- positive / negative / ambiguous conflict 규칙이 테스트로 잠긴다.

### Step 5. Preview / Evaluate 재확인

목표:

- Step 5 변경 후 entry_quality preview를 다시 보고 해석한다.

해야 할 일:

- explicit baseline pair 또는 current preview dataset로 재학습
- entry_quality target의 split health / auc / calibration 재확인
- timing / exit_management와의 상대 해석도 같이 본다

완료 기준:

- Step 5 변경이 preview에서 설명 가능한 방향인지 확인된다.

### Step 6. 문서 동기화

목표:

- Step 5 spec / checklist / casebook / reconfirm memo / 마스터 문서를 맞춘다.

완료 기준:

- 문서만 읽어도 Step 5가 어디까지 됐는지 보인다.

## 6. Done Definition

아래를 만족하면 Step 5를 닫을 수 있다.

- `entry_quality`가 timing과 구분돼 설명 가능하다.
- positive / negative / ambiguous casebook이 있다.
- target fold refinement가 코드에 반영됐다.
- 테스트가 추가 또는 보강됐다.
- preview / evaluate 재확인 메모가 있다.
- 다음 active step을 `Step 6 legacy feature tier refinement`로 넘길 수 있다.

## 7. 다음 단계

이 checklist 기준으로 구현이 끝나면
R3의 다음 active step은
`Step 6 legacy feature tier refinement`가 된다.
