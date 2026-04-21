# BC10 실행 로드맵

1. detector snapshot에서 bounded-live review 후보 재조립
2. current runtime row와 비교해 cooldown / runtime-zero / stale 여부 판정
3. weight bounded-live readiness 집계
4. threshold bounded-live readiness 집계
5. threshold single-delta 계약 충돌 여부 판정
6. 가능하면 apply handler 실행, 아니면 blocker를 artifact로 남김
