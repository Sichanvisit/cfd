# Teacher-Label State25 Step E2 Full Labeling QA 메모

## 메모

- Step E2는 아직 ground-truth confusion matrix 단계가 아니다.
- 현재 단계에서의 confusion은 `primary-secondary pair`를 proxy로 본다.
- 따라서 이 리포트는 `full labeling QA`이면서 동시에 `confusion 준비도 리포트` 역할을 한다.

## 구현 이유

- Step E1은 seed가 실험 가능한지 보는 단계였다.
- Step E2는 그 seed가 `어디로 치우쳐 있고 무엇이 비어 있는지`를 본다.
- 지금처럼 labeled row가 2K 수준일 때도 미리 돌려볼 수 있어야, 10K로 커졌을 때 같은 리포트로 자연스럽게 이어진다.

## 이번 구현에서 특히 본 것

- 25개 전체 패턴 coverage
- missing primary ids
- rare primary ids
- symbol별 group skew
- watchlist pair와 pair concentration

## 다음 연결

- Step E2 결과를 현재 2K+ seed에 먼저 적용
- skew/missing pattern을 확인
- 그 뒤 Step E3 baseline model 준비

## 2026-04-02 현재 seed 적용 결과

- `labeled_rows = 2140`
- `full_qa_ready = False`
- `shortfall_rows = 7860`
- 현재 primary coverage는 `6/25`다.
- 주요 primary는 `1`, `14`, `5`, `9`에 집중되어 있고, 전체 group 분포는 `A = 85.14%`, `D = 13.46%`, `E = 1.40%`다.
- symbol별로는 `BTCUSD:A`, `XAUUSD:A` skew 경고가 유지된다.
- primary-secondary pair는 현재 `1-5`가 가장 크고 watchlist pair(`12-23`, `5-10`, `2-16`)는 아직 거의 잡히지 않는다.

즉 Step E2 기준에서 현재 seed는 `리포트/QA/실험 준비도 확인`에는 충분하지만, `10K full labeling QA 완료` 단계는 아직 아니다.

## skew 해석 보강

이번 결과에서 중요한 건 `A 그룹 편향 자체`를 실패로 보지 않는다는 점이다.

- 조용한 장/압축장이 다수인 것은 시장 현실에 가깝다.
- rare 패턴이 적은 것도 자연스러운 현상이다.
- 따라서 지금 seed는 `25개 전체를 대표하는 완성 seed`는 아니지만,
  `pilot baseline과 초기 실험용 seed`로는 충분히 유효하다.

다음 단계의 핵심은
`현재 skew를 억지로 없애는 것`이 아니라
`계속 labeled row를 누적하면서 학습 시 가중치/샘플링/rolling window로 불균형을 관리하는 것`이다.
