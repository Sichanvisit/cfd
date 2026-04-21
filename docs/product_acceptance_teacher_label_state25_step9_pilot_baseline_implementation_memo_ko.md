# Teacher-Label State25 Step 9-E3 Pilot Baseline 메모

## 메모

- 현재 seed는 25개 전체를 대표하진 못한다.
- 하지만 pilot baseline을 통해 `학습 가능성`과 `현재 skew 하에서의 구분 가능성`을 먼저 확인할 수 있다.

## 이번 설계의 핵심

- `group_task`로 큰 그룹 구분부터 본다.
- `pattern_task`는 support가 충분한 class만 쓴다.
- teacher label 자체는 feature로 다시 넣지 않는다.
- dummy baseline과 같이 비교해서 최소 성능 의미를 확보한다.

## 현재 단계 해석

이 baseline 결과는

- 최종 execution 반영 판단용이 아니라
- 현재 라벨과 feature pack이 학습 가능한 구조인지 확인하는 용도다.

따라서 결과가 좋아도 바로 execution으로 가지 않고,
E4/E5와 labeled seed 누적을 같이 본다.
