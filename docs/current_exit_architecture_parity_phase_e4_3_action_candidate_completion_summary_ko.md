# 청산 구조 정렬 Phase E4-3 완료 요약

작성일: 2026-03-29 (KST)
상태: 완료

## 1. 이번 단계에서 닫은 것

이번 E4-3에서는 `exit_manage_positions.py` 안에 남아 있던 아래 실행 후보들을 별도 owner로 분리했다.

- partial close 후보
- stop-up / break-even move 후보
- protect / lock / time stop / target 계열 stage exit 후보

즉 이번 단계의 핵심은 `manage loop가 직접 조건을 길게 들고 판단하던 부분`을 `candidate helper가 먼저 결정하고 loop는 실행만 하는 구조`로 바꾼 것이다.


## 2. 새로 생긴 owner

### 2-1. partial close 후보

파일:
- `backend/services/exit_partial_action_policy.py`

역할:
- partial close가 가능한지
- 현재 move/profit 조건이 문턱을 넘었는지
- 얼마를 줄일지
- partial 직후 break-even을 어디로 둘지

를 한 번에 계산한다.

이제 manage loop는 더 이상 partial trigger, volume ratio, break-even price를 본문에서 직접 계산하지 않는다.


### 2-2. stop-up 후보

파일:
- `backend/services/exit_stop_up_action_policy.py`

역할:
- 현재 장면이 stop-up 대상인지
- break-even 수준인지, profit lock 수준인지
- target stop price가 어디인지

를 별도 candidate로 만든다.

기존 `_resolve_profit_stop_up(...)`는 호환 wrapper로 남겨 두었고, 실제 owner는 새 helper가 되었다.


### 2-3. stage exit 후보

파일:
- `backend/services/exit_stage_action_policy.py`

역할:
- protect 계열 짧은 청산
- adverse recheck 보호/락 청산
- mid-stage 시간청산 / lock / target

을 scope별 candidate로 만든다.

이번 구현에서는 scope를 세 가지로 나눴다.

- `protect`
- `adverse_recheck`
- `mid_stage`

이 덕분에 기존 실행 순서를 바꾸지 않고 owner만 밖으로 빼낼 수 있었다.


## 3. manage loop에서 바뀐 점

`backend/services/exit_manage_positions.py`는 이제 아래 순서로 읽힌다.

1. recovery / hard guard / reverse 계열을 먼저 처리한다.
2. partial candidate를 읽고 필요하면 부분청산과 BE 이동을 실행한다.
3. stop-up candidate를 읽고 필요하면 stop을 올린다.
4. protect candidate를 읽고 필요하면 즉시 청산한다.
5. adverse recheck candidate를 읽고 필요하면 보호/락 청산을 실행한다.
6. mid-stage candidate를 읽고 time stop / lock / target을 실행한다.
7. 그 다음에만 scalp / reversal 등의 나머지 branch로 내려간다.

즉 manage loop는 한 단계 더 `candidate orchestrator`에 가까워졌다.


## 4. 이번 단계가 중요한 이유

이번 단계가 닫히면서 청산 실행 루프는 더 이상

- partial rule 계산
- stop-up rule 계산
- protect/lock/time-stop/target rule 계산

을 한 함수 안에서 모두 직접 들고 있지 않게 되었다.

이건 단순 가독성 문제가 아니다.

- 새 조건을 붙일 때 owner를 더 쉽게 찾을 수 있다.
- direct helper 테스트로 stage rule을 바로 잠글 수 있다.
- 이후 E4-4에서 execution orchestrator를 만들기 쉬워진다.
- entry / wait / exit가 모두 `input -> candidate/policy -> execute` 결로 가까워진다.


## 5. 이번 단계에서 추가된 테스트

- `tests/unit/test_exit_partial_action_policy.py`
- `tests/unit/test_exit_stop_up_action_policy.py`
- `tests/unit/test_exit_stage_action_policy.py`

기존 회귀도 함께 다시 확인했다.

- `tests/unit/test_exit_profit_protection.py`
- `tests/unit/test_exit_recovery_execution.py`
- `tests/unit/test_exit_engines.py`
- `tests/unit/test_wait_engine.py`
- `tests/unit/test_decision_models.py`


## 6. 검증 결과

확인한 테스트:

- `python -m py_compile backend/services/exit_partial_action_policy.py backend/services/exit_stop_up_action_policy.py backend/services/exit_stage_action_policy.py backend/services/exit_manage_positions.py`
- `pytest tests/unit/test_exit_partial_action_policy.py tests/unit/test_exit_stop_up_action_policy.py tests/unit/test_exit_stage_action_policy.py tests/unit/test_exit_profit_protection.py tests/unit/test_exit_recovery_execution.py tests/unit/test_exit_engines.py tests/unit/test_wait_engine.py tests/unit/test_decision_models.py -q`

결과:

- `74 passed`


## 7. 지금 남은 큰 축

E4에서 남은 건 이제 `E4-4 execution orchestrator / result surface close-out`이다.

즉 다음 단계의 중심은

- action candidate들의 우선순위 정리
- first-hit execution plan contract
- action result surface
- runtime / logger / live metrics handoff close-out

이다.

이 시점부터는 `rule owner를 더 떼는 단계`보다 `실행 루프 자체를 더 얇은 orchestrator로 마감하는 단계`에 가깝다.
