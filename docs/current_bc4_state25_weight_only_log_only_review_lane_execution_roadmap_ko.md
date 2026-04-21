# BC4 State25 Weight-Only Log-Only Review Lane 실행 로드맵
## BC4-1. Context Bridge -> Review Packet

목표:
- `state25_candidate_context_bridge_v1`에서
  state25 weight review candidate를 직접 만들 수 있게 한다.

완료 기준:
- requested weight가 있으면 review packet이 생성된다.
- bridge trace가 evidence snapshot에 남는다.


## BC4-2. Detector Surface

목표:
- candle/weight detector lane에
  `state25 context bridge weight review 후보`를 올린다.

완료 기준:
- detector snapshot에 BC4 row가 포함된다.
- row에서 `weight_patch_preview`를 확인할 수 있다.


## BC4-3. Propose Backlog

목표:
- `/propose`가 최신 detector refs의 BC4 후보를 review backlog로 보여준다.

완료 기준:
- report lines에 BC4 section이 생긴다.
- proposal envelope evidence snapshot에 BC4 count가 기록된다.


## BC4-4. Tests

최소 테스트:
1. bridge 기반 review packet 생성
2. detector BC4 row surface
3. `/propose` BC4 section surface
