# R3 Step 6 Legacy Feature Tier Refinement Implementation Checklist

## 1. 목적

이 문서는
[refinement_r3_step6_legacy_feature_tier_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step6_legacy_feature_tier_refinement_spec_ko.md)
의 실행 checklist다.

목표는 `legacy / mixed / modern` source에서
semantic dataset builder가 feature tier를 어떤 기준으로 드롭/유지/관측하는지
설명 가능하게 고정하는 것이다.

## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- current feature tier baseline snapshot 고정
- legacy / mixed / modern casebook 작성
- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py) tier policy refinement
- dropped feature reason surface 보강
- 테스트 보강
- preview / evaluate 재확인
- 문서 동기화

### 하지 않을 것

- timing / entry_quality / exit_management target 재정의
- split health 기준 재변경
- promotion gate live 확장
- chart / runtime execution rule 변경

## 3. 입력 기준

기준 문서:

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_step6_legacy_feature_tier_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step6_legacy_feature_tier_refinement_spec_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)

중요 파일:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)
- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)

## 4. 현재 상태

현재 baseline은 아래와 같다.

- `legacy`
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = observed_only`
- `modern`
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = enabled`
- `mixed`
  - 현재는 `modern`과 같은 정책으로 들어간다

그리고 current builder는
all-missing column을 dropped feature로 기록하되,
source_generation과 tier를 섞어 reason을 남긴다.

Step 6에서 정리할 핵심은:

- mixed를 지금처럼 `enabled`로 계속 둘지
- modern all-missing을 더 강하게 surface할지
- summary / metrics에서 feature tier 계약을 더 직접적으로 보일지

## 5. 구현 순서

### Step 1. Feature Tier Baseline Snapshot 고정

목표:

- 현재 `_feature_tier_policy`, `_resolve_dataset_feature_policy` 기준을 문서로 먼저 고정한다.

해야 할 일:

- current tier policy 메모
- dropped feature reason vocabulary 메모
- current preview / summary 기준 확인

완료 기준:

- Step 6 시작 기준선이 문서로 남아 있다.

### Step 2. Legacy / Mixed / Modern Casebook 작성

목표:

- generation별 대표 케이스를 문서로 정리한다.

해야 할 일:

- legacy all-missing trace-quality 예시
- mixed source 예시
- modern source 예시
- 어떤 케이스를 warning / observed-only / drop으로 볼지 정리

완료 기준:

- generation별 처리 원칙이 row/summary 예시로 설명 가능하다.

### Step 3. dataset_builder Tier Policy Refinement

목표:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)의 feature tier 처리를 설명 가능한 형태로 refine한다.

해야 할 일:

- mixed tier 처리 보정 여부 결정
- dropped feature reason 개선
- summary / manifest에서 feature tier visibility 보강 여부 반영

완료 기준:

- tier policy가 코드 기준으로 더 명확해진다.

### Step 4. 테스트 보강

목표:

- feature tier 계약을 테스트로 잠근다.

최소 대상:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)

완료 기준:

- legacy / mixed / modern 처리 차이가 테스트로 고정된다.

### Step 5. Preview / Evaluate 재확인

목표:

- Step 6 변경이 preview에서 어떤 영향을 주는지 확인한다.

해야 할 일:

- explicit baseline pair 또는 current preview dataset로 재확인
- dropped feature / feature count / split health / leakage 영향 확인

완료 기준:

- no-regression 또는 explainable regression 상태가 확인된다.

### Step 6. 문서 동기화

목표:

- Step 6 spec / checklist / casebook / reconfirm memo / 마스터 문서를 맞춘다.

완료 기준:

- 문서만 읽어도 Step 6이 어디까지 끝났는지 보인다.

## 6. Done Definition

아래를 만족하면 Step 6을 닫을 수 있다.

- current feature tier baseline snapshot이 있다.
- generation별 casebook이 있다.
- builder tier refinement가 코드에 반영된다.
- 관련 테스트가 보강된다.
- preview / evaluate reconfirm memo가 있다.
- 다음 active step이 `Step 7 preview / audit refinement`로 보인다.

## 7. 다음 단계

이 checklist 기준으로 구현이 끝나면,
R3의 다음 active step은 `Step 7 preview / audit refinement`가 된다.
