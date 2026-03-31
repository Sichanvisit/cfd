# Position Rulebook

## 1. 목적

`Position`은 현재 시장이 큰 그림에서 어디에 있는지를 말하는 레이어다.

- 하단에 가까운가
- 중심에 가까운가
- 상단에 가까운가
- 중심에서 얼마나 멀어졌는가

`Position`은 큰 위치를 설명하는 역할만 하며, 실제 진입 확정 레이어가 아니다.

## 2. 기본 원칙

- 기본 side seed는 항상 `box` 양끝과 `Bollinger Band` 양끝에서 나온다.
- 하단에 가까우면 기본 후보는 `BUY`다.
- 상단에 가까우면 기본 후보는 `SELL`이다.
- 중심에서 멀수록 `position energy`는 강해진다.
- 중심에 가까울수록 `Position`은 약하게 말해야 한다.

## 3. Position이 해야 하는 일

- `global lower / middle / upper`를 정리한다.
- `edge`에 얼마나 가까운지 정리한다.
- `lower_bias / upper_bias / unresolved / conflict`를 정직하게 남긴다.
- 강한 확정이 어려우면 확정보다 `bias` 또는 `unresolved`를 준다.

## 4. Position이 하면 안 되는 일

- local spike만 보고 진입을 확정하면 안 된다.
- wick 하나만 보고 reversal을 확정하면 안 된다.
- `SR`, `Evidence`, `Belief`, `Barrier` 역할까지 대신하면 안 된다.
- 중심 구간인데 too early `BUY` 또는 `SELL` 확정을 주면 안 된다.

## 5. 기본 진입 기준

- `box` 하단 + `band` 하단 근접: 기본 후보 `BUY`
- `box` 상단 + `band` 상단 근접: 기본 후보 `SELL`
- `band` 돌파: continuation 가능
- `band` 지지/저항 실패: reversal 또는 fail 가능

단, 이 해석은 `Position` 단독 확정이 아니라 뒤 레이어 handoff 전제다.

## 6. Handoff 순서

아래 판단은 `Position`이 아니라 다음 순서에서 한다.

1. `Response Raw`
2. `Response Vector`
3. `State Vector`
4. `Evidence`
5. `Belief`
6. `Barrier`

즉:

- `Position` = 큰 위치
- `Response` = 그 위치에서 나온 실제 반응
- 나머지 = 그 반응을 실행 가능한지 판정

## 7. 중심 구간 규칙

- 중심에서는 `Position` 비중을 낮춘다.
- 중심에서는 `Response/State/Evidence/Belief/Barrier` 비중을 높인다.
- 중심인데 강한 `BUY/SELL` 확정이 나오면 과민 반응으로 본다.

## 8. 로컬 반응 규칙

global 위치가 `lower/middle`여도 local 상단 probe가 가능하다.
global 위치가 `upper/middle`여도 local 하단 probe가 가능하다.

이런 로컬 판단은 `Position`이 아니라 `Response Raw/Vector`에서 처리한다.

예:

- local upper probe
- upper-half reject
- wick reject
- failed pop
- lower flush
- lower reclaim fail

## 9. SR의 역할

- `SR`은 보조 컨텍스트다.
- `SR`만으로 기본 side seed를 만들지 않는다.
- 기본 side seed는 여전히 `band edge`와 `box edge`에서 나온다.
- `SR`은 진입 허용/보류/강화 판단에 참여한다.

## 10. 현재 구현 방향

- `edge`에서는 `Position` authority를 높인다.
- `middle`에서는 `Position` authority를 낮춘다.
- `bb44`가 아직 `middle`이면 weak alignment를 쉽게 확정하지 않는다.
- `structural break`가 나오면 reversal보다 fail/continuation을 우선 본다.
- local upper reject / lower reject는 `Response` 계층에서 처리한다.

## 11. 한 줄 요약

`Position`은 큰 위치만 말하고, 실제 진입 판단은 항상 뒤 레이어가 확정한다.
