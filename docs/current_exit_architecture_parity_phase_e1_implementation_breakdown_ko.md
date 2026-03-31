# 청산 구조 정렬 Phase E1 구현 분해

작성일: 2026-03-29 (KST)
현재 상태: E1 실제 구현 진입용 breakdown, E1 전체 구현 완료

## 1. 목적

이 문서는 Phase E1을 바로 구현할 수 있게
작업 순서와 파일 범위를 정리한 실행 문서다.

E1의 범위는
`exit profile / recovery policy router를 identity / posture / base policy / overlay owner로 분리하는 것`
이다.


## 2. 현재 실제 진입점

현재 E1의 실질적인 진입점은 한 파일이다.

- `backend/services/exit_profile_router.py`

여기서 현재 크게 네 블록이 보인다.

1. state 기반 execution override 계산
2. belief 기반 execution override 계산
3. 기본 exit profile resolve
4. recovery policy resolve

즉 이 파일이 지금 E1의 write scope 중심이다.


## 3. 추천 작업 순서

추천 순서는 아래와 같다.

1. `E1-1` profile identity extraction
2. `E1-2` lifecycle posture extraction
3. `E1-3` recovery base policy extraction
4. `E1-4` temperament overlay extraction
5. router 조합기 정리

이 순서가 좋은 이유는
앞쪽 두 단계가 비교적 안정적이고,
뒤쪽 둘은 숫자와 scene bias가 얽혀 있어서
나중에 빼는 편이 안전하기 때문이다.


## 4. E1-1 구현 분해

### 목표

기본 exit profile identity를 별도 owner로 뺀다.

### 추천 새 파일

- `backend/services/exit_profile_identity_policy.py`

### 추천 함수

- `resolve_exit_profile_identity_v1(...)`

### 이 단계에서 수정할 파일

- 새 파일 추가
- `backend/services/exit_profile_router.py`
- 관련 단위 테스트 파일 추가

### direct 테스트 후보

- `tests/unit/test_exit_profile_identity_policy.py`

### 추천 테스트 장면

- reversal profile -> tight protect
- breakout hold -> hold then trail
- support hold -> tight protect
- invalidation fallback
- setup fallback
- neutral fallback

### 완료 기준

기존 `resolve_exit_profile(...)`는
새 owner를 호출하는 thin wrapper에 가까워지거나,
혹은 내부에서 새 owner를 바로 재사용하게 된다.


## 5. E1-2 구현 분해

### 목표

market posture에 따른 lifecycle profile 조정을 별도 owner로 뺀다.

### 추천 새 파일

- `backend/services/exit_lifecycle_profile_policy.py`

### 추천 함수

- `apply_exit_lifecycle_profile_v1(...)`

### direct 테스트 후보

- `tests/unit/test_exit_lifecycle_profile_policy.py`

### 추천 테스트 장면

- range가 아닐 때 no-op
- range + hold_then_trail -> tighter posture
- range + protect_then_hold + middle -> tighter posture
- range지만 조정이 필요 없는 경우 유지

### 완료 기준

기존 lifecycle adjustment 로직이 별도 helper로 이동하고,
router에서는 호출만 남는다.


## 6. E1-3 구현 분해

### 목표

recovery 기본 수치 정책을 별도 owner로 뺀다.

### 추천 새 파일

- `backend/services/exit_recovery_base_policy.py`

### 추천 함수

- `resolve_exit_recovery_base_policy_v1(...)`

### 이 단계에서 포함할 것

- management profile별 base policy
- invalidation별 base policy
- setup / symbol별 base policy
- base wait / reverse / loss / time 설정

### 이 단계에서 제외할 것

- state / belief / edge overlay

### direct 테스트 후보

- `tests/unit/test_exit_recovery_base_policy.py`

### 추천 테스트 장면

- reversal profile BTC
- support hold profile
- breakout hold / breakdown hold
- range upper reversal symbol variants
- range lower reversal symbol variants
- breakout retest variants
- invalidation failure variants

### 완료 기준

recovery의 기본 숫자 테이블이
state / belief overlay 없이 독립적으로 재사용 가능해진다.


## 7. E1-4 구현 분해

### 목표

state / belief / edge overlay를 별도 owner로 뺀다.

### 추천 새 파일

- `backend/services/exit_recovery_temperament_policy.py`

### 추천 함수

- `resolve_exit_recovery_temperament_bundle_v1(...)`
- `apply_exit_recovery_temperament_v1(...)`

### 이 단계에서 포함할 것

- state wait multiplier
- state fast-exit pressure
- belief same-side / opposite-side bias
- edge rotation reverse bias
- symbol edge execution override

### direct 테스트 후보

- `tests/unit/test_exit_recovery_temperament_policy.py`

### 추천 테스트 장면

- no state/no belief -> neutral
- fast-exit state -> wait 축소
- same-side confirmed belief -> hold extension
- strong opposite belief -> fast cut
- edge rotation -> prefer reverse
- symbol edge execution payload 보존

### 완료 기준

overlay 결과가 bundle로 분리되고,
최종 policy는 base policy + overlay 적용 결과로 읽힌다.


## 8. 기존 회귀와 연결해야 하는 테스트

새 helper direct 회귀 외에 아래를 계속 붙여 봐야 한다.

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_trading_application_runtime_status.py`

특히 중요한 것은
E1을 진행하면서도
기존 exit taxonomy와 recent exit summary가 깨지지 않는지 확인하는 것이다.


## 9. 권장 PR 분할

한 번에 크게 하지 말고 아래처럼 자르는 편이 좋다.

### PR 1

- E1-1
- E1-2

### PR 2

- E1-3

### PR 3

- E1-4
- final router cleanup

이렇게 하면 각 단계의 의미 변화가 선명하다.


## 10. 가장 먼저 시작할 실제 순서

다음 실제 작업은 아래 순서로 들어가면 된다.

1. `exit_profile_identity_policy.py` 추가
2. `resolve_exit_profile(...)`를 새 owner 호출로 치환
3. direct helper 테스트 추가
4. 기존 exit 회귀 돌리기

이게 끝나면 그다음은 자연스럽게 `E1-2`로 이어간다.
