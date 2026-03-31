# 청산 구조 정렬 현황과 다음 로드맵

작성일: 2026-03-29 (KST)
현재 상태: entry / wait 구조 정리를 기준으로 exit / manage parity를 점검한 문서

## 1. 이 문서의 목적

이 문서는 지금 청산 축이 어디까지 정리되었는지와,
entry / wait에서 했던 수준의 구조 정렬을 청산에도 적용하려면 무엇이 더 필요한지를
코드 기준으로 객관적으로 정리한 문서다.

핵심 질문은 하나다.

`청산도 이제 entry / wait처럼 입력 계약, 의미 계약, 최근 관측 surface, 실행 seam이 분리된 구조로 가고 있는가?`


## 2. 결론부터

결론은 다음과 같다.

1. 청산은 이미 꽤 올라왔다.
2. 특히 최근 이번 작업으로 입력 계약과 recent runtime surface는 상당 부분 갖춰졌다.
3. 하지만 아직 entry / wait만큼 owner 분리가 끝난 것은 아니다.
4. 가장 큰 남은 덩어리는 `exit profile / recovery policy`, `exit wait state`, `exit utility decision`, `manage execution seam` 네 축이다.

즉 지금 상태는

`청산 observability의 뼈대는 생겼고, 남은 일은 core policy owner를 잘게 나누는 구조 정리`

라고 보는 게 가장 정확하다.


## 3. 지금까지 실제로 구축된 것

### 3-1. 공통 입력 계약이 생겼다

이전에는 청산 쪽에서 같은 trade를 보더라도
ExitService, WaitEngine, manage loop가
각자 필요한 값을 다시 풀어 읽는 비중이 컸다.

이번에는 이것을 줄이기 위해
청산/관리 쪽이 공통으로 읽는 canonical context가 생겼다.

여기에는 대략 아래 층이 담긴다.

- 진입에서 넘어온 handoff identity
- 현재 청산 stage와 selector stage
- 실제 실행에 쓰이는 exit profile posture
- 현재 시장 위치와 regime 정보
- 현재 손익, giveback, 보유 시간, adverse risk 같은 위험 정보

이 변화의 의미는 크다.
이제 적어도 `이 trade를 어떤 청산 맥락으로 보고 있는가`를
ExitService, WaitEngine, manage loop가 같은 입력면으로 보기 시작했다.


### 3-2. 청산의 hold / wait / reverse 의미 계약이 생겼다

이전에는 청산 wait 쪽이
raw state 이름과 utility winner만 남는 성격이 강했다.

지금은 청산 쪽도

- 현재 hold 상태가 어떤 계열인지
- 실제 decision이 어떤 계열인지
- state와 decision이 서로 자연스럽게 이어진 것인지

를 요약해서 남기는 taxonomy가 생겼다.

그래서 이제 단순히
`hold`, `wait_exit`, `reverse_now`, `exit_now`
같은 raw label만 보는 것이 아니라,

- 지금 이 trade는 구조적으로 hold 성격인가
- recovery wait 성격인가
- reversal bridge로 넘어가는 중인가
- state와 decision이 서로 어긋났는가

를 한 단계 더 높은 의미로 읽을 수 있게 됐다.


### 3-3. recent exit runtime surface가 생겼다

이전에는 청산도 결국 개별 trade row를 열어서
사람이 왜 그런 decision이 났는지 해석해야 하는 비중이 컸다.

지금은 trade history를 recent truth source로 읽어
runtime status와 detail status에서 최근 청산 패턴을 바로 볼 수 있다.

예를 들면 이제 최근 window 기준으로

- 어떤 exit state 계열이 많았는지
- 어떤 decision 계열이 많았는지
- state에서 decision으로 넘어가는 bridge가 어떤 패턴이었는지
- 심볼별로 청산이 어떤 방향으로 분포했는지

를 바로 읽을 수 있다.

이건 entry / wait에서 했던
`최근 200건을 사람이 수동으로 훑지 않아도 최근 패턴을 바로 읽을 수 있게 만드는 작업`
이 청산에도 들어오기 시작했다는 뜻이다.


## 4. 객관적으로 아직 덜 끝난 곳

### 4-1. exit profile / recovery policy owner가 아직 크다

현재 청산 정책의 큰 허브 중 하나는
`exit_profile_router.py`이다.

이 파일은 지금도 아래 성격이 많이 섞여 있다.

- 진입 handoff를 보고 base exit profile을 정하는 일
- range lifecycle에 따라 profile을 바꾸는 일
- recovery wait / reverse 정책을 심볼, setup, invalidation, management profile 기준으로 바꾸는 일
- state / belief / edge overlay를 읽어 한 번 더 tempering 하는 일

문제는 이것들이 모두 청산의 중요한 의미인데,
아직 한 owner 안에 뭉쳐 있다는 점이다.

entry 쪽 기준으로 비유하면,
`기본 identity router`, `scene-specific override`, `execution temperament`가
아직 완전히 나뉘지 않은 상태에 가깝다.

즉 지금 청산은 입력 계약은 생겼지만,
그 입력을 어떻게 policy로 바꾸는지는 아직 큰 router 안에 남아 있는 부분이 있다.


### 4-2. exit wait state 계산이 아직 WaitEngine 안에 크다

청산 wait state는 지금도 WaitEngine이 직접 많이 계산한다.

현재 이 부분은 아래를 함께 하고 있다.

- exit context 해석
- recovery policy 읽기
- profit / giveback / duration / adverse risk를 기준으로 state 판정
- green close, recovery BE, recovery TP1, reverse-ready, cut-immediate 같은 상태 분기
- state bias에 따라 state를 다시 바꾸는 후처리

즉 wait 쪽에서 entry에 대해 했던 것처럼
`입력 context`와 `state policy`와 `state rewrite`가
아직 충분히 분리되지 않았다.

지금 단계에서 이걸 안 건드리면,
앞으로 청산 scene 특례가 더 붙을수록
WaitEngine exit path가 다시 비대해질 가능성이 높다.


### 4-3. exit utility decision도 아직 큰 policy 덩어리다

청산 decision은 최근 taxonomy까지는 잘 붙었지만,
정작 utility winner를 만드는 본문은 아직 크다.

현재 이 부분은 아래 성격을 동시에 가진다.

- base utility 계산
- recovery utility 계산
- profile별 성향 조정
- symbol/setup 특례
- opposite edge completion bias
- reverse eligibility 판단
- 최종 winner 선택과 reason 부여
- taxonomy 생성

이건 entry 쪽으로 치면
`base score`, `scene relief`, `late block rewrite`, `display semantics`
가 한 함수 안에 가까이 있는 것과 비슷하다.

즉 청산도 이제 observability는 올라왔지만,
`왜 hold가 이겼는가`, `왜 reverse가 막혔는가`, `왜 support bounce에서 exit_now가 강화됐는가`
를 owner별로 분해해서 관리하는 단계는 아직 남아 있다.


### 4-4. manage loop는 아직 execution seam이 두껍다

`exit_manage_positions.py`는 현재도 굉장히 많은 것을 한 자리에서 한다.

- runtime snapshot 읽기
- taxonomy 읽기
- trade logger update
- live metrics 구성
- recovery execution 판단
- hard guard 처리
- adverse recheck
- partial / break-even / time-stop / protect / lock / reverse 실행

이건 자연스러운 부분도 있지만,
지금 구조 기준에서는 `execution loop`가 꼭 알아야 할 것과
`정책 해석 surface`가 섞여 있는 부분이 아직 있다.

entry / wait 기준으로 보면,
`실행기`는 얇고 `정책 결과 surface`는 밖에서 공급받는 형태가 더 이상적이다.

청산도 그 방향으로 가려면
manage loop는 점점

- canonical input read
- policy surface read
- concrete action execute

에 가까워져야 한다.


## 5. 지금 안 하면 어떤 문제가 남는가

지금 상태로도 기능은 돌아간다.
최근 summary도 읽힌다.
그러나 구조를 여기서 멈추면 아래 문제가 남는다.

### 5-1. 청산만 다시 큰 함수 중심으로 커질 수 있다

entry / wait는 owner를 잘게 나누면서
의미 drift를 줄였다.

반면 청산은 아직 큰 router와 큰 utility 본문이 남아 있어서,
scene 특례가 늘 때마다
다시 한 함수 안에서 의미가 엉키기 쉽다.


### 5-2. 최근 summary는 있는데 근본 owner는 덜 분리된 상태로 남는다

이건 관측은 좋아졌지만 구조는 아직 완전히 닫히지 않은 상태다.

즉
`최근에 recovery wait가 늘었다`
까지는 바로 보이는데,
`그 증가가 base recovery policy 때문인지 symbol override 때문인지 belief overlay 때문인지`
는 여전히 큰 함수 안으로 다시 내려가야 할 수 있다.


### 5-3. lifecycle parity가 반쯤만 완성된다

지금 목표가
entry / wait / exit / manage가 한 언어로 이어지는 lifecycle이라면,
청산도 entry / wait만큼 owner 경계가 선명해야 한다.

그렇지 않으면

- entry는 정교하게 설명되는데
- exit는 최근 summary만 좋고 내부 owner는 다시 복잡한

비대칭 구조가 남는다.


## 6. 다음으로 해야 할 일

이제부터의 작업은 크게 다섯 묶음으로 보는 것이 좋다.

### E1. exit profile / recovery policy 분리

목표는 `exit_profile_router.py` 안의 책임을 나누는 것이다.

권장 분해는 아래와 같다.

- canonical exit profile identity resolver
- lifecycle profile adjustment resolver
- recovery base policy resolver
- state / belief / edge temperament overlay resolver

이 단계가 끝나면
`청산 프로필을 무엇으로 볼 것인가`
와
`그 프로필을 지금 장면에서 얼마나 보수적으로 쓸 것인가`
가 분리된다.


### E2. exit wait state contract / policy 분리

목표는 `WaitEngine.build_exit_wait_state(...)`를
entry wait state 때처럼

- context adapter
- state policy input
- state policy resolver
- state rewrite / bias application

형태로 나누는 것이다.

이 단계가 끝나면
`green close`, `recovery`, `cut immediate`, `reverse ready`
같은 상태 전환을 훨씬 선명하게 유지할 수 있다.


### E3. exit utility decision policy 분리

목표는 `WaitEngine.evaluate_exit_utility_decision(...)`을
여러 owner로 나누는 것이다.

권장 분해는 아래와 같다.

- base exit utility bundle
- recovery utility bundle
- symbol/setup special bias bundle
- reverse eligibility / decision bridge resolver
- final winner / reason / taxonomy builder

이 단계가 끝나면
최근 summary에서 보이는 decision 패턴을
구체적인 owner로 역추적하기가 쉬워진다.


### E4. manage execution seam slimming

목표는 `exit_manage_positions.py`를
정책 해석기보다 execution runner에 가깝게 만드는 것이다.

권장 방향은 아래와 같다.

- trade logger payload builder 분리
- live metrics surface builder 분리
- recovery execution resolver 분리
- action branch selection surface 분리

이 단계가 끝나면 manage loop는
`읽고 / 선택된 surface를 받고 / 실행하는` 구조에 가까워진다.


### E5. end-to-end contract test와 읽기 표면 마감

목표는 청산도 entry / wait처럼
scene -> state -> decision -> row/runtime -> recent summary
연속 계약을 테스트와 문서로 잠그는 것이다.

여기에는 아래가 포함된다.

- 대표 exit scene fixture
- runtime aggregation parity test
- recent exit read guide
- handoff / checklist sync


## 7. 추천 작업 순서

추천 순서는 아래와 같다.

1. E1. exit profile / recovery policy 분리
2. E2. exit wait state contract / policy 분리
3. E3. exit utility decision policy 분리
4. E4. manage execution seam slimming
5. E5. end-to-end test + handoff close-out

이 순서가 좋은 이유는
먼저 canonical policy owner를 정리해야
뒤에서 state / decision / manage가 같은 언어를 쓰기 쉽기 때문이다.


## 8. 지금 기준의 객관적 평가

지금 청산은 entry / wait에 비해 뒤처진 상태가 아니다.
오히려 최근 며칠 사이에 뼈대가 꽤 빠르게 올라왔다.

다만 entry / wait와 완전히 같은 완성도를 말하려면 아직 이르다.

가장 정확한 표현은 아래다.

`청산은 이제 관측 가능성과 입력 계약은 entry / wait 수준으로 올라오기 시작했고, 남은 핵심은 core policy owner와 execution seam을 얇게 나누는 일이다.`


## 9. 다음 한 단계

지금 당장 가장 자연스러운 다음 단계는 `E1`이다.

즉 `exit_profile_router.py`를 바로 정리 대상으로 삼아

- 기본 profile identity
- lifecycle posture 조정
- recovery base policy
- state / belief / edge overlay

를 분리하는 작업이 청산 parity의 첫 본체가 된다.

