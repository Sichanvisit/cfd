# 청산 구조 정렬 Phase E3 구현 분해

작성일: 2026-03-29 (KST)
현재 상태: E3 완료, exit utility decision owner separation core implemented

## 1. 목적

이 문서는 E3를 실제 구현 단위로 쪼개서
어떤 파일을 어떤 순서로 손대면 되는지 바로 실행용으로 정리한 문서다.

E3의 범위는 `WaitEngine.evaluate_exit_utility_decision(...)`를
입력 계약, utility bundle, scene bias, final decision owner로 나누는 것이다.


## 2. 현재 실제 진입점

현재 E3의 실제 진입점은 아래 함수다.

- `backend/services/wait_engine.py`의 `evaluate_exit_utility_decision(...)`

이 함수는 지금 아래를 한 번에 수행한다.

1. stage input 해석
2. base utility 계산
3. state bias 기반 utility 조정
4. scene / symbol / setup 특례 조정
5. recovery utility / reverse eligibility 계산
6. final winner 선택
7. decision reason / taxonomy 연결

즉 E3의 목표는 이 본문을 얇은 orchestrator로 바꾸는 것이다.


## 3. 권장 작업 순서

권장 순서는 아래와 같다.

1. `E3-1` utility input / base bundle freeze
2. `E3-2` recovery utility / reverse eligibility extraction
3. `E3-3` scene bias bundle extraction
4. `E3-4` final winner / decision policy extraction
5. `WaitEngine` cleanup


## 4. E3-1 구현 분해

### 목표

base utility의 입력과 1차 계산 결과를 contract로 분리한다.

### 추천 파일

- `backend/services/exit_utility_input_contract.py`
- `backend/services/exit_utility_base_bundle.py`

### 추천 함수

- `build_exit_utility_input_v1(...)`
- `compact_exit_utility_input_v1(...)`
- `resolve_exit_utility_base_bundle_v1(...)`

### 여기서 넣을 것

- profit / peak profit / giveback / duration
- adverse risk / score gap
- entry direction / recovery policy id / exit profile id
- regime / current box / current bb
- locked profit / upside / giveback cost / reverse edge
- wait improvement / wait miss cost
- base utility 4종

### direct 테스트 후보

- `tests/unit/test_exit_utility_input_contract.py`
- `tests/unit/test_exit_utility_base_bundle.py`

### 완료 기준

`evaluate_exit_utility_decision(...)`이 base utility 4종을 직접 만들지 않는다.

### 현재 구현 상태

- `backend/services/exit_utility_input_contract.py` 추가 완료
- `backend/services/exit_utility_base_bundle.py` 추가 완료
- `WaitEngine.evaluate_exit_utility_decision(...)`가 input contract와 base bundle을 사용하도록 전환 완료
- `tests/unit/test_exit_utility_input_contract.py` 추가 완료
- `tests/unit/test_exit_utility_base_bundle.py` 추가 완료


## 5. E3-2 구현 분해

### 목표

recovery utility와 reverse eligibility를 별도 owner로 뺀다.

### 추천 파일

- `backend/services/exit_recovery_utility_bundle.py`
- `backend/services/exit_reverse_eligibility_policy.py`

### 추천 함수

- `resolve_exit_recovery_utility_bundle_v1(...)`
- `resolve_exit_reverse_eligibility_v1(...)`

### 여기서 넣을 것

- u_cut_now
- u_wait_be
- u_wait_tp1
- u_reverse
- allow_wait_be / allow_wait_tp1
- tight-protect green disable
- reverse min prob / hold seconds / score gap
- reverse eligible reason

### direct 테스트 후보

- `tests/unit/test_exit_recovery_utility_bundle.py`
- `tests/unit/test_exit_reverse_eligibility_policy.py`

### 완료 기준

recovery / reverse 후보의 생성과 차단 이유가 helper 결과로 보인다.

### 현재 구현 상태

- `backend/services/exit_recovery_utility_bundle.py` 추가 완료
- `backend/services/exit_reverse_eligibility_policy.py` 추가 완료
- `WaitEngine.evaluate_exit_utility_decision(...)`가 recovery utility bundle과 reverse eligibility helper를 사용하도록 전환 완료
- `tests/unit/test_exit_recovery_utility_bundle.py` 추가 완료
- `tests/unit/test_exit_reverse_eligibility_policy.py` 추가 완료


## 6. E3-3 구현 분해

### 목표

scene / symbol / setup bias를 하나의 utility bias bundle로 분리한다.

### 추천 파일

- `backend/services/exit_utility_scene_bias_policy.py`

### 추천 함수

- `resolve_exit_utility_scene_bias_bundle_v1(...)`

### 여기서 넣을 것

- range middle hold bias
- opposite edge completion bias
- lower reversal hold bias
- XAU lower edge-to-edge hold bias
- BTC upper support bounce bias
- BTC lower hold bias
- BTC lower mid noise hold bias
- NAS upper hold bias

### direct 테스트 후보

- `tests/unit/test_exit_utility_scene_bias_policy.py`

### 완료 기준

scene-specific utility 조정이 별도 bundle 결과로 나오고,
`WaitEngine` 본문에서는 그 bundle만 적용한다.

### 현재 구현 상태

- `backend/services/exit_utility_scene_bias_policy.py` 추가 완료
- `WaitEngine.evaluate_exit_utility_decision(...)`가 scene bias bundle을 사용하도록 전환 완료
- `tests/unit/test_exit_utility_scene_bias_policy.py` 추가 완료


## 7. E3-4 구현 분해

### 목표

final winner 선택과 decision reason, taxonomy 연결을 별도 owner로 뺀다.

### 추천 파일

- `backend/services/exit_utility_decision_policy.py`

### 추천 함수

- `resolve_exit_utility_decision_policy_v1(...)`

### 여기서 넣을 것

- loss/recovery path priority
- green/profit path priority
- final winner
- winner value
- decision reason
- wait selected / wait decision
- taxonomy input shaping

### direct 테스트 후보

- `tests/unit/test_exit_utility_decision_policy.py`

### 완료 기준

`winner / reason / selected / taxonomy input`이 helper 결과로 나온다.

### 현재 구현 상태

- `backend/services/exit_utility_decision_policy.py` 추가 완료
- `WaitEngine.evaluate_exit_utility_decision(...)`가 final winner / decision policy helper를 사용하도록 전환 완료
- `tests/unit/test_exit_utility_decision_policy.py` 추가 완료


## 8. 같이 묶어서 봐야 하는 기존 회귀

새 helper direct 테스트 외에 아래 회귀는 계속 함께 봐야 한다.

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_trading_application_runtime_status.py`
- 필요시 `tests/unit/test_exit_recovery_execution.py`


## 9. 권장 PR 분할

### PR 1

- E3-1

### PR 2

- E3-2

### PR 3

- E3-3

### PR 4

- E3-4
- `WaitEngine` cleanup


## 10. 가장 먼저 시작할 실제 작업

다음 실제 작업은 아래 순서가 가장 좋다.

1. `exit_utility_input_contract.py` 추가
2. `exit_utility_base_bundle.py` 추가
3. `evaluate_exit_utility_decision(...)`가 base bundle을 읽게 변경
4. direct helper 테스트 추가
5. `test_wait_engine.py`와 `test_decision_models.py` 회귀 확인

그다음부터는 E3-2로 자연스럽게 이어진다.
