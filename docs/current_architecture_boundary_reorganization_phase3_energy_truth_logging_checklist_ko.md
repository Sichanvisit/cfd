# CFD 현재 아키텍처 정리 Phase 3 체크리스트

부제: Energy Truthful Usage Logging

작성일: 2026-03-27 (KST)

## 1. Phase 목표

Phase 3의 목표는 energy usage trace를 `결과 기반 추론`에서 `실제 branch 사용 기록` 중심으로 끌어올리는 것이다.

현재 trace는 이미 유용하지만, replay/forensics/ML rollout 설명력을 더 높이려면 branch-truth 성격이 필요하다.


## 2. 현재 문제 요약

현재 관련 핵심 구간:

- `backend/services/energy_contract.py:1419-1548`

현재 구조는 아래와 같다.

- 최종 payload 결과를 보고 consumed_fields를 추정
- 그 결과를 `consumer_usage_trace`에 부착

이 구조는 완전히 틀린 것은 아니지만, 이상적인 형태는 아니다.

이상적인 형태는 아래다.

- 실제 분기 내부에서
- 어떤 field를 읽었는지
- 왜 사용했는지
- 그 자리에서 기록


## 3. 대상 파일

- `backend/services/energy_contract.py`
- `backend/services/entry_service.py`
- 필요 시 `backend/services/wait_engine.py`
- 관련 unit tests


## 4. 권장 구현 방향

### 4-1. usage recorder 개념 도입

예시 개념:

- `consumed_fields_recorder`
- `record_energy_usage(field_name, reason)`

핵심은 분기 내부에서 append하는 것이다.

### 4-2. attach 단계는 formatting 위주로 축소

`attach_energy_consumer_usage_trace(...)`는 가능하면 아래 역할만 맡는 것이 좋다.

- 정규화
- metadata에 붙이기
- compatibility field 유지

### 4-3. fallback inference는 유지

바로 모든 branch를 다 계측하지 못할 수 있으므로, 결과 기반 재구성은 한동안 fallback으로 남겨두는 편이 안전하다.


## 5. 체크리스트

### 5-1. 현재 inference field inventory

- 현재 어떤 조건에서 어떤 consumed_fields를 추론하는지 표로 정리한다
- `soft_block`, `confidence_adjustment`, `forecast_gap_usage` 계열을 먼저 나눈다

### 5-2. 기록 API 설계

- branch 내부에서 호출 가능한 작은 recorder API를 만든다
- duplicate field append 방지 규칙을 정한다
- field뿐 아니라 reason/branch label도 남길지 결정한다

### 5-3. entry_service 계측

- `energy_soft_block` live branch
- priority hint 적용 branch
- confidence adjustment branch
- forecast gap usage branch

를 먼저 계측한다

### 5-4. wait_engine 계측 여부 판단

- wait decision에서 energy hints를 실제 소비하는 branch도 trace 대상에 넣을지 결정한다
- 넣는다면 wait path와 entry path trace를 어떻게 구분할지 정한다

### 5-5. attach/fallback 정리

- recorder 결과가 있으면 그 값을 우선 사용한다
- recorder 결과가 없을 때만 inference fallback을 사용한다
- trace에 `usage_source=recorded|inferred` 같은 구분자를 둘지 검토한다

### 5-6. 테스트 보강

- recorded branch가 있으면 inferred 값과 충돌하지 않는지
- soft block branch에서 실제 consumed_fields가 기대대로 남는지
- forecast gap live gate branch가 기대대로 남는지
- compatibility fallback이 기존 행위와 크게 어긋나지 않는지


## 6. 완료 기준

- 적어도 핵심 energy branch들은 branch-level recorded trace를 남긴다
- trace를 보고 “추정”인지 “실제 기록”인지 구분할 수 있다
- 기존 contract를 깨지 않고 점진 전환이 가능하다


## 7. 건드리면 안 되는 것

- trace 개선을 하면서 decision logic 자체를 동시에 크게 바꾸지 말 것
- usage logging 개선을 이유로 identity owner를 건드리지 말 것
- fallback inference를 너무 빨리 제거하지 말 것


## 8. 권장 테스트 명령

- `pytest tests/unit/test_entry_service_guards.py -k "energy_soft_block" -q`
- 관련 신규 trace 테스트
- 필요 시 `pytest tests/unit/test_trading_application_runtime_status.py -q`


## 9. Phase 종료 후 확인 포인트

- `consumer_usage_trace`가 recorded/inferred 여부를 구분할 수 있는지
- energy soft block branch의 consumed_fields가 실제 코드 분기와 맞는지
- trace 품질이 runtime/detail export와 모순되지 않는지
