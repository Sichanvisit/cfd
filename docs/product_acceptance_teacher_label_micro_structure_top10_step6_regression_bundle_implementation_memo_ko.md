# Teacher-Label Micro-Structure Top10 Step 6 메모

## 메모

- Step 6은 feature 추가 단계가 아니라 검증 묶음 단계다.
- Step 1부터 Step 5까지는 각 owner에서 따로 회귀가 있었고, 이번엔 그 값이 실제 한 줄로 이어지는지를 본다.
- 특히 teacher-state 25를 제대로 붙이려면 “계산된다”보다 “계산된 값이 다음 층까지 살아서 전달된다”가 중요하다.

## 이번 단계에서 보는 대표 실패 유형

- helper에서 만든 값이 raw snapshot에서 누락되는 경우
- vector metadata에는 있는데 forecast harvest에서 빠지는 경우
- hot payload에서 semantic/source 중 하나만 빠지는 경우
- gap anchor 없음이 숫자 `0`이나 잘못된 progress로 오염되는 경우
- closed compact에서 blank refresh가 numeric micro를 덮는 경우

## 완료 후 해석

- Step 6이 닫히면 micro-structure Top10은 “점별 구현”을 넘어 “파이프라인 수준 검증 완료” 상태로 본다
- 그 다음 자연스러운 단계는 Step 7 casebook 연결이다

## 이번 단계 결과

- [test_micro_structure_pipeline_regression.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_micro_structure_pipeline_regression.py) 에서
  - breakout/continuation smoke
  - reversal/wick smoke
  - missing gap anchor safety
  3개를 cross-stage로 잠갔다
- 이 회귀는 `helper -> raw snapshot -> vector metadata -> forecast harvest -> hot surface` 흐름을 직접 검증한다
- 기존 Step 1~5 핵심 회귀도 함께 다시 돌려서 전부 통과했다

## 후속 권장

- 다음 단계는 Step 7에서 teacher-state 25 casebook과 Top10 field의 대표 연결을 붙이는 것
- pandas warning 정리는 기능 축이 아니라 housekeeping 축으로 분리해서 보는 편이 안전하다
