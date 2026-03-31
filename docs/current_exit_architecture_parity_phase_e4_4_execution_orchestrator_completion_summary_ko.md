# 청산 구조 정렬 Phase E4-4 완료 요약

작성일: 2026-03-29 (KST)
상태: 완료

## 1. 이번 단계에서 닫은 것

이번 E4-4에서는 `exit_manage_positions.py` 안에 흩어져 있던 실행 분기들을

- 후보 목록
- 우선순위가 있는 실행 계획
- 실행 결과 surface

로 분리했다.

즉 이제 청산 관리 루프는 예전처럼 조건을 하나씩 내려가며 즉시 실행하는 본문에 덜 가깝고,
`candidate -> first-hit plan -> execute -> result surface` 흐름에 더 가까워졌다.


## 2. 새로 생긴 owner

### 2-1. 실행 계획 orchestrator

파일:
- `backend/services/exit_execution_orchestrator.py`

역할:
- recovery phase, managed exit phase처럼 실행 단위를 나누고
- 여러 candidate 중 실제로 먼저 실행할 대상을 고르고
- 선택된 이유, 순서, reverse surface를 한 plan으로 돌려준다

이제 `manage loop`는 "무엇을 먼저 실행할지"를 직접 정하는 대신, orchestrator가 고른 plan을 받아 실행한다.


### 2-2. 실행 결과 surface

파일:
- `backend/services/exit_execution_result_surface.py`

역할:
- 방금 선택된 실행 후보를
  - trade logger handoff payload
  - live metrics payload
  - compact summary

로 번역한다.

이제 실행 직전 정보가 `reason`, `policy_scope`, `execution candidate kind`, `execution status` 형태로 한 surface로 모인다.


## 3. manage loop에서 실제로 바뀐 점

`backend/services/exit_manage_positions.py`는 이제 아래처럼 읽힌다.

1. recovery execution candidate를 만든다.
2. recovery plan을 고른다.
3. recovery result surface를 logger/live metrics에 넘긴다.
4. partial / stop-up은 non-terminal action으로 별도 처리한다.
5. emergency / protect / adverse / mid-stage candidate를 만든다.
6. managed exit plan을 고른다.
7. managed exit result surface를 logger/live metrics에 넘긴다.
8. 선택된 후보만 실제로 실행한다.
9. 아무 것도 선택되지 않으면 그 다음 scalp / reversal 쪽으로 내려간다.

즉 이제 manage loop 본문은 "실행 분기 그 자체"보다 "실행 orchestration"에 더 가까워졌다.


## 4. 이번 단계가 중요한 이유

E4-4가 닫히면서 청산 실행 seam은 아래 기준으로 entry / wait와 더 가까워졌다.

- 먼저 policy/candidate가 만들어진다.
- 그다음 실행 순서가 plan으로 정리된다.
- 마지막에 execution 결과가 별도 surface로 번역된다.

이 차이가 중요한 이유는 세 가지다.

1. 실행 순서를 나중에 바꾸거나 늘릴 때 owner가 명확하다.
2. "왜 이 branch가 먼저 선택됐는가"를 direct test로 잠글 수 있다.
3. logger / live metrics로 전달되는 정보가 본문 중간 변수 묶음이 아니라 contract surface가 된다.


## 5. 이번 단계에서 추가된 테스트

- `tests/unit/test_exit_execution_orchestrator.py`
- `tests/unit/test_exit_execution_result_surface.py`

같이 확인한 기존 회귀:

- `tests/unit/test_exit_profit_protection.py`
- `tests/unit/test_exit_recovery_execution.py`
- `tests/unit/test_exit_engines.py`
- `tests/unit/test_wait_engine.py`
- `tests/unit/test_decision_models.py`


## 6. 검증 결과

확인한 테스트:

- `python -m py_compile backend/services/exit_execution_orchestrator.py backend/services/exit_execution_result_surface.py backend/services/exit_manage_positions.py`
- `pytest tests/unit/test_exit_execution_orchestrator.py tests/unit/test_exit_execution_result_surface.py tests/unit/test_exit_profit_protection.py tests/unit/test_exit_recovery_execution.py tests/unit/test_exit_engines.py tests/unit/test_wait_engine.py tests/unit/test_decision_models.py -q`

결과:

- `66 passed`


## 7. 지금 의미하는 것

이제 청산은 단순히 recent summary와 taxonomy만 있는 단계가 아니다.

다음 네 층이 모두 들어가 있다.

- canonical input contract
- state / decision / utility owner 분리
- recent runtime summary surface
- manage execution orchestrator / result surface

즉 청산도 entry / wait와 꽤 비슷한 밀도의 구조 정렬 상태로 올라왔다고 봐도 된다.


## 8. 다음 자연스러운 축

E4가 닫힌 지금부터의 다음 축은 "청산 구조 정렬 본체"라기보다 아래 둘 중 하나다.

1. exit handoff / runtime read guide close-out
2. exit end-to-end continuity test / lifecycle summary close-out

즉 이제부터는 owner 분해를 더 크게 하기보다,
새 스레드와 운영자가 지금 만들어진 청산 surface를 더 빠르게 읽을 수 있게 마감하는 단계가 자연스럽다.
