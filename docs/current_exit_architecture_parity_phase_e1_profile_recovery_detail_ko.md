# 청산 구조 정렬 Phase E1 상세

작성일: 2026-03-29 (KST)
현재 상태: exit / manage parity 로드맵의 첫 본체 상세, E1 전체 구현 완료

## 1. E1이 맡는 일

E1의 목표는 단순하다.

`청산 프로필과 recovery 정책을 한 덩어리 router에서 꺼내어, identity / posture / base policy / temperament overlay로 분리한다.`

지금 청산은 관측 표면과 recent summary는 많이 올라왔다.
하지만 그 바닥에서 실제로

- 어떤 exit profile을 기본으로 볼지
- range나 box 위치에 따라 lifecycle posture를 어떻게 바꿀지
- wait / reverse / recovery 허용치를 무엇으로 둘지
- state / belief / edge 정보가 그 정책을 얼마나 조정할지

가 아직 큰 router 안에서 함께 움직인다.

entry / wait 기준으로 말하면,
입력 계약은 생겼는데
그 입력을 policy로 번역하는 중추가 아직 크다.

E1은 바로 그 번역 레이어를 쪼개는 phase다.


## 2. 왜 지금 E1이 필요한가

청산 쪽은 최근에 아래가 이미 생겼다.

- 공통 입력 계약
- hold / decision taxonomy
- recent exit runtime summary

그래서 이제 남은 병목은 관측이 아니라 policy owner다.

이 시점에 E1이 필요한 이유는 세 가지다.

### 첫째, profile identity와 temperament가 섞여 있다

현재 router는
`이 trade의 기본 exit 성향이 무엇인가`
와
`지금 이 장면에서 그 성향을 얼마나 빠르게/느리게 쓸 것인가`
를 한 파일 안에서 같이 다룬다.

이 둘은 성격이 다르다.

- identity는 비교적 안정적이다
- temperament는 state / belief / market scene에 따라 변한다

이 둘이 섞여 있으면, 새 특례를 넣을 때 identity가 흔들린다.

### 둘째, recovery base policy와 overlay가 섞여 있다

현재는 recovery 정책도

- 기본 wait 허용치
- reverse 최소 조건
- 심볼/셋업별 기본값
- state / belief / edge overlay

가 한 흐름으로 이어진다.

이렇게 두면 최근 summary에서 보이는 변화가
base policy 때문인지 overlay 때문인지 바로 분리되지 않는다.

### 셋째, WaitEngine이 여전히 큰 policy를 직접 먹고 있다

청산 wait state와 utility decision은 이제 최근 surface까지 올라왔지만,
그 밑에서 먹는 recovery policy가 여전히 큰 덩어리면
다음 단계에서 WaitEngine을 잘게 나누기가 어렵다.

즉 E1은 단독 phase가 아니라,
E2와 E3가 깔끔하게 갈 수 있게 하는 바닥 정리다.


## 3. 현재 owner가 실제로 섞여 있는 방식

현 상태의 청산 router는 크게 네 성격을 함께 가진다.

### 3-1. 기본 exit profile identity

진입에서 넘어온 handoff id와 setup을 보고
기본 profile을 정하는 역할이다.

예를 들면 이런 질문에 답한다.

- reversal 성향인가
- breakout hold 성향인가
- support hold 성향인가
- range reversal 성향인가

이건 비교적 안정적인 identity layer다.

### 3-2. lifecycle posture adjustment

같은 profile이어도
현재 regime이 range인지,
box 위치가 middle인지에 따라
조금 더 빠르게 보호할지,
조금 더 hold를 허용할지 바뀐다.

이건 identity가 아니라 posture layer다.

### 3-3. recovery base policy

이 layer는 실제 숫자를 만든다.

- wait를 얼마나 허용할지
- breakeven recovery를 허용할지
- TP1 recovery를 허용할지
- reverse를 어느 score gap부터 허용할지
- wait 최대 시간을 얼마로 둘지

이건 청산 정책의 가장 실질적인 body다.

### 3-4. temperament overlay

마지막으로 state / belief / edge가
이미 정해진 recovery base policy를 더 보수적으로 바꾸거나 완화한다.

예를 들어

- fast exit 성향이면 wait를 줄이고
- same-side confirmation이면 hold를 늘리고
- edge rotation scene이면 reverse 허용을 빨리 열고
- symbol edge execution override가 있으면 hold to opposite edge를 강화하는 식이다

이건 base policy와 다르게
scene-sensitive overlay다.


## 4. E1에서 만들고 싶은 목표 형태

E1이 끝났을 때의 이상적인 흐름은 아래와 같다.

1. 기본 identity를 정한다.
2. 현재 market posture로 lifecycle profile을 조정한다.
3. symbol / setup / management profile 기준으로 recovery base policy를 만든다.
4. state / belief / edge overlay로 그 policy를 조정한다.
5. 최종 recovery policy contract를 반환한다.

이렇게 되면 각 단계가 답하는 질문이 분리된다.

- 나는 어떤 기본 profile인가
- 지금 장면에서 profile posture는 어떻게 조정되는가
- recovery 기본 허용치는 얼마인가
- 지금 state / belief / edge가 그 허용치를 얼마나 움직이는가


## 5. E1을 어떻게 쪼개는가

E1은 네 조각으로 나누는 것이 안전하다.

## E1-1. Exit Profile Identity Extraction

### 목표

기본 exit profile identity를 독립 owner로 분리한다.

### 이 조각에서 다루는 것

- management profile 기반 기본 profile 결정
- invalidation 기반 기본 profile 결정
- entry setup 기반 기본 profile 결정
- fallback profile 결정

### 이 조각에서 다루지 않는 것

- 현재 regime / box state를 반영한 lifecycle adjustment
- recovery wait / reverse 수치
- state / belief / edge overlay

### 추천 새 owner

- `exit_profile_identity_policy.py`

### 추천 함수 형태

- `resolve_exit_profile_identity_v1(...)`

### 완료 기준

`이 trade의 기본 exit 성향이 무엇인가`에 대한 답이
나머지 dynamic overlay와 분리되어 독립적으로 테스트된다.


## E1-2. Lifecycle Posture Adjustment Extraction

### 목표

range / current box 위치에 따른 lifecycle profile 조정을 독립 owner로 분리한다.

### 이 조각에서 다루는 것

- range 환경에서 hold_then_trail을 더 빠른 profile로 낮추는지
- middle box에서 protect_then_hold를 더 빠르게 바꾸는지

### 이 조각에서 다루지 않는 것

- base profile identity
- recovery wait / reverse limits
- state / belief / edge overlay

### 추천 새 owner

- `exit_lifecycle_profile_policy.py`

### 추천 함수 형태

- `apply_exit_lifecycle_profile_v1(...)`

### 완료 기준

`같은 profile이어도 지금 시장 위치 때문에 얼마나 보수적으로 쓸지`
가 독립 테스트 단위로 잠긴다.


## E1-3. Recovery Base Policy Extraction

### 목표

청산 recovery의 기본 정책을 하나의 stable owner로 분리한다.

### 이 조각에서 다루는 것

- management profile 기반 기본 recovery 성향
- invalidation 기반 기본 recovery 성향
- setup / symbol 기반 기본 recovery 성향
- wait 허용 여부
- reverse 허용 기본 성향
- wait 최대 시간
- breakeven / TP1 최대 허용 손실
- reverse score gap 기본값

### 이 조각에서 다루지 않는 것

- state / belief / edge overlay
- symbol temperament가 만든 scene-sensitive 후처리

### 추천 새 owner

- `exit_recovery_base_policy.py`

### 추천 함수 형태

- `resolve_exit_recovery_base_policy_v1(...)`

### 완료 기준

청산 recovery 정책의 숫자 본문이
state / belief overlay와 독립된 base table로 존재한다.


## E1-4. Recovery Temperament Overlay Extraction

### 목표

state / belief / edge 기반 조정을 recovery base policy 밖의 독립 owner로 분리한다.

### 이 조각에서 다루는 것

- state 기반 wait / reverse multiplier
- belief 기반 hold extension / fast cut bias
- edge rotation reverse bias
- symbol edge execution bias
- force disable wait 규칙

### 추천 새 owner

- `exit_recovery_temperament_policy.py`

### 추천 함수 형태

- `apply_exit_recovery_temperament_v1(...)`
- 또는 `resolve_exit_recovery_temperament_bundle_v1(...)`

### 완료 기준

이제 recovery policy 변화가
base policy 변화인지
temperament overlay 변화인지
분리해서 읽힌다.


## 6. 최종 조립 형태

E1이 닫히면 현재 큰 router는 최종적으로 아래 형태만 남는 것이 좋다.

1. identity owner 호출
2. lifecycle posture owner 호출
3. recovery base policy owner 호출
4. temperament overlay owner 호출
5. 최종 payload 조립

즉 router 본문은 점점
`많이 판단하는 곳`이 아니라
`각 owner를 연결하는 곳`에 가까워져야 한다.


## 7. 어떤 테스트가 필요하나

E1은 구조 공사라서 direct helper 회귀가 중요하다.

### E1-1 direct 회귀

- reversal profile이 tight protect로 가는지
- breakout hold가 hold_then_trail로 가는지
- invalidation fallback이 맞는지
- setup 기반 fallback이 맞는지

### E1-2 direct 회귀

- range가 아닐 때 profile이 유지되는지
- range에서 hold_then_trail이 tighter posture로 바뀌는지
- middle box에서 protect_then_hold가 더 빠른 posture로 바뀌는지

### E1-3 direct 회귀

- management profile별 기본 recovery 숫자가 맞는지
- symbol/setup 조합별 기본 policy가 맞는지
- invalidation failure가 reverse 성향을 키우는지

### E1-4 direct 회귀

- state fast-exit가 wait 허용치를 줄이는지
- belief same-side confirmation이 hold 쪽을 늘리는지
- edge rotation이 reverse 성향을 강화하는지
- symbol edge bias가 따로 남는지

### existing 회귀와 연결해야 하는 것

- `WaitEngine` exit wait state 회귀
- exit taxonomy 회귀
- decision model snapshot 회귀
- recent exit runtime summary 회귀


## 8. 구현할 때 주의할 점

### 첫째, identity와 overlay를 다시 섞지 말 것

기본 profile identity는 되도록 stable layer로 남겨야 한다.
scene-specific 판단은 overlay로 밀어내야 한다.

### 둘째, payload shape는 급하게 바꾸지 말 것

지금은 wait / exit recent summary가 이미 올라와 있다.
E1에서는 구조를 바꾸되,
기존 runtime payload key를 불필요하게 흔들지 않는 편이 좋다.

### 셋째, base policy와 final policy를 구분해서 남길 것

가능하면 최종 정책만 남기지 말고,
base policy와 overlay applied 결과를 구분해서 남기는 방향이 더 좋다.
그래야 observability가 더 강해진다.


## 9. E1 완료 선언 조건

E1은 아래 조건이 충족되면 완료로 본다.

1. 기본 exit profile identity owner가 분리되어 있다.
2. lifecycle posture adjustment owner가 분리되어 있다.
3. recovery base policy owner가 분리되어 있다.
4. temperament overlay owner가 분리되어 있다.
5. 최종 router는 owner 조합기 성격이 강해졌다.
6. direct helper 회귀가 각 조각별로 존재한다.
7. 기존 wait / exit runtime 회귀가 깨지지 않는다.


## 10. 가장 먼저 시작할 실제 작업

첫 구현은 `E1-1`이 가장 좋다.

이유는 세 가지다.

- 가장 독립적이다
- downstream 의미를 거의 안 흔든다
- E1-2, E1-3, E1-4의 기준점이 된다

즉 다음 실제 순서는 이렇게 가는 것이 좋다.

1. `E1-1` 기본 exit profile identity 추출
2. `E1-2` lifecycle posture 추출
3. `E1-3` recovery base policy 추출
4. `E1-4` temperament overlay 추출
