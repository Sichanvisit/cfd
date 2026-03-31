# 기다림 정리 Phase W6 구현 분해 문서

부제: exit/manage 연결 준비를 실제 작업 단위로 나눈 실행 문서

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 W6 진입 전 작업 분해

## 1. 문서 목적

이 문서는 `Phase W6. Exit/Manage 연결 준비`를
바로 실행 가능한 작업 묶음으로 쪼개기 위한 문서다.

W6는 wait처럼 바로 code extraction을 크게 시작하는 phase가 아니다.
따라서 이번 단계의 산출물은

- owner map
- canonical input 초안
- taxonomy 초안
- next implementation gate

가 된다.


## 2. W6 전체 목표

최종 목표는 아래 한 문장으로 정리할 수 있다.

`entry wait와 exit/manage가 나중에 같은 언어와 같은 경계로 정리될 수 있도록, exit/manage boundary를 먼저 얼린다.`


## 3. W6-1. Exit/Manage Owner Inventory

### 목표

현재 exit/manage 축의 owner 지도를 만든다.

### 대상 파일

- `backend/services/exit_service.py`
- `backend/services/exit_profile_router.py`
- `backend/services/exit_manage_positions.py`
- `backend/services/exit_engines.py`
- `backend/services/consumer_contract.py`
- `docs/exit_handoff_contract.md`
- `docs/trust_wait_hold_owner_ko.md`

### 체크리스트

- `ExitService`가 실제로 조합하는 판단 종류 목록화
- `exit_profile_router.py`가 identity/profile/override 중 무엇을 맡는지 구분
- `WaitEngine` exit path가 hold/wait_exit/reverse-ready에서 맡는 역할 분리
- `exit_manage_positions.py`가 실제 execution loop에서 하는 판단 분리
- `exit_engines.py`가 concrete execution에서 맡는 역할 분리

### 산출물

- owner responsibility 표
- “지금 섞여 있는 책임” 목록

### 완료 기준

- 다음 phase에서 어떤 owner를 먼저 extraction할지 설명 가능하다


## 4. W6-2. Canonical Exit Context Freeze 준비

### 목표

나중에 만들 canonical exit context 입력면 초안을 정리한다.

### 후보 이름

- `exit_manage_context_v1`
- 또는 `exit_runtime_context_v1`

### 포함 후보

- canonical handoff ids
  - `management_profile_id`
  - `invalidation_id`
- legacy fallback ids
  - `entry_setup_id`
  - `exit_profile`
- current execution posture
  - `chosen_stage`
  - `policy_stage`
  - `exec_profile`
- risk/runtime inputs
  - profit
  - duration
  - adverse risk
  - score gap
  - confirm needed
- temperament overlays
  - state overrides
  - belief overrides
  - edge overrides

### 대상 파일

- `backend/services/exit_service.py`
- `backend/services/exit_profile_router.py`
- `backend/services/consumer_contract.py`

### 완료 기준

- canonical input과 derived temperament input이 구분된 초안이 있다


## 5. W6-3. Exit Hold/Decision Taxonomy 준비

### 목표

entry wait와 대응되는 exit hold semantics 초안을 만든다.

### 핵심 질문

- exit에서도 `state / decision`을 분리할 것인가
- hard hold / soft hold를 둘 것인가
- `reverse`를 decision으로 볼 것인가 별도 branch로 볼 것인가
- `wait_exit`와 일반 hold의 차이를 어디에 둘 것인가

### 대상 파일

- `backend/services/wait_engine.py`
- `backend/services/exit_service.py`
- `backend/services/exit_manage_positions.py`
- 관련 문서:
  - `docs/trust_wait_hold_owner_ko.md`
  - `docs/entry_exit_wait_reason_expression_ko.md`

### 산출물

- exit hold taxonomy 초안
- entry wait와의 대응표

### 완료 기준

- 다음 phase에서 observability를 붙일 때 어떤 summary가 필요한지 말할 수 있다


## 6. W6-4. Next Implementation Gate

### 목표

다음 실제 코드 phase의 시작점을 하나로 좁힌다.

### 후보

1. `exit_profile_router` extraction first slice
2. exit hold state contract first slice
3. exit runtime observability first slice

### 선택 기준

- 현재 가장 owner가 섞여 있는 곳인가
- 다음 observability를 붙일 준비가 되는가
- wait에서 했던 패턴을 가장 무리 없이 재사용할 수 있는가

### 완료 기준

- 다음 구현이 어디서 시작될지 문서상으로 단일 추천안이 있다


## 7. 권장 작업 순서

추천 순서는 아래와 같다.

1. W6-1 owner inventory
2. W6-2 canonical exit context 초안
3. W6-3 hold/decision taxonomy
4. W6-4 next implementation gate


## 8. 권장 검증

W6는 주로 문서와 boundary phase이므로,
이번 단계에서는 아래 정도가 충분하다.

- 현재 코드 owner가 문서와 맞는지 파일 교차 확인
- existing exit handoff contract와 문서 표현이 일치하는지 확인
- wait 쪽 용어를 exit 쪽에 그대로 강제 적용하고 있지 않은지 확인


## 9. 하지 말아야 할 것

- exit 전체 execution loop를 바로 뜯는 것
- 새로운 exit runtime summary를 지금 바로 구현하는 것
- chart/lifecycle UI까지 같이 건드리는 것
- wait 축 문서를 다시 크게 수정하는 것


## 10. 바로 시작할 첫 작업

첫 작업은 W6-1이다.

즉 다음 실제 행동은
`ExitService / ExitProfileRouter / ExitManagePositions / WaitEngine(exit path)`를 기준으로
owner inventory 문서를 먼저 만드는 것이다.

이 작업이 끝나야
그다음 코드 phase를 어디서 시작할지 무리 없이 좁혀질 수 있다.
