# Teacher-Label Micro-Structure Top10 Step 2 state_raw_snapshot 구현 메모

## 목적

Step 2는 `micro_structure_v1`를 계산하는 단계가 아니라,
그 결과를 `StateRawSnapshot` canonical state로 승격하는 단계다.

## 이번 단계 핵심 결정

1. 기존 raw field는 유지한다
2. `micro_structure_v1`는 새 canonical field와 metadata flat surface 두 층에 같이 남긴다
3. `body`와 `compression`은 기존 field fallback을 허용한다
4. `gap_fill_progress`는 `None`을 유지해서 anchor 부족 상태를 숨기지 않는다

## 기대 효과

- Step 3 이후 forecast/vector harvest가 micro-structure를 직접 사용할 수 있다
- entry/export 쪽에서 compact `micro_*` surface를 바로 가져갈 수 있다
- teacher-state 25 패턴과 raw snapshot을 직접 연결하기 쉬워진다

## 주의점

- Step 2는 raw snapshot contract만 다룬다
- 아직 runtime 전체가 항상 `micro_structure_v1`를 채우는 단계는 아니다
- 따라서 missing-safe fallback이 반드시 필요하다
