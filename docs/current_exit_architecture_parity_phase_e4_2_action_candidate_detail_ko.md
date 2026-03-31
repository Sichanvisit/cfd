# 청산 구조 정렬 Phase E4-2 상세

작성일: 2026-03-29 (KST)
현재 상태: E4-2 구현 시작

## 1. 이번 단계의 목표

E4-2의 목표는 `manage loop`와 `ExitRiskGuard` 안에 아직 남아 있는

- recovery execution 판단
- hard guard action 판단
- reverse action 판단

을 별도 owner로 빼는 것이다.

이 단계의 핵심은 “실행”을 빼는 것이 아니라 “실행 후보를 정하는 해석”을 먼저 빼는 데 있다.


## 2. 지금 섞여 있는 것

현재 청산 실행 seam에는 아래 세 갈래가 서로 다른 위치에 퍼져 있다.

1. `recovery wait / recovery close / recovery reverse`
2. `profit giveback / plus-to-minus / adverse hard guard`
3. `adverse reversal / standard reversal`

문제는 이 셋이 모두 “실행 직전 candidate 판단”인데,
owner가 한 군데로 모여 있지 않다는 점이다.


## 3. 이번 단계에서 분리할 owner

### 3-1. recovery execution candidate

이 owner는 지금 wait state와 utility winner를 읽고

- 그냥 종료할지
- 잠깐 더 들고 갈지
- 반전까지 허용할지

를 정한다.

권장 파일:

- `backend/services/exit_recovery_execution_policy.py`


### 3-2. hard guard action candidate

이 owner는 hard guard 계열이 실제로 어떤 action을 밀어붙일지 정한다.

- profit giveback이면 lock exit
- plus-to-minus면 protect exit
- adverse 장면이면 protect / lock / adverse reverse / adverse stop

중요한 점은 이 owner가 “실행”까지 하면 안 되고,
어떤 action이 맞는지를 candidate surface로 먼저 반환해야 한다는 점이다.

권장 파일:

- `backend/services/exit_hard_guard_action_policy.py`


### 3-3. reverse action candidate

이 owner는 hard guard 밖에서 나오는 두 종류의 반전 후보를 맡는다.

- adverse recheck 이후 반전 후보
- 일반 reversal confirm 이후 반전 후보

이 단계에서는 runtime call이나 streak state 자체보다는,
이미 계산된 숫자와 상태를 보고 “지금 반전이 맞는가”를 정하는 surface를 먼저 분리한다.

권장 파일:

- `backend/services/exit_reverse_action_policy.py`


## 4. 구현 순서

가장 안전한 순서는 아래다.

1. recovery candidate를 먼저 분리한다.
2. hard guard decision tree를 pure helper로 빼고 `ExitRiskGuard`는 executor wrapper로 줄인다.
3. adverse reverse / standard reversal candidate를 helper로 뺀다.
4. `manage_positions.py`는 candidate helper 결과를 읽고 실행만 하게 만든다.


## 5. 이번 단계에서 바꾸지 않을 것

이번 단계는 candidate owner 분리 단계이므로 아래는 유지하는 것이 중요하다.

- 기존 exit reason 문자열
- 기존 metric key 이름
- 기존 reverse action 방향 계산
- 기존 `ExitRiskGuard`의 execute timing
- 기존 reversal streak 저장 방식


## 6. direct 테스트 권장안

- `tests/unit/test_exit_recovery_execution_policy.py`
- `tests/unit/test_exit_hard_guard_action_policy.py`
- `tests/unit/test_exit_reverse_action_policy.py`

핵심은 “어떤 action을 할지”를 direct helper 수준에서 고정하는 것이다.


## 7. 완료 기준

E4-2가 끝났다고 부를 수 있으려면 아래가 보여야 한다.

1. recovery 판단이 shared helper owner에 있다.
2. hard guard decision tree가 `ExitRiskGuard` 본문 밖 helper에 있다.
3. adverse reverse / standard reversal candidate가 helper owner로 보인다.
4. manage loop는 candidate를 읽고 실행하는 조합기 형태에 더 가까워진다.
