# 청산 구조 정렬 Phase E4 상세

작성일: 2026-03-29 (KST)
현재 상태: E3 완료 이후, 다음 큰 축은 manage execution seam 정리

## 1. E4가 맡는 일

E4의 목표는 `exit_manage_positions.py`의 두꺼운 실행 루프를
entry / wait / exit decision 이후 단계에 맞게 정리하는 것이다.

한 문장으로 줄이면 아래와 같다.

`청산 정책 해석 결과와 실제 실행 루프를 분리해서, manage loop를 input read -> policy surface read -> concrete action execute 구조로 바꾼다.`


## 2. 왜 지금 E4가 필요한가

지금까지의 흐름을 보면

- E1: profile / recovery policy owner 분리
- E2: exit wait state 분리
- E3: exit utility decision 분리

까지는 끝났다.

즉 이제 청산은
`왜 이 상태가 됐는가`, `왜 이 decision이 나왔는가`
까지는 상당히 잘 설명된다.

하지만 실제 실행 루프인 `exit_manage_positions.py`는 아직 아래를 같이 많이 안고 있다.

- runtime snapshot read
- taxonomy read
- trade logger update
- live metrics 조립
- recovery execution 판단
- hard guard reverse 판단
- partial close
- stop-up / break-even
- protect / lock / reverse / adverse recheck

즉 지금 단계의 병목은 정책 owner가 아니라
`실행 seam`이다.


## 3. 지금 exit_manage_positions가 실제로 하는 일

현재 manage loop는 대략 아래 층을 한 함수 / 한 루프 안에서 많이 처리한다.

### 3-1. canonical read

- runtime의 exit utility shadow 읽기
- exit manage context 읽기
- exit wait taxonomy 읽기
- threshold / stage / shock context 계산

### 3-2. sink write

- trade logger policy context update
- live metrics payload 생성

### 3-3. action pre-check

- recovery execution 판단
- hard risk guard 판단
- adverse recheck 조건 판단

### 3-4. concrete action execution

- reverse execute
- partial close
- break-even / stop-up
- protect exit
- lock exit
- adverse reverse

즉 지금 manage loop는
`무엇을 할지 해석`과 `실제로 무엇을 실행할지 결정`과 `그 결과를 어디에 기록할지`
가 아직 꽤 가까이 붙어 있다.


## 4. E4가 끝나면 어떤 구조가 되어야 하나

E4가 끝나면 manage execution은 아래 흐름으로 읽혀야 한다.

1. canonical manage execution input을 읽는다.
2. manage runtime sink payload를 별도 owner가 만든다.
3. recovery / hard guard / adverse reverse / partial / stop-up / stage exit를
   각각 action candidate 형태로 만든다.
4. execution loop는 후보를 순서대로 평가하고 concrete action만 실행한다.
5. action result surface를 runtime / logger / live metrics에 쓴다.

즉 지금의 목표는

`정책 해석이 끝난 뒤의 실행 루프를, 큰 procedural body에서 action candidate orchestrator로 바꾸는 것`

이다.


## 5. E4를 어떻게 나눌 것인가

E4는 크게 4개 묶음으로 보는 것이 좋다.

## E4-1. Manage Execution Input / Runtime Sink Freeze

### 목표

manage loop가 읽는 input과 logger / live metrics / runtime sink payload를 먼저 contract로 고정한다.

### 여기서 다룰 것

- exit shadow read
- exit manage context read
- exit wait taxonomy read
- stage / threshold / shock compact input
- trade logger payload
- ai exit live metrics payload

### 추천 파일

- `backend/services/exit_manage_execution_input_contract.py`
- `backend/services/exit_manage_runtime_sink_contract.py`

### 완료 기준

manage loop가 logger / live metrics payload를 본문에서 직접 조립하지 않는다.


## E4-2. Recovery / Hard-Guard / Reverse Candidate 분리

### 목표

실행 직전의 가장 중요한 action candidate들을 별도 owner로 뺀다.

### 여기서 다룰 것

- recovery reverse candidate
- hard guard reverse candidate
- adverse reverse candidate
- reverse execute eligibility

### 추천 파일

- `backend/services/exit_recovery_execution_policy.py`
- `backend/services/exit_hard_guard_action_policy.py`
- `backend/services/exit_reverse_action_policy.py`

### 완료 기준

reverse 계열 실행 여부와 이유가 helper 결과로 먼저 보인다.


## E4-3. Partial / Stop-Up / Stage Exit Candidate 분리

### 목표

partial close, stop-up, protect / lock exit를 action candidate owner로 뺀다.

### 여기서 다룰 것

- partial close candidate
- break-even / stop-up candidate
- protect exit candidate
- lock exit candidate
- adverse recheck exit candidate

### 추천 파일

- `backend/services/exit_partial_action_policy.py`
- `backend/services/exit_stop_up_action_policy.py`
- `backend/services/exit_stage_action_policy.py`

### 완료 기준

partial / stop-up / stage exit branch가 개별 candidate로 읽힌다.


## E4-4. Execution Orchestrator / Result Surface Close-Out

### 목표

manage loop 본문을 candidate orchestrator로 얇게 만들고,
action result surface를 별도 contract로 정리한다.

### 여기서 다룰 것

- candidate priority order
- first-hit execution orchestration
- result surface
- runtime / logger / live metrics write handoff

### 추천 파일

- `backend/services/exit_execution_orchestrator.py`
- `backend/services/exit_execution_result_surface.py`

### 완료 기준

`exit_manage_positions.py` 본문이 action candidate를 평가하고 executor를 호출하는 얇은 orchestrator에 가까워진다.


## 6. E4가 해결하는 것

E4가 풀어야 하는 핵심은 세 가지다.

### 6-1. 관리 루프 비대화를 막는다

지금은 scene와 execution branch가 늘수록 `exit_manage_positions.py`가 계속 커질 위험이 있다.
E4는 이걸 action candidate owner로 나눠서 막는다.

### 6-2. 왜 실행됐는지와 어떻게 실행됐는지를 구분한다

지금은 policy 해석과 concrete action이 붙어 있어서
`왜 그 branch가 선택됐는가`와 `실제로 어떤 order action이 나갔는가`가 쉽게 섞인다.

E4는 이 둘을 구분하려는 단계다.

### 6-3. lifecycle parity를 실제 실행 단계까지 확장한다

entry / wait / exit decision만 owner가 나뉘고,
실행 단계는 다시 큰 loop로 남으면 lifecycle parity가 반쯤만 완성된다.

E4는 이 마지막 비대칭을 줄이는 단계다.


## 7. 이 단계에서 아직 건드리지 말 것

E4에서 중요한 건 루프를 얇게 만드는 것이지,
청산 전략 자체를 새로 바꾸는 것이 아니다.

그래서 아래는 최대한 유지해야 한다.

- 현재 partial / protect / lock / reverse 우선 순서의 의미
- 기존 trade logger field shape
- 기존 live metric 핵심 필드
- 이미 붙어 있는 recent exit summary field

즉 E4는 동작 변경보다
`실행 seam owner 분리`에 집중해야 한다.


## 8. 다음 실제 진입점

지금 가장 자연스러운 다음 시작점은 E4-1이다.

즉 먼저

- manage loop가 읽는 canonical input
- logger / runtime / live metrics sink payload

를 contract로 얼리고,
그 다음 action candidate 쪽으로 들어가는 것이 가장 안전하다.
