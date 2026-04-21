# Teacher-Label State25 Step 9 메모

## 메모

- Step 9는 baseline 모델부터 바로 시작하는 단계가 아니라, 현재 labeled seed를 실험 가능한 숫자로 읽는 단계부터 시작해야 한다.
- 이번 구현은 그 첫 관문으로 `experiment seed report`를 추가한 것이다.

## 왜 이 구현이 필요한가

- labeled row 수만 보는 것으로는 부족하다
- 어떤 자산/패턴/편향에 쏠렸는지 같이 봐야 한다
- Step 8 경고와 seed readiness를 같이 봐야 다음 calibration 순서를 정할 수 있다

## 다음 자연스러운 순서

1. seed report 실행
2. Step E1 asset calibration
3. Step E2 full labeling QA
4. baseline model

즉 Step 9는 `리포트 -> calibration -> baseline` 순서로 보는 것이 맞다.
