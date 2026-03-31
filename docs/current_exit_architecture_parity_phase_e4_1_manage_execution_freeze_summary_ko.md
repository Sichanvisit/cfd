# 청산 구조 정렬 Phase E4-1 완료 요약

작성일: 2026-03-29 (KST)
현재 상태: E4-1 manage execution input / runtime sink freeze 완료

## 1. 이번 단계에서 닫은 것

이번 단계의 목적은 `exit_manage_positions.py` 안에서 섞여 있던 두 seam을 먼저 얼리는 것이었다.

1. 최신 runtime snapshot에서 청산 판단 surface를 읽어오는 입력면
2. trade logger / live metrics로 같은 의미를 다시 써내리는 sink면

이번 구현으로 이 두 영역은 각각 별도 contract를 갖게 됐다.

- `backend/services/exit_manage_execution_input_contract.py`
- `backend/services/exit_manage_runtime_sink_contract.py`


## 2. 무엇이 달라졌는가

이전에는 manage loop 본문이 직접 아래를 모두 했다.

- `exit_utility_v1` 읽기
- `exit_manage_context_v1` 읽기
- `exit_wait_taxonomy_v1` 읽기
- management / invalidation / effective exit profile 재해석
- logger payload 직접 조립
- live metrics payload 직접 조립

지금은 흐름이 아래처럼 바뀌었다.

1. `exit_manage_execution_input_v1`를 한 번 만든다.
2. 그 contract에서 현재 청산 판단 surface를 읽는다.
3. `exit_manage_runtime_sink_v1`를 만든다.
4. logger payload와 live metrics payload는 sink contract 결과만 사용한다.

즉 `exit_manage_positions.py`는 점점 “실행 조합기” 쪽으로 얇아지고 있고, 입력 해석과 sink 조립은 본문 밖으로 빠지기 시작했다.


## 3. 새로 생긴 입력 contract의 의미

`exit_manage_execution_input_v1`는 manage loop가 실제로 읽는 청산 표면을 한 덩어리로 고정한다.

여기에는 아래가 들어간다.

- 거래 식별 정보
- handoff에서 넘어온 management / invalidation 식별자
- 현재 선택된 stage, policy stage, execution profile
- 실제로 적용되는 exit profile
- 청산 utility winner와 이유
- wait 선택 여부와 wait decision
- 청산 wait taxonomy의 state / decision / bridge 결과
- protect / lock / hold threshold와 confirm ticks, delay ticks
- 현재 regime, observed regime, switch detail
- peak profit, giveback
- shock summary와 progress
- runtime snapshot의 `exit_utility_v1`, `exit_manage_context_v1`, `exit_wait_taxonomy_v1`, `exit_prediction_v1`

핵심은 “manage loop가 지금 무엇을 input truth로 삼고 있는가”가 이제 한 contract 이름 아래 고정된다는 점이다.


## 4. 새로 생긴 sink contract의 의미

`exit_manage_runtime_sink_v1`는 입력 contract를 받아 아래 두 payload를 재생성한다.

- trade logger update payload
- AI / live metrics payload

중요한 점은 이번 단계가 새 의미를 만든 것이 아니라, 기존 payload key를 그대로 유지한 채 조립 위치만 바꿨다는 점이다.

즉 downstream schema는 바꾸지 않고, 조립 책임만 본문 밖으로 뺐다.


## 5. 이번 단계가 중요한 이유

이 작업이 없으면 이후 E4-2, E4-3, E4-4에서 candidate / execution orchestrator를 분리할 때 manage loop 본문이 여전히

- 입력 해석
- action 후보 판단
- sink 기록

을 동시에 들고 있게 된다.

그러면 다음 단계에서 owner를 빼도 다시 본문 안에서 의미가 재조립된다.

이번 E4-1은 그걸 막기 위한 바닥 공사다.


## 6. 현재 기준에서 보장되는 것

이번 단계 이후에도 아래는 그대로 유지된다.

- recovery execution 계산은 기존과 같은 `exit_shadow`를 읽는다.
- AI exit / reversal 판단에 전달되는 live metrics key 이름은 유지된다.
- trade logger에 쓰는 exit policy context key 이름도 유지된다.

즉 동작 의미를 바꾸지 않고 seam만 얼린 단계로 보는 것이 정확하다.


## 7. 검증

직접 추가한 회귀

- `tests/unit/test_exit_manage_execution_input_contract.py`
- `tests/unit/test_exit_manage_runtime_sink_contract.py`

기존 영향 범위 회귀

- `tests/unit/test_exit_recovery_execution.py`
- `tests/unit/test_exit_profit_protection.py`
- `tests/unit/test_wait_engine.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_exit_manage_context_contract.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`


## 8. 다음 단계

이제 자연스러운 다음 단계는 E4-2다.

즉 `exit_manage_positions.py` 안에 남아 있는 아래 action-precheck 계열을 별도 owner로 빼는 작업이다.

- recovery execution candidate
- hard guard candidate
- reverse action candidate

이번 단계로 input과 sink가 얼었기 때문에, 다음 단계부터는 manage loop 본문을 더 안전하게 조합기 형태로 줄여갈 수 있다.
