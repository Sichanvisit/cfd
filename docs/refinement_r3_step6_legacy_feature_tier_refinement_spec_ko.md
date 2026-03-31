# R3 Step 6 Legacy Feature Tier Refinement Spec

## 1. 목적

이 문서는 `R3. Semantic ML Step 3~7 refinement` 중
`Step 6. legacy feature tier refinement` 전용 spec이다.

Step 5에서 `entry_quality` target 계약을 정리했으므로,
이제는 `legacy / mixed / modern` source가 섞여도
semantic dataset builder가 어떤 feature를

- 그대로 쓸지
- 있어야만 쓰는지
- 비어 있으면 조용히 드롭할지

를 문서와 코드 기준으로 같이 설명 가능하게 만드는 단계다.

## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- Step 6의 포함 범위와 제외 범위
- `source_generation` 별 feature tier policy
- `semantic_input_pack` / `trace_quality_pack`의 owner와 의미
- all-missing feature를 `warning`, `drop`, `fail` 중 어디로 볼지
- Step 6의 구현 산출물과 완료 기준

이 문서는 구현 checklist가 아니라
Step 6을 어떤 기준으로 구현할지 잠그는 상위 기준 문서다.

## 3. 기준 문서

Step 6은 아래 문서를 source set으로 읽는다.

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)
- [refinement_r3_step5_preview_evaluate_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_preview_evaluate_reconfirm_memo_ko.md)
- [storage_semantic_flow_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\storage_semantic_flow_handoff_ko.md)

## 4. 현재 위치

현재 기준 상태는 아래와 같다.

- R2 저장 / export / replay 정합성 완료
- R3 Step 3 timing target refinement 완료
- R3 Step 4 split health refinement 완료
- R3 Step 5 entry_quality target refinement 완료
- 다음 active step: `Step 6 legacy feature tier refinement`

현재 [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py) 에는
이미 아래의 baseline tier policy가 있다.

- `legacy`
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = observed_only`
- `modern` / `mixed`
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = enabled`

하지만 지금은 아직 아래가 충분히 닫히지 않았다.

- mixed를 언제 legacy처럼 볼지
- all-missing trace-quality를 언제 조용히 드롭하고 언제 경고로 볼지
- summary / metrics / preview에서 dropped feature reason을 어디까지 surface할지

## 5. 포함 범위

### 포함

- `source_generation` 해석 기준 refinement
- `semantic_input_pack` / `trace_quality_pack` tier policy refinement
- all-missing feature 처리 기준 refinement
- dropped feature reason vocabulary 정리
- summary / manifest / metrics에서의 surface 기준 정리
- preview 재확인 시 feature tier 영향 확인

### 제외

- timing / entry_quality / exit_management target 정의 변경
- split health 기준 변경
- promotion gate live 확장
- chart / runtime / execution owner 변경

## 6. 직접 owner

Step 6의 직접 owner는 아래 파일이다.

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

간접 owner / 확인 대상:

- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- [test_semantic_v1_training.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_training.py)

## 7. 해석 원칙

### 7-1. feature tier는 target owner를 바꾸지 않는다

Step 6은 feature를 어떤 방식으로 읽고 버릴지 정하는 단계지,

- side
- setup
- invalidation
- execution owner

를 바꾸는 단계가 아니다.

즉 Step 6은 semantic ML이 어떤 feature를
안전하게 쓸 수 있는지 정리하는 단계다.

### 7-2. legacy에서는 trace-quality를 fail 대신 observed-only로 본다

legacy source는 원래 trace-quality 필드가 없거나,
거의 전부 비어 있는 경우가 많다.

그래서 legacy에서 trace-quality all-missing은
즉시 실패가 아니라 `observed_only drop`로 처리하는 것이 baseline이다.

### 7-3. modern에서는 silent drop보다 signal을 남기는 쪽이 우선이다

modern source에서 trace-quality pack이 전부 비어 있다면
그건 단순 legacy 제약이 아니라 이상 신호일 수 있다.

따라서 Step 6에서는 modern all-missing을
legacy와 같은 수준으로 취급할지,
warning을 더 강하게 surface할지를 정해야 한다.

### 7-4. mixed는 무조건 modern 취급하지 않는다

mixed는 이름 그대로 `legacy + modern`이 섞인 상태다.

따라서 mixed에서 trace-quality all-missing이 발생했을 때
그걸 무조건 이상으로 보지 않고,
실제 feature source 구성을 보고 `observed_only`에 가깝게 볼지
부분 warning으로 올릴지를 정리해야 한다.

## 8. Step 6에서 봐야 할 축

### 8-1. source_generation

- `legacy`
- `mixed`
- `modern`
- `unknown`

이 값이 실제 dataset summary와 preview metrics에서
일관되게 해석되는지 확인한다.

### 8-2. feature pack tier

- `semantic_input_pack`
- `trace_quality_pack`

각 pack이 `enabled` / `observed_only`일 때
무슨 의미인지 다시 문서화한다.

### 8-3. dropped feature reason

현재 대표 reason은 아래와 같다.

- `all_missing_feature`
- `{source_generation}_{tier}_all_missing`

Step 6에서는 이 reason vocabulary가
문서, summary, metrics에서 읽기 좋게 설명 가능한지 본다.

### 8-4. preview 영향

feature tier 조정이 실제 preview에서

- row count
- feature count
- dropped feature columns
- split health
- leakage audit

에 어떤 영향을 주는지 확인해야 한다.

## 9. 권장 방향

### 유지할 것

- legacy
  - `semantic_input_pack = enabled`
  - `trace_quality_pack = observed_only`

### Step 6에서 정리할 것

- mixed source의 `trace_quality_pack`를 정말 `enabled`로 둘지
- modern all-missing trace-quality를 더 강한 warning으로 surface할지
- dataset summary와 training metrics에 dropped feature tier 정보를 더 직접 노출할지

### 지금 하지 않을 것

- target fold 변경
- split cutoff 변경
- promotion gate threshold 변경

## 10. 산출물

Step 6에서 최소 아래 산출물을 만든다.

- Step 6 spec
- Step 6 implementation checklist
- legacy/mixed/modern feature tier casebook
- Step 6 refinement memo
- preview / evaluate reconfirm memo

## 11. 구현 순서

권장 순서는 아래와 같다.

1. current feature tier baseline snapshot 고정
2. legacy / mixed / modern casebook 작성
3. `dataset_builder.py` feature tier refinement
4. 테스트 보강
5. preview / evaluate 재확인
6. 문서 동기화

## 12. 완료 기준

아래를 만족하면 Step 6을 닫을 수 있다.

- `source_generation` 별 feature tier 정책을 문장으로 설명 가능하다.
- dropped feature reason을 summary / metrics / preview 기준으로 함께 설명할 수 있다.
- legacy / mixed / modern에서 all-missing feature가 어떻게 처리되는지 문서와 코드가 맞다.
- preview / evaluate 기준으로 no-regression 또는 explainable regression 상태다.
- 다음 Step 7 `preview / audit refinement`로 넘어갈 준비가 된다.

## 13. 다음 단계

이 spec 다음에는
[refinement_r3_step6_legacy_feature_tier_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step6_legacy_feature_tier_refinement_implementation_checklist_ko.md)
를 기준으로 실제 구현에 들어간다.
