# 청산 구조 정렬 Phase E2 구현 분해

작성일: 2026-03-29 (KST)
현재 상태: E2 실제 구현 진입용 breakdown, E2-4 구현 완료

## 1. 목적

이 문서는 E2를 바로 구현할 수 있게
대상 파일, 작업 순서, 테스트 범위를 정리한 실행 문서다.

E2의 범위는
`build_exit_wait_state(...)`를 입력 계약, state policy, rewrite, surface contract로 나누는 것
이다.


## 2. 현재 실제 진입점

현재 E2의 중심 진입점은 아래 함수다.

- `backend/services/wait_engine.py`의 `build_exit_wait_state(...)`

이 함수는 지금 아래를 한 자리에서 한다.

1. exit manage context 읽기
2. risk / market / identity 값 추출
3. recovery policy 적용값 읽기
4. 기본 state 후보 결정
5. rewrite 수행
6. metadata 조립
7. `WaitState` 반환

즉 E2의 목표는 이 함수의 “판단 본문”을 하나씩 밖으로 빼는 것이다.


## 3. 추천 작업 순서

추천 순서는 아래와 같다.

1. `E2-1` input contract freeze
2. `E2-2` base state policy extraction
3. `E2-3` state rewrite extraction
4. `E2-4` surface / metadata freeze
5. `WaitEngine` thin orchestrator 정리


## 4. E2-1 구현 분해

### 목표

청산 wait state 입력면을 별도 contract로 얼린다.

### 추천 새 파일

- `backend/services/exit_wait_state_input_contract.py`

### 추천 함수

- `build_exit_wait_state_input_v1(...)`
- `compact_exit_wait_state_input_v1(...)`

### 이 단계에서 포함할 것

- canonical exit manage context
- profit / peak profit / giveback / duration
- regime / box / bb 위치
- entry direction
- adverse risk / tf confirm / score gap
- recovery policy resolved values
- state / belief / symbol edge bias references

### direct 테스트 후보

- `tests/unit/test_exit_wait_state_input_contract.py`

### 추천 테스트 장면

- context 우선 사용
- trade_ctx fallback
- stage_inputs fallback
- compact summary shape

### 완료 기준

WaitEngine이 긴 local variable 다발 대신 `exit_wait_state_input_v1`를 읽는다.


## 5. E2-2 구현 분해

### 목표

기본 state 후보 판정을 policy owner로 뺀다.

### 추천 새 파일

- `backend/services/exit_wait_state_policy.py`

### 추천 함수

- `resolve_exit_wait_state_policy_v1(...)`

### 이 단계에서 다룰 것

- reversal confirm
- active observe
- recovery TP1
- recovery BE
- reverse ready
- cut immediate
- green close
- none

### direct 테스트 후보

- `tests/unit/test_exit_wait_state_policy.py`

### 완료 기준

기본 state 후보와 reason이 WaitEngine 밖의 단일 helper에서 결정된다.


## 6. E2-3 구현 분해

### 목표

rewrite 규칙을 별도 owner로 분리한다.

### 추천 새 파일

- `backend/services/exit_wait_state_rewrite_policy.py`

### 추천 함수

- `apply_exit_wait_state_rewrite_v1(...)`

### 이 단계에서 다룰 것

- green close hold bias
- belief hold extension
- symbol edge hold bias
- fast cut rewrite

### direct 테스트 후보

- `tests/unit/test_exit_wait_state_rewrite_policy.py`

### 완료 기준

base state에서 rewritten state로 바뀐 이유가 별도 helper 결과로 남는다.


## 7. E2-4 구현 분해

### 목표

surface / metadata를 별도 contract로 만든다.

### 추천 새 파일

- `backend/services/exit_wait_state_surface_contract.py`

### 추천 함수

- `build_exit_wait_state_surface_v1(...)`
- `compact_exit_wait_state_surface_v1(...)`

### 이 단계에서 포함할 것

- score
- penalty
- hard_wait
- recovery thresholds
- applied policy ids
- rewrite reason
- compact summary

### direct 테스트 후보

- `tests/unit/test_exit_wait_state_surface_contract.py`

### 완료 기준

metadata 생성이 WaitEngine 본문 밖으로 빠지고
downstream surface가 더 안정적으로 유지된다.


## 8. 기존 회귀와 연결해야 하는 테스트

새 helper direct 회귀 외에 아래를 계속 붙여 봐야 한다.

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_trading_application_runtime_status.py`


## 9. 권장 PR 분할

한 번에 크게 하지 말고 아래처럼 자르는 편이 좋다.

### PR 1

- E2-1

### PR 2

- E2-2

### PR 3

- E2-3

### PR 4

- E2-4
- WaitEngine cleanup


## 10. 가장 먼저 시작할 실제 순서

다음 실제 작업은 아래 순서가 가장 좋다.

1. `exit_wait_state_input_contract.py` 추가
2. `build_exit_wait_state(...)`가 그 contract를 읽게 변경
3. direct helper 테스트 추가
4. `test_wait_engine.py`와 exit taxonomy 회귀 확인

그다음부터는 E2 close-out 또는 E3로 자연스럽게 이어진다.
