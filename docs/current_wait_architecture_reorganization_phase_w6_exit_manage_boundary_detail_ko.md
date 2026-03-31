# 기다림 정리 Phase W6 상세 문서

부제: entry wait와 exit/manage를 같은 언어로 잇기 위한 boundary 준비 기준서

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 W5 완료 이후 W6 진입 전 정리

## 1. 문서 목적

이 문서는 `Phase W6. Exit/Manage 연결 준비`를 실제 설계 기준으로 풀어 쓴 상세 문서다.

W6의 목적은 바로 exit 전체를 다시 쓰는 것이 아니다.
이미 정리된 entry/wait 축과,
아직 상대적으로 덜 정리된 exit/manage 축이
나중에 같은 언어와 같은 경계로 이어질 수 있게
준비 작업을 하는 것이다.

즉 W6는 구현 phase라기보다
`다음 exit/manage 정리를 안전하게 시작하기 위한 boundary freeze phase`
에 가깝다.


## 2. 왜 W6가 지금 필요한가

현재 상태를 한 줄로 요약하면 이렇다.

- entry는 semantic identity와 consumer handoff가 많이 정리됐다
- wait는 owner, context, runtime, handoff, 테스트까지 한 사이클이 닫혔다
- exit/manage는 canonical handoff와 일부 owner는 있지만 아직 lifecycle 전체 언어가 완전히 고정되지는 않았다

즉 지금부터 exit/manage를 건드리기 시작하면
두 가지 방향이 생길 수 있다.

1. entry/wait에서 만든 언어를 이어받아 같은 철학으로 정리하는 길
2. exit 쪽에서 다시 별도 언어와 예외 규칙이 자라나는 길

W6 없이 바로 구현부터 들어가면 두 번째 위험이 커진다.

그래서 W6는
`지금 exit/manage는 누구의 입력을 읽어야 하고, 무엇을 identity로 쓰며, 무엇을 단지 hold/wait bias로만 써야 하는가`
를 먼저 정리하는 단계가 된다.


## 3. 현재 exit/manage에서 이미 있는 기반

W6가 시작점이 될 수 있는 이유는,
exit/manage가 완전히 비어 있기 때문이 아니라
이미 좋은 기반이 몇 개 깔려 있기 때문이다.

### 3-1. canonical exit handoff가 이미 있다

현재 exit handoff는 이미 별도 계약으로 정리되어 있다.

핵심 계약:

- `management_profile_id`
- `invalidation_id`

legacy fallback:

- `entry_setup_id`
- `exit_profile`

즉 exit는 원칙상
entry consumer handoff에서 내려온 canonical ids를 먼저 읽고,
setup 기반 fallback은 보조로만 쓰는 방향이 이미 정해져 있다.

이는 `docs/exit_handoff_contract.md`와
`backend/services/consumer_contract.py`의 `resolve_exit_handoff(...)`에서 확인된다.

### 3-2. ExitService가 중심 orchestration 역할을 갖고 있다

현재 `ExitService`는 아래를 모으는 큰 orchestrator다.

- context classifier
- exit handoff
- exit profile router
- exit wait state
- recovery predictor
- action executor
- risk guard
- manage loop

즉 구조상 “중심 서비스”는 이미 분명하다.
문제는 그 안에 아직 서로 다른 성격의 owner가 많이 함께 들어 있다는 점이다.

### 3-3. hold/wait/reverse 언어의 씨앗도 이미 있다

현재 exit 쪽에는 이미 아래와 같은 언어가 존재한다.

- `hold`
- `wait_exit`
- `exit_now`
- `reverse`
- `chosen_stage`
- `policy_stage`
- `exec_profile`
- `wait_state`

즉 완전히 무형의 상태는 아니고,
이미 exit wait/hold를 말하는 어휘가 코드 안에 존재한다.

W6의 목표는 이 어휘를
entry/wait의 `state / decision / hard wait / bridge` 언어와
어떻게 맞출지 준비하는 것이다.


## 4. 현재 구조에서 보이는 boundary 문제

W6가 실제로 풀어야 하는 boundary 문제는 크게 6가지다.

### 4-1. exit identity와 execution temperament가 아직 섞여 있다

현재 exit에서는 canonical input으로
`management_profile_id`와 `invalidation_id`를 읽는 방향이 있다.

하지만 동시에 실제 behavior는

- state overrides
- belief execution overrides
- edge execution overrides
- recovery/reverse rules
- stage 선택

이런 실행 temperament와 강하게 섞여 있다.

즉 “이 거래의 canonical exit identity”와
“지금 얼마나 오래 버틸 것인가”가
코드 레벨에서는 아직 분리 owner로 완전히 얼지 않았다.

### 4-2. exit wait/hold가 entry wait와 같은 형태로 보이지 않는다

entry wait는 지금 아래처럼 읽을 수 있다.

- wait state
- wait decision
- hard wait 여부
- recent state summary
- state -> decision bridge

반면 exit/manage에서는 비슷한 성격의 개념이 있어도
아직 같은 계약 이름이나 같은 읽기 표면으로 고정돼 있지 않다.

즉 “entry wait와 exit hold/wait_exit를 같은 언어로 연결한다”는 목표가
아직 코드 표면에는 직접 드러나지 않는다.

### 4-3. profile router가 execution temperament owner와 policy mixer 역할을 함께 한다

`exit_profile_router.py`를 보면
state/belief/edge execution overrides가 한 파일 안에서 섞여 있다.

이 자체가 틀렸다는 뜻은 아니다.
하지만 W6 관점에서는 아래 질문이 필요하다.

- 어떤 부분이 canonical management profile의 책임인가
- 어떤 부분이 현재 state/belief에 따른 execution temperament인가
- 어떤 부분이 symbol-specific edge bias인가

즉 router 하나에 있는 내용을
identity / temperament / override로 다시 구분해야 할 가능성이 높다.

### 4-4. manage_positions helper가 여전히 “큰 실제 루프”다

`exit_manage_positions.py`는 extraction이 되어 있지만,
여전히 큰 루프 안에서 여러 판단을 같이 수행한다.

예를 들면:

- recovery hold / reverse execute
- stop-up
- exit threshold
- chosen stage 기반 execution

이런 것들이 같은 흐름 안에 있다.

즉 W6 전에는 “extract는 됐지만 아직 역할별 contract는 덜 정리된 상태”라고 보는 것이 정확하다.

### 4-5. runtime observability가 entry/wait만큼 닫혀 있지 않다

entry/wait는 지금

- row
- latest runtime row
- detail recent diagnostics
- symbol summary
- handoff/checklist

까지 읽기 표면이 닫혔다.

exit/manage는 아직 그 정도로 “왜 hold했는지 / 왜 exit_now가 났는지 / 왜 reverse가 됐는지”를
entry 수준으로 summary화해서 읽는 표면이 정리된 상태는 아니다.

즉 W6는 exit observability 자체를 끝내는 단계는 아니지만,
나중에 어떤 표면이 필요할지 boundary를 정리해 두어야 한다.

### 4-6. chart / lifecycle language parity가 아직 없다

entry/wait는 최근에 언어를 많이 정리했다.
하지만 trade lifecycle 전체 관점에서 보면

- entry에서는 `BLOCKED / PROBE / READY / WAIT`
- exit에서는 `hold / wait_exit / exit_now / reverse`

가 아직 서로 직접 연결되는 taxonomy로 정리되지는 않았다.

W6는 이 둘을 억지로 같은 단어로 만들자는 단계는 아니지만,
적어도 “무엇이 같은 종류의 판단이고 무엇이 다른 종류의 판단인가”는 맞춰둬야 한다.


## 5. W6가 지향하는 최종 상태

W6가 끝나면 아래 6가지가 준비돼 있어야 한다.

1. exit/manage의 canonical input이 무엇인지 명확하다
2. entry wait와 exit hold/wait_exit/reverse를 잇는 공통 taxonomy 초안이 있다
3. `ExitService / ExitProfileRouter / WaitEngine(exit path) / ExitManagePositions`의 역할 경계가 정리돼 있다
4. 앞으로 extraction할 owner 후보가 구체화돼 있다
5. runtime/diagnostics에서 무엇을 보여줘야 하는지 표면 요구사항이 정리돼 있다
6. 다음 implementation phase가 어디서 시작해야 하는지 분명해진다

즉 W6는 결과적으로
`이제 exit/manage도 wait 때처럼 쪼개기 시작해도 된다`
는 준비 상태를 만드는 단계다.


## 6. W6에서 꼭 정리해야 할 개념

### 6-1. exit identity

무슨 거래를 어떻게 관리할 것인지에 대한 canonical identity다.

핵심 후보:

- `management_profile_id`
- `invalidation_id`

이 둘은 entry consumer handoff에서 내려온 canonical id이며,
W6에서는 “무엇이 canonical exit identity인가”를 여기로 고정하는 것이 중요하다.

### 6-2. exit temperament

동일한 identity라도
현재 state/belief/edge 조건에 따라
얼마나 오래 버틸지, 얼마나 빨리 정리할지 달라질 수 있다.

이 부분은 identity가 아니라 execution temperament로 분리되어야 한다.

후보:

- state execution overrides
- belief execution overrides
- edge execution overrides
- recovery wait/reverse overrides

### 6-3. exit hold semantics

entry wait와 맞물려 읽히려면
exit에서도 최소한 아래 같은 의미 층이 필요하다.

- 현재 hold state
- 그 hold가 hard hold인지 soft hold인지
- 최종 decision이 hold / wait_exit / exit_now / reverse 중 어디인지
- 어떤 state가 어떤 decision으로 이어졌는지

즉 entry wait에서 했던
`state -> decision -> bridge`
형식이 exit에도 대응 개념으로 필요하다.

### 6-4. lifecycle bridge

entry 이후의 lifecycle은
단순히 완전히 다른 시스템이 아니라 이어지는 과정이다.

따라서 W6에서는 아래 연결도 정의해야 한다.

- entry에서 내려온 management profile이 exit의 어떤 profile routing으로 이어지는지
- invalidation id가 어떤 failure identity로 살아남는지
- entry wait와 exit hold가 어떤 차원에서 같은 “보류”인지
- reverse는 wait의 연장인지, exit decision의 한 종류인지


## 7. 권장 owner 지도

현재 기준으로 W6는 아래 owner 지도로 보는 것이 가장 자연스럽다.

### 7-1. canonical handoff owner

- `consumer_contract.py`
- `exit_handoff_contract.md`

역할:

- entry consumer에서 canonical exit input을 freeze한다

### 7-2. exit identity / profile owner

- `exit_profile_router.py`

현재 역할:

- management profile 기반 exit temperament와 routing을 섞어 다룬다

W6 목표:

- identity/profile routing과 execution override를 더 분리할 준비를 한다

### 7-3. exit wait/hold state owner

- `wait_engine.py`의 exit path

현재 역할:

- exit 시점의 hold / wait_exit / reverse-ready 성격을 계산한다

W6 목표:

- entry wait와 대응되는 exit hold semantics contract 후보를 정의한다

### 7-4. execution / manage owner

- `exit_manage_positions.py`
- `exit_engines.py`

현재 역할:

- 실제 청산, 보류, reverse 실행 흐름을 담당한다

W6 목표:

- orchestration과 concrete execution을 더 분리할 준비를 한다

### 7-5. top-level orchestration owner

- `exit_service.py`

현재 역할:

- 전체 exit/manage 흐름의 조합기

W6 목표:

- 앞으로 어떤 owner들을 밖으로 뺄지, 무엇을 조합기로 남길지 경계를 정한다


## 8. W6를 어떻게 나눌 것인가

W6도 W1/W2처럼 크게 뜯는 단계는 아니다.
하지만 다음 implementation phase를 위한 기준이 필요하므로
아래 4단으로 나누는 것이 적절하다.

### W6-1. Exit/Manage Owner Inventory

목표:

- 현재 exit/manage 축에서 누가 무엇을 하는지 owner 지도를 만든다

핵심 질문:

- canonical input owner는 누구인가
- profile owner는 누구인가
- hold/wait/reverse state owner는 누구인가
- concrete execution owner는 누구인가

완료 기준:

- `ExitService / ExitProfileRouter / WaitEngine(exit path) / ExitManagePositions / ExitEngines`
  책임도가 정리돼 있다

### W6-2. Canonical Exit Context Freeze 준비

목표:

- 나중에 만들 `exit_manage_context_v1` 같은 contract의 입력 후보를 정의한다

후보 입력:

- management profile
- invalidation id
- entry direction / setup / stage
- chosen stage / policy stage / exec profile
- state/belief/edge overrides
- current profit / duration / adverse risk / score gap

완료 기준:

- “exit가 실제로 읽는 canonical input 묶음” 초안이 정리돼 있다

### W6-3. Exit Hold/Decision Taxonomy 준비

목표:

- exit hold/wait_exit/reverse를 entry wait와 비교 가능한 언어로 정리한다

핵심 질문:

- hold state와 final decision을 분리할 것인가
- hard hold와 soft hold를 구분할 것인가
- reverse는 exit decision의 한 종류인가, 별도 lifecycle branch인가

완료 기준:

- `state / decision / bridge` 대응 개념 초안이 있다

### W6-4. Next Implementation Gate

목표:

- 다음 실제 exit/manage refactor를 어디서 시작할지 고정한다

후보 시작점:

- exit profile router extraction
- exit hold state contract
- exit runtime observability first slice

완료 기준:

- 다음 코드 phase의 first slice가 하나로 좁혀진다


## 9. 이 단계에서 건드리면 안 되는 것

### 9-1. exit 전체 리팩터링을 한 번에 시작하는 것

W6는 boundary 준비지,
대형 구현 phase가 아니다.

### 9-2. entry/wait semantics를 다시 흔드는 것

지금 wait 축은 막 close-out이 끝났다.
W6에서 그 축을 다시 흔들면 범위가 섞인다.

### 9-3. chart까지 동시에 통합하려는 것

lifecycle parity는 중요하지만,
차트 표현까지 동시에 손대면 W6 범위를 넘어간다.


## 10. 권장 구현 순서

W6는 아래 순서가 가장 자연스럽다.

1. owner inventory 정리
2. canonical exit context 초안 정의
3. hold/decision taxonomy 정리
4. 다음 implementation start point 확정


## 11. 완료 선언 조건

W6를 완료로 보려면 아래가 만족돼야 한다.

- exit/manage owner 지도가 문서로 정리돼 있다
- canonical exit input 초안이 있다
- entry wait와 exit hold/wait_exit/reverse를 잇는 taxonomy 초안이 있다
- 다음 implementation start point가 분명하다


## 12. 지금 바로 시작할 첫 작업

첫 작업은 `W6-1 owner inventory`다.

이유는 단순하다.
지금 exit/manage는 로직 자체보다도
`누가 identity를 읽고, 누가 temperament를 만들고, 누가 실행을 결정하는가`
를 먼저 선명하게 해야 한다.

즉 다음 실제 행동은
`W6 implementation breakdown 문서를 만들고, owner inventory부터 시작하는 것`
이다.
