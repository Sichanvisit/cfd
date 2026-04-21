# Teacher-Label Micro-Structure Top10 Step 3 vector/forecast harvest 구현 메모

## 이번 단계 핵심

Step 3는 raw micro 값을 그대로 action에 연결하는 단계가 아니다.

이번 단계에서 한 일은:

1. raw micro source를 중간 semantic state로 해석
2. 그 semantic state를 바탕으로 기존 coefficient를 작게 보정
3. forecast semantic harvest에서 사람이 읽고 학습하기 쉬운 surface를 추가

## 1차 설계 판단

- `compression + burst + run`은 breakout readiness 쪽
- `wick + retest + doji + decay`는 reversal risk 쪽
- `burst + decay`는 participation 쪽
- `gap_fill_progress`는 별도 gap context로 유지

## 주의점

- 이 단계는 coefficient를 완전히 재설계하지 않는다
- additive micro-adjustment만 넣는다
- 기존 regime/topdown/liquidity 체계를 덮지 않는다

## 기대 효과

- teacher-state 25의 `브레이크아웃 직전`, `변동성 컨트랙션`, `페이크아웃 반전`, `더블탑/바텀`, `엔진 꺼짐장` 같은 패턴을 더 직접적으로 설명할 수 있다
- forecast feature bundle이 micro-structure를 semantic state와 source 값 양쪽으로 들고 다니게 된다
