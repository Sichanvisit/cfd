# Teacher-Label State25 Compact Schema 메모

## 메모

- 지금 단계에서 가장 중요한 건 “25개를 어떻게 판정할까”보다 “판정 결과를 어떤 컬럼에 남길까”를 먼저 닫는 것이다.
- schema가 없으면 라벨러를 붙여도 QA와 실험 문서가 같은 row를 보지 못한다.

## 이번 단계 결정

- teacher-pattern은 먼저 `closed-history compact row`를 canonical home으로 둔다.
- `primary + secondary + bias + provenance`를 필수 묶음으로 본다.
- preview surface는 나중 단계로 미룬다.

## 핵심 이유

- 학습은 결국 close result와 같이 보게 된다.
- raw를 줄이더라도 compact row는 남게 된다.
- 따라서 `teacher_pattern_*`는 closed-history에 먼저 심는 편이 가장 안정적이다.

## 후속 단계

- schema가 닫히면 다음은 `state25 라벨러 초안`
- 그 다음은 `labeling QA`
- 그 다음은 `experiment tuning`

즉 이 문서는 state25 본 구현의 출발점이다.
