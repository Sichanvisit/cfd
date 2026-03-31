# CFD 현재 아키텍처 정리 Phase 4 체크리스트

부제: EntryService Slimming

작성일: 2026-03-27 (KST)

## 1. Phase 목표

Phase 4의 목표는 EntryService를 점진적으로 `execution guard 중심`으로 되돌리는 것이다.

이 단계는 가장 가치가 크지만 회귀 위험도 가장 높다.

따라서 반드시 Phase 1~3 이후에 진행하는 편이 안전하다.


## 2. 현재 문제 요약

현재 EntryService는 execution guard만 수행하지 않는다.

특히 아래 구간은 scene-specific policy shaping 성격이 강하다.

- `backend/services/entry_service.py:3089-3116`

여기에는 아래가 섞여 있다.

- symbol-specific relief
- probe plan 조건
- box/bb 상태
- energy soft block reason/strength
- scenario threshold

이 구조는 유지보수 비용을 빠르게 키운다.


## 3. 대상 파일

- `backend/services/entry_service.py`
- 필요 시 `backend/services/consumer_*`
- 필요 시 `backend/services/layer_mode_*`
- 필요 시 `backend/services/energy_*`
- 관련 unit tests


## 4. 권장 구현 방향

### 4-1. 먼저 inventory를 만든다

바로 코드를 옮기기보다, 먼저 EntryService 내부 scene-specific branch 목록을 만든다.

분류 기준 예시:

- execution safety
- consumer policy
- layer mode influence
- energy advisory
- symbol-specific exception

### 4-2. owner 후보를 정한다

각 branch를 아래 중 하나로 보낸다.

- EntryService에 남김
- Consumer owner로 이동
- LayerMode owner로 이동
- Energy helper/advisory owner로 이동

### 4-3. 동작 보존 중심으로 이동한다

이 단계는 구조 개선 단계이지 성능 튜닝 단계가 아니다.

따라서 원칙은 아래다.

- 먼저 동작 동일성 유지
- 그다음 owner 위치만 이동
- 마지막에 dead code/compatibility 정리


## 5. 체크리스트

### 5-1. scene-specific branch inventory

- `entry_service.py` 안의 symbol/scenario 특수 분기 목록 작성
- 각 분기에 현재 입력 필드와 출력 영향 필드 기록
- 테스트 유무 확인

### 5-2. owner 재분류

- 각 분기를 execution/consumer/layer_mode/energy owner 후보로 재분류
- 이유를 한 줄씩 남긴다

### 5-3. 이동 우선순위 결정

- 가장 덜 위험한 분기부터 이동한다
- 공통 branch부터 옮기고 symbol 특수 분기는 나중에 다룬다

### 5-4. 코드 이동

- owner 위치로 함수/정책표를 이동한다
- EntryService는 호출/조합 역할만 남긴다
- 가능하면 `if symbol == ...` 형태를 줄인다

### 5-5. compatibility 정리

- 이동 후 남은 dead branch를 정리한다
- 중복 metadata write가 있으면 줄인다

### 5-6. 테스트 보강

- branch 이동 전후 동작 동일성 테스트
- symbol-specific 예외 테스트
- regression test snapshot 재확인


## 6. 완료 기준

- EntryService를 읽을 때 execution safety owner로 해석된다
- scene-specific policy branch가 대폭 줄어든다
- symbol별 특수 예외가 명시적 owner 아래로 이동한다
- 기능 회귀 없이 테스트가 유지된다


## 7. 건드리면 안 되는 것

- Phase 1~3 이전에 이 작업을 먼저 하지 말 것
- observability가 약한 상태에서 내부 branch를 크게 걷어내지 말 것
- owner를 옮긴다는 이유로 behavior tuning까지 동시에 하지 말 것


## 8. 권장 테스트 명령

- `pytest tests/unit/test_entry_service_guards.py -q`
- 관련 chart/runtime status 테스트
- 필요 시 symbol-specific scenario test 추가


## 9. Phase 종료 후 확인 포인트

- EntryService 파일 크기와 branch 밀도가 실제로 줄었는지
- symbol-specific 예외가 어디 owner인지 문서로 설명 가능한지
- 새 스레드에서 EntryService를 읽었을 때 “왜 여기까지 알고 있지?”라는 느낌이 줄었는지
