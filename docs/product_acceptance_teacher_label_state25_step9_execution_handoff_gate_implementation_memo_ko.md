# Teacher-Label State25 Step 9-E5 Execution Handoff Gate Memo

## 이번 단계 목적

이번 단계는 `execution을 바로 켤지 말지`를 감으로 판단하지 않도록
Step 9-E5 gate를 고정하는 작업이다.

즉 아래 흐름을 한 번에 묶는다.

- E1 asset calibration
- E2 full labeling QA
- E3 pilot baseline
- E4 top confusion pair tuning

## 구현 방향

- E5는 새로운 라벨러가 아니다
- E5는 `현재 상태를 판정하는 gate`다
- skew와 희귀 패턴 부족은 warning으로 본다
- 반면 seed shortfall, coverage 부족, supported class 부족, baseline 미달, high confusion은 blocker로 본다

## 현재 단계에서 기대한 결과

현재 seed는 아직 execution handoff까지는 이르므로
E5는 `NOT_READY`를 주는 것이 정상이다.

이 단계의 가치는
`왜 아직 아닌가`를 자동으로 설명하는 데 있다.

## 다음 연결

E5 결과가 `NOT_READY`면 다음은:

- labeled row 누적
- E4 재관찰/재조정
- E3 baseline 재실행

E5 결과가 `READY_WITH_WARNINGS` 또는 `READY`로 바뀌면
그때 execution 반영 범위를 별도 memo로 분기한다.

## 현재 실데이터 결과

현재 report 기준 결과는 아래와 같다.

- `handoff_status = NOT_READY`
- `labeled_rows = 2140`
- `covered_primary_count = 6`
- `supported_pattern_count = 4`
- `group_test_macro_f1 = 0.9104`
- `pattern_test_macro_f1 = 0.9758`

즉 baseline 품질 자체보다,
아래 네 가지가 현재 blocker다.

- `full_qa_seed_shortfall`
- `insufficient_primary_coverage`
- `insufficient_supported_pattern_classes`
- `unresolved_high_confusions (A->D)`
