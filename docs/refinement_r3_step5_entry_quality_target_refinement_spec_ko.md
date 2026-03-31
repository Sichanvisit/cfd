# R3 Step 5 Entry Quality Target Refinement Spec

## 1. 목적

이 문서는 `R3. Semantic ML Step 3~7 refinement` 중
`Step 5. entry_quality target refinement` 전용 spec이다.

Step 4에서 split health를 정리했으므로,
이제는 `entry_quality`가 실제로 "좋은 진입"을 설명하도록
target 정의를 다시 고정해야 한다.

이 단계의 목적은:

- `timing`과 `entry_quality`를 의미상 분리하고
- 단순 수익 여부가 아니라 진입 품질을 설명 가능하게 만들고
- hold가 더 나았던 케이스, fallback-heavy 케이스, 애매한 케이스를
  positive / negative / ambiguous로 어떻게 볼지 고정하는 것이다.

## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- Step 5의 범위와 비범위
- `entry_quality` target이 무엇을 의미하는지
- 어떤 입력을 owner로 볼지
- 어떤 row를 positive / negative / ambiguous로 볼지
- 어떤 경우를 leakage 위험으로 볼지
- 구현 전에 필요한 산출물과 완료 기준

이 문서는 구현 checklist가 아니라
Step 5 구현을 위한 상위 기준 문서다.

## 3. 기준 문서

Step 5는 아래 문서를 source set으로 읽는다.

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [refinement_r3_step3_timing_target_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step3_timing_target_casebook_ko.md)
- [refinement_r3_step4_split_health_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step4_split_health_reconfirm_memo_ko.md)
- [refinement_r1_stagee_micro_calibration_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_spec_ko.md)

## 4. 현재 위치

현재 기준선은 아래와 같다.

- R2 완료
- R3 Step 3 `timing target refinement` 완료
- R3 Step 4 `split health refinement` 완료
- 다음 active step: `Step 5 entry_quality target refinement`

현재 [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)의
`_resolve_entry_quality_target(...)`는 대체로 아래 두 값에 의존한다.

- `transition_same_side_positive_count - transition_adverse_positive_count`
- `transition_quality_score`

즉 현재는:

- support delta가 높고 quality가 높으면 positive
- support delta가 음수고 quality가 낮으면 negative
- 그 외는 `None`

으로 접히는 단순 구조다.

이 방식은 baseline으로는 충분했지만,
실제 "좋은 진입"과 "나중에 hold가 더 나았던 진입"을 구분하기에는 단순할 수 있다.

## 5. 포함 범위

### 포함

- `entry_quality` target 의미 재정의
- positive / negative / ambiguous 기준 재정의
- timing과 entry_quality의 경계 정리
- `hold가 더 나았던 진입`의 해석 기준
- fallback-heavy / noisy row의 취급 기준
- direct leakage 위험 검토
- preview / evaluate에 필요한 casebook 기준

### 제외

- timing target 재정의
- split health 기준 재조정
- legacy feature tier 변경
- promotion gate live 확장
- chart / runtime execution owner 변경

## 6. owner

Step 5의 직접 owner는 아래 파일이다.

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

간접 owner / 연계:

- [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
- [train_entry_quality.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_entry_quality.py)
- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)

owner 원칙:

- `entry_quality`는 side / setup / management_profile owner를 빼앗지 않는다.
- `entry_quality`는 "이 진입이 얼마나 좋았는가"만 설명한다.
- `timing`은 지금 들어갈까 / 기다릴까를 다루고,
  `entry_quality`는 들어간 진입이 좋았는가를 다룬다.

## 7. 해석 원칙

### 7-1. timing과 entry_quality는 다르다

- `timing`:
  - 지금 진입이 낫나
  - 조금 더 기다리는 게 낫나
- `entry_quality`:
  - 이 진입이 구조적으로 괜찮은 진입이었나
  - 같은 시점의 진입들 중 품질이 높았나

즉 timing positive라고 해서 entry_quality positive가 반드시 되는 것은 아니다.

### 7-2. 단순 수익 = 좋은 진입은 아니다

좋은 진입은 아래를 함께 봐야 한다.

- same-side progress가 있었는가
- adverse move보다 유리한 진행이 있었는가
- quality score가 구조적으로 받쳐줬는가
- hold가 더 나았던 케이스인지

### 7-3. hold가 더 나았던 케이스

아래는 별도 주의 대상이다.

- 진입 자체는 틀리지 않았지만
- exit가 너무 빨랐거나
- hold가 더 유리했던 케이스

이 경우는 단순 negative보다는
`ambiguous` 또는 `quality conflict`로 보는 편이 더 맞을 수 있다.

## 8. entry_quality 관측 축

Step 5에서는 최소 아래 축을 본다.

### 8-1. support delta

- `transition_same_side_positive_count`
- `transition_adverse_positive_count`

둘의 차이를 본다.

### 8-2. transition quality

- `transition_quality_score`

이 값은 진입의 구조적 품질 축으로 해석한다.

### 8-3. target source / fallback heaviness

- fallback-heavy row는 target을 너무 공격적으로 positive/negative로 접지 않는다.
- 해석이 약한 row는 ambiguous 처리 후보로 본다.

### 8-4. hold-best / exit-too-early 계열

- 진입은 맞았지만 management가 아쉬웠던 row는
  `bad entry`가 아니라 `quality ambiguity` 후보로 본다.

## 9. 판단 규칙 방향

### positive 후보

- same-side support가 분명히 우세
- quality가 양수이며 최소 기준 이상
- fallback-heavy가 아님
- hold-best conflict가 강하지 않음

### negative 후보

- adverse support가 우세
- quality가 0 이하 또는 음수 기준 아래
- 진입 자체가 구조적으로 약했다고 볼 근거가 있음

### ambiguous 후보

- support delta가 약함
- quality가 경계 근처
- fallback-heavy
- hold-best conflict가 있음
- positive와 negative 신호가 동시에 강하게 충돌

## 10. leakage 주의

Step 5에서는 아래를 직접 feature/label 정의에 섞으면 안 된다.

- 명백한 미래 청산 결과를 직접 복사하는 규칙
- exit owner가 이미 확정된 후의 후행 상태를 좋은 진입 정의로 바로 쓰는 것
- preview에서 forbidden feature로 잡힐 수 있는 direct target leakage

즉 hold-best를 보더라도,
그 자체를 정답으로 복사하는 게 아니라
"negative로 박을지 ambiguous로 돌릴지"를 정하는 보조 신호로 써야 한다.

## 11. 산출물

Step 5에서 최소 아래 산출물을 만든다.

- Step 5 spec
- Step 5 implementation checklist
- entry_quality casebook
- target refinement memo
- preview / evaluate reconfirm memo

## 12. 구현 순서

권장 순서는 아래와 같다.

1. 현재 entry_quality baseline snapshot 고정
2. positive / negative / ambiguous casebook 작성
3. [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py) refinement
4. 테스트 보강
5. preview / evaluate 재확인
6. 문서 동기화

## 13. 완료 기준

아래를 만족하면 Step 5를 닫을 수 있다.

- `entry_quality`가 무엇인지 timing과 구분해 설명 가능하다.
- positive / negative / ambiguous 기준을 row 단위로 설명 가능하다.
- fallback-heavy / hold-best conflict를 별도 처리하는 원칙이 문서와 코드에 고정된다.
- preview / evaluate 기준으로 entry_quality 해석이 더 자연스러워진다.
- 다음 Step 6 `legacy feature tier refinement`로 넘어갈 준비가 된다.

## 14. 다음 단계

이 spec 다음에는
[refinement_r3_step5_entry_quality_target_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step5_entry_quality_target_refinement_implementation_checklist_ko.md)
를 기준으로 실제 구현에 들어간다.
