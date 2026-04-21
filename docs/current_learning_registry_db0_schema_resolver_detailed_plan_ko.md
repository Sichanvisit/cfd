# DB0 schema + resolver 상세 계획

## 목표

중앙 학습 변수 레지스트리를 실제 서비스가 직접 바인딩하기 전에,

- 공통 필드 계약
- 공통 resolver
- key 교차 대조 audit

를 먼저 고정한다.

즉 이 단계는 서비스 문구를 바꾸는 단계가 아니라,
다음 단계에서 detector / weight review / proposal / forecast가
제각각 다른 방식으로 registry를 읽지 않게 만드는 기초 공사다.

## 왜 DB0가 먼저 필요한가

지금 바로 각 서비스가

- 레지스트리 import
- raw key lookup
- label 변환

을 제각각 시작하면,
직접 바인딩은 들어가도 스타일이 금방 갈라진다.

그래서 먼저 필요한 것은

1. 공통 출력 필드
2. 공통 resolver 함수
3. 어떤 key를 앞으로 묶을지 보는 binding plan
4. 현재 몇 % 묶였는지 보는 progress audit

이다.

## 이번 단계에서 하는 것

### 1. resolver 모듈 추가

파일:

- [learning_registry_resolver.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_registry_resolver.py)

핵심 역할:

- `registry_key` 기준 row 조회
- direct binding용 필드 묶음 생성
- `evidence_registry_keys / target_registry_keys` relation 생성
- 단계별 direct binding plan 제공

### 2. 공통 바인딩 필드 선고정

resolver가 기본적으로 만드는 필드:

- `registry_key`
- `registry_label_ko`
- `registry_description_ko`
- `registry_category`
- `registry_category_label_ko`
- `registry_component_key`
- `registry_runtime_role_ko`
- `registry_proposal_role_ko`
- `registry_source_file`
- `registry_source_field`
- `registry_binding_mode`
- `registry_binding_version`
- `registry_found`

### 3. relation 묶음 지원

복합 detector/proposal을 위해 아래 2축을 지원한다.

- `evidence_registry_keys`
- `target_registry_keys`

이 단계에서는 실제 서비스 적용보다,
이 두 개념을 먼저 공통 계약으로 굳히는 것이 목표다.

### 4. binding plan / progress audit 추가

기존 audit인

- [learning_apply_connection_audit.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_apply_connection_audit.py)

를 확장해 아래를 본다.

- direct binding 대상 stage
- stage별 target registry key 수
- 계획 key가 실제 registry에 모두 있는지
- detector / weight_review / feedback / forecast 중 어디가 이미 resolver를 직접 쓰는지
- binding progress (`bound / unbound / rate`)

## 이번 단계에서 하지 않는 것

- detector row에 실제 `registry_key` 주입
- weight review payload 직접 변경
- proposal summary 직접 변경
- forecast/report 문구 직접 변경

즉 DB0는 끝까지 준비 단계다.

## 다음 단계와의 연결

DB0가 끝나면 아래가 가능해진다.

### DB1

- detector direct binding
- `registry_key`, `evidence_registry_keys` 주입

### DB2

- state25 weight review direct binding
- `target_registry_keys` 주입

### DB3

- feedback/proposal runtime direct binding

## 완료 조건

- resolver 모듈이 존재한다
- direct binding field contract를 resolver가 실제 코드로 구현한다
- audit에서 binding plan과 binding progress를 볼 수 있다
- 다음 서비스 단계가 resolver를 재사용할 수 있는 상태가 된다
