# 청산 구조 정렬 Phase E4 구현 분해

작성일: 2026-03-29 (KST)
현재 상태: E4 설계 시작, 다음 구현 시작점은 E4-1 manage execution input / runtime sink freeze

## 1. 목적

이 문서는 E4를 실제 구현 단위로 쪼개서
어떤 파일을 어떤 순서로 손대면 되는지 바로 실행용으로 정리한 문서다.

E4의 범위는 `exit_manage_positions.py` 안의 manage execution seam을
input contract, runtime sink, action candidate, execution orchestrator로 나누는 것이다.


## 2. 현재 실제 진입점

현재 E4의 실제 진입점은 아래다.

- `backend/services/exit_manage_positions.py`

이 파일은 지금 아래를 한 번에 많이 수행한다.

1. runtime snapshot read
2. trade logger / live metrics payload 조립
3. recovery / reverse / hard guard 판단
4. partial / stop-up / protect / lock 실행 branch
5. concrete action execute

즉 E4의 목표는 이 루프를
`얇은 execution orchestrator`
로 바꾸는 것이다.


## 3. 권장 작업 순서

권장 순서는 아래와 같다.

1. `E4-1` manage execution input / runtime sink freeze
2. `E4-2` reverse / recovery / hard-guard candidate extraction
3. `E4-3` partial / stop-up / stage exit candidate extraction
4. `E4-4` execution orchestrator / result surface close-out


## 4. E4-1 구현 분해

### 목표

manage loop가 읽는 입력과 sink payload를 contract로 먼저 고정한다.

### 추천 파일

- `backend/services/exit_manage_execution_input_contract.py`
- `backend/services/exit_manage_runtime_sink_contract.py`

### 추천 함수

- `build_exit_manage_execution_input_v1(...)`
- `compact_exit_manage_execution_input_v1(...)`
- `build_exit_manage_runtime_sink_v1(...)`
- `compact_exit_manage_runtime_sink_v1(...)`

### 여기서 넣을 것

- exit shadow / context / taxonomy compact read
- protect / lock / hold / reverse threshold surface
- shock compact surface
- logger payload
- ai live metrics payload

### direct 테스트 후보

- `tests/unit/test_exit_manage_execution_input_contract.py`
- `tests/unit/test_exit_manage_runtime_sink_contract.py`

### 완료 기준

`exit_manage_positions.py`가 logger / live metrics payload를 본문에서 직접 크게 조립하지 않는다.


## 5. E4-2 구현 분해

### 목표

reverse / recovery / hard guard 계열 실행 후보를 별도 owner로 뺀다.

### 추천 파일

- `backend/services/exit_recovery_execution_policy.py`
- `backend/services/exit_hard_guard_action_policy.py`
- `backend/services/exit_reverse_action_policy.py`

### 추천 함수

- `resolve_exit_recovery_execution_candidate_v1(...)`
- `resolve_exit_hard_guard_action_candidate_v1(...)`
- `resolve_exit_reverse_action_candidate_v1(...)`

### 여기서 넣을 것

- recovery reverse candidate
- hard guard reverse candidate
- adverse reverse candidate
- can_reverse / reverse_reason
- reverse action payload

### direct 테스트 후보

- `tests/unit/test_exit_recovery_execution_policy.py`
- `tests/unit/test_exit_hard_guard_action_policy.py`
- `tests/unit/test_exit_reverse_action_policy.py`

### 완료 기준

reverse 계열 실행 이유와 실행 가능 여부가 helper surface로 먼저 보인다.


## 6. E4-3 구현 분해

### 목표

partial / stop-up / stage exit를 개별 action candidate로 뺀다.

### 추천 파일

- `backend/services/exit_partial_action_policy.py`
- `backend/services/exit_stop_up_action_policy.py`
- `backend/services/exit_stage_action_policy.py`

### 추천 함수

- `resolve_exit_partial_action_candidate_v1(...)`
- `resolve_exit_stop_up_action_candidate_v1(...)`
- `resolve_exit_stage_action_candidate_v1(...)`

### 여기서 넣을 것

- partial close candidate
- BE / stop-up candidate
- protect exit candidate
- lock exit candidate
- adverse recheck exit candidate

### direct 테스트 후보

- `tests/unit/test_exit_partial_action_policy.py`
- `tests/unit/test_exit_stop_up_action_policy.py`
- `tests/unit/test_exit_stage_action_policy.py`

### 완료 기준

partial / stop-up / protect / lock branch가 helper candidate 결과로 먼저 보인다.


## 7. E4-4 구현 분해

### 목표

manage loop 본문을 candidate orchestrator로 얇게 만들고,
execution result surface를 별도 contract로 정리한다.

### 추천 파일

- `backend/services/exit_execution_orchestrator.py`
- `backend/services/exit_execution_result_surface.py`

### 추천 함수

- `resolve_exit_execution_plan_v1(...)`
- `build_exit_execution_result_surface_v1(...)`

### 여기서 넣을 것

- candidate priority
- first-hit execution order
- action result payload
- sink write handoff

### direct 테스트 후보

- `tests/unit/test_exit_execution_orchestrator.py`
- `tests/unit/test_exit_execution_result_surface.py`

### 완료 기준

`exit_manage_positions.py`는
candidate를 평가하고 executor를 부르는 얇은 orchestrator에 가까워진다.


## 8. 같이 묶어서 봐야 하는 기존 회귀

새 helper direct 테스트 외에 아래 회귀는 계속 함께 봐야 한다.

- `tests/unit/test_exit_recovery_execution.py`
- `tests/unit/test_exit_profit_protection.py`
- `tests/unit/test_exit_engines.py`
- `tests/unit/test_decision_models.py`
- 필요시 `tests/unit/test_trading_application_runtime_status.py`


## 9. 권장 PR 분할

### PR 1

- E4-1

### PR 2

- E4-2

### PR 3

- E4-3

### PR 4

- E4-4
- `exit_manage_positions.py` cleanup


## 10. 가장 먼저 시작할 실제 작업

다음 실제 작업은 아래 순서가 가장 좋다.

1. `exit_manage_execution_input_contract.py` 추가
2. `exit_manage_runtime_sink_contract.py` 추가
3. `exit_manage_positions.py`가 새 contract를 읽게 변경
4. direct helper 테스트 추가
5. `test_exit_recovery_execution.py`와 `test_exit_profit_protection.py` 회귀 확인

그다음부터는 E4-2로 자연스럽게 이어진다.
