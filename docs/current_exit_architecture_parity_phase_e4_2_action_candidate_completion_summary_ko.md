# 청산 구조 정렬 Phase E4-2 완료 요약

작성일: 2026-03-29 (KST)
현재 상태: E4-2 recovery / hard-guard / reverse candidate extraction 완료

## 1. 이번 단계에서 닫은 것

이번 단계의 목적은 청산 실행 직전의 핵심 action candidate를
`manage loop`와 `ExitRiskGuard` 본문 밖 owner로 빼는 것이었다.

이번에 실제로 분리된 것은 아래 세 갈래다.

- recovery execution candidate
- hard guard action candidate
- reverse action candidate


## 2. 새로 분리된 owner

### recovery candidate

- `backend/services/exit_recovery_execution_policy.py`

이 owner는 wait state와 utility winner를 읽고
`hold / exit / reverse` 중 어떤 recovery 성격이 맞는지를 정한다.


### hard guard candidate

- `backend/services/exit_hard_guard_action_policy.py`

이 owner는 hard guard 계열이
`lock / protect / adverse reverse / adverse stop / defer`
중 어디로 가야 하는지를 먼저 surface로 만든다.


### reverse candidate

- `backend/services/exit_reverse_action_policy.py`

이 owner는

- adverse reverse candidate
- standard reversal candidate

를 별도 helper로 계산한다.


## 3. 무엇이 달라졌는가

이전에는

- recovery 판단은 `exit_manage_positions.py`
- hard guard decision tree는 `ExitRiskGuard`
- reversal branch 판단은 다시 `exit_manage_positions.py`

에 흩어져 있었다.

지금은 이 셋이 모두 shared helper owner를 갖게 됐고,
caller는 helper 결과를 읽고 실제 exit 실행만 하는 쪽으로 조금 더 얇아졌다.


## 4. caller 변화

### manage loop

`backend/services/exit_manage_positions.py`

이제 이 파일은

- recovery candidate를 shared helper에 위임하고
- adverse reverse candidate를 shared helper에 위임하고
- standard reversal candidate를 shared helper에 위임한다.


### ExitRiskGuard

`backend/services/exit_engines.py`

이제 `ExitRiskGuard.try_execute_hard_risk_guards(...)`는
직접 decision tree를 길게 들고 있기보다
hard guard candidate helper를 호출한 뒤
그 결과를 실행하는 wrapper에 더 가까워졌다.


## 5. 이번 단계에서 유지한 것

이번 단계는 owner 분리 단계이므로 아래는 유지했다.

- 기존 reason 문자열
- 기존 metric key 이름
- 기존 reverse 방향 계산
- 기존 execute timing
- 기존 reversal streak 저장 방식

즉 동작 변경보다 execution seam 정리에 더 가까운 단계다.


## 6. 검증

직접 추가한 회귀

- `tests/unit/test_exit_recovery_execution_policy.py`
- `tests/unit/test_exit_hard_guard_action_policy.py`
- `tests/unit/test_exit_reverse_action_policy.py`

연결 회귀

- `tests/unit/test_exit_engines.py`
- `tests/unit/test_exit_recovery_execution.py`
- `tests/unit/test_exit_profit_protection.py`
- `tests/unit/test_wait_engine.py`
- `tests/unit/test_decision_models.py`


## 7. 다음 단계

이제 자연스러운 다음 단계는 E4-3이다.

즉 아직 manage loop에 남아 있는

- partial close
- stop-up / break-even move
- protect / lock / stage exit

계열을 action candidate owner로 빼는 작업이다.

이번 E4-2로 reversal / hard-guard / recovery 후보가 정리됐기 때문에,
다음부터는 execution seam을 더 균일한 형태로 줄여갈 수 있다.
