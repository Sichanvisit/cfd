# R3 Step 3 Timing Target Refinement Spec

## 1. 목적

이 문서는 `R3. Semantic ML Step 3~7 refinement` 중
첫 active step인 `Step 3. timing target refinement` 전용 spec이다.

목표는 `timing_now_vs_wait` target이
현재 semantic compact dataset과 replay label 구조를 기준으로
실제 의미와 같은 방향으로 접히는지 다시 고정하는 것이다.

쉽게 말하면,

- "지금 진입하는 게 유리한가"
- "1~2 bar 기다리는 게 유리한가"

를 현재 target fold rule이 정말 올바르게 표현하는지 다시 점검하는 단계다.


## 2. 이 문서의 역할

이 문서는 아래를 고정한다.

- Step 3의 범위와 제외 범위
- timing target의 현재 fold 규칙
- 무엇을 positive / negative / ambiguous로 볼지의 기준축
- 어떤 row를 casebook으로 모아야 하는지
- Step 3 완료 기준

이 문서는 구현 checklist가 아니라,
`timing target refinement`의 설계 기준을 잠그는 문서다.


## 3. 기준 문서

- [refinement_r3_semantic_ml_refinement_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_spec_ko.md)
- [refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_semantic_ml_refinement_implementation_checklist_ko.md)
- [semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md)
- [semantic_ml_v1_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_v1_execution_plan_ko.md)
- [refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r2_semantic_dataset_builder_compatibility_memo_ko.md)


## 4. 범위

### 포함 범위

- 현재 timing target fold 규칙 분해
- `same_side_positive_count`, `adverse_positive_count`, `transition_quality_score` 축 해석
- fallback-heavy row와 clean row 분리
- positive / negative / ambiguous sample row casebook
- preview가 왜 낮은지의 원인이 model이 아니라 target인지 점검

### 제외 범위

- split health 기준 변경
- `entry_quality` / `exit_management` target 정의 변경
- promotion gate 변경
- chart / execution rule 변경


## 5. 현재 owner와 대상 파일

주 owner:

- [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py)

관련 확인 파일:

- [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)
- 필요 시 preview / evaluate 관련 파일
  - [evaluate.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\evaluate.py)
  - [train_timing.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\train_timing.py)


## 6. 현재 구현 기준선

현재 timing target fold는 [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py) 기준으로 아래와 같다.

- tie-break threshold
  - `TIMING_TIE_QUALITY_THRESHOLD = 0.0005`
- count delta
  - `transition_same_side_positive_count - transition_adverse_positive_count`
- fallback delta
  - `transition_positive_count - transition_negative_count`
- quality
  - `transition_quality_score`

현재 핵심 함수:

- `_resolve_timing_target`: [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L674)
- `_resolve_timing_margin`: [dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\dataset_builder.py#L690)

현재 로직 요약:

1. `count_delta > 0`이면 positive
2. `count_delta < 0`이면 negative
3. count tie면 `fallback_delta`와 `quality`가 같은 방향일 때만 positive/negative
4. 그것도 아니면 `None`

즉 현재 timing target은
`semantic target source`가 있는 row에 대해
count 우선, quality tie-break 보조 규칙으로 접히고 있다.


## 7. 왜 지금 timing을 먼저 보는가

[semantic_ml_structure_change_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\semantic_ml_structure_change_plan_ko.md) 기준으로
현재 가장 먼저 깨졌을 가능성이 큰 축이 timing이다.

문서상 핵심 문제는 이거다.

- AUC가 매우 낮았음
- model capacity보다 target 정의 문제일 가능성이 큼
- "지금 진입"과 "조금 기다림"의 경계가 사람 체감과 어긋날 수 있음

즉 Step 3은
`모델을 더 학습시키기 전에 정답이 맞는지 다시 보는 단계`다.


## 8. Step 3에서 답해야 할 질문

### 8-1. positive의 의미

positive는 단순히 "결국 맞았다"가 아니라,
`wait보다 now가 유리했다`를 뜻해야 한다.

그래서 아래를 구분해야 한다.

- 지금 진입이 실제로 유리했던 row
- 결과는 좋아도 1~2 bar 기다렸어도 비슷했을 row
- 지금 진입은 애매하고 wait이 더 나았던 row

### 8-2. negative의 의미

negative는 단순 loss가 아니라,
`지금 진입보다 wait이 낫거나, 지금 진입이 너무 성급했다`를 뜻해야 한다.

### 8-3. ambiguous의 의미

아래는 `None` 또는 제외 후보로 보는 게 맞다.

- count tie + quality 미약
- fallback-heavy row인데 방향 합의가 약함
- censored / unknown이 많아서 timing을 확정하기 어려움

### 8-4. fallback-heavy row 처리

fallback-heavy row는 지금 구조상 특히 중요하다.

현재 Step 3의 핵심 확인 포인트는:

- fallback-heavy인데 timing positive로 접히는 row가 과한지
- clean row와 같은 기준으로 접는 게 맞는지
- quality score가 noise를 positive로 과신하게 만들지 않는지


## 9. casebook 분류 기준

Step 3 구현 전 casebook은 최소 아래 유형을 모아야 한다.

### Group A. clear positive

- `same_side_positive_count > adverse_positive_count`
- quality도 같은 방향
- 사람이 봐도 now가 유리하다고 납득 가능한 row

### Group B. clear negative

- `same_side_positive_count < adverse_positive_count`
- quality도 반대 방향
- 사람이 봐도 wait 또는 반대 전개가 더 낫다고 보이는 row

### Group C. tie but quality agrees

- count tie
- fallback delta와 quality가 같은 방향
- 현재 규칙상 positive/negative가 될 수 있는 row

이 그룹이 Step 3의 핵심 검증 지점이다.

### Group D. tie and quality weak

- count tie
- quality 절대값이 작음
- 현재 규칙상 `None`

이 그룹은 ambiguous / 제외 기준을 문서화하는 데 필요하다.

### Group E. fallback-heavy disagreement

- fallback delta는 크지만
- semantic count 또는 quality와 잘 안 맞는 row

이 그룹은 "지금 진입" 정의가 틀어지는 대표 위험군이다.


## 10. 테스트 기준선

현재 timing target 관련 테스트는 [test_semantic_v1_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_semantic_v1_dataset_builder.py)에서 이미 일부 잠겨 있다.

핵심 기준:

- tie-break가 fallback과 quality가 같은 방향일 때만 동작
- quality가 약하면 `None`
- clear positive count는 positive

즉 Step 3은 이 기존 테스트를 깨뜨릴지 유지할지 판단하는 단계이기도 하다.


## 11. 산출물

Step 3이 끝나면 최소 아래 산출물이 있어야 한다.

- timing target casebook
- timing target fold rule memo
- 관련 테스트 보강 또는 수정
- 필요 시 preview / evaluate 재실행 결과 메모


## 12. 완료 기준

Step 3은 아래 조건을 만족하면 닫을 수 있다.

- timing target 정의를 사람이 row 단위로 설명 가능하다.
- positive / negative / ambiguous 경계가 문서로 남는다.
- fallback-heavy row와 clean row를 어떻게 다룰지 설명 가능하다.
- preview가 최소 무작위보다 의미 있게 동작하거나,
  그렇지 않다면 target 외의 다음 owner가 어디인지 분리 가능하다.


## 13. 다음 단계

이 spec을 고정한 뒤 실제 구현은
`Step 3 timing target refinement implementation checklist`
기준으로 진행한다.
