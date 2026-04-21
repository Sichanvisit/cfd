# 중앙 학습 변수 레지스트리 직접 바인딩 세부 실행 로드맵

## 목적

이 로드맵의 목적은

- 이미 살아 있는 학습/제안/반영 루프를 유지한 채
- 중앙 학습 변수 레지스트리를 각 서비스의 직접 참조점으로 점진적으로 수렴시키는 것

이다.

즉 지금 하려는 일은 새 루프를 만드는 것이 아니라,
이미 있는 루프가 **같은 키와 같은 언어를 쓰게 만드는 정제 작업**이다.

## 현재 위치

기준 문서:

- [current_learning_parameter_registry_master_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_parameter_registry_master_ko.md)
- [current_learning_apply_connection_audit_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_apply_connection_audit_ko.md)
- [current_learning_registry_direct_binding_field_contract_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_field_contract_ko.md)

현재 audit 해석:

- 학습/제안/반영 루프 자체는 `PASS`
- 중앙 레지스트리 직접 바인딩은 `WARN`

즉 지금 단계의 핵심은

- 구조를 더 만드는 것

이 아니라

- detector / proposal / review / report가 같은 `registry_key`와 같은 `label_ko`를 직접 보게 만드는 것

이다.

## 전체 원칙

### 1. 생산자부터 묶는다

직접 바인딩은 입력 생산자부터 시작한다.

순서:

1. detector
2. weight review
3. feedback/proposal
4. forecast/report

이유:
- 생산자의 언어가 바뀌어야 downstream이 자연스럽게 따라온다.

### 2. schema와 resolver를 먼저 둔다

서비스가 제각각 레지스트리를 직접 읽기 시작하면 스타일이 갈라질 수 있다.

그래서 먼저

- 공통 field 계약
- 공통 resolver 함수

를 두고,
서비스는 resolver를 통해서만 중앙 기준을 읽게 한다.

### 3. key는 강제, 문장은 유연

강제:
- `registry_key`
- `label_ko`
- `category`
- `component_key`

유연:
- detector summary 문장
- proposal priority 문장
- report 문장 톤

즉 개념 정합성은 높이고, 실험성은 남긴다.

## 실행 단계

### DB0. schema + resolver 선고정

상태:

- 완료

상세 기준:

- [current_learning_registry_db0_schema_resolver_detailed_plan_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_db0_schema_resolver_detailed_plan_ko.md)

#### 목표

직접 바인딩이 서비스별 임시 스타일로 퍼지지 않게, 먼저 공통 출력 계약과 resolver를 고정한다.

#### 해야 할 일

- detector row / proposal item / review item에서 공통으로 쓸 바인딩 필드 합의
- resolver 함수 초안 추가
- key 교차 대조 audit 추가

#### 권장 필드

- `registry_key`
- `registry_label_ko`
- `registry_category`
- `registry_component_key`
- `registry_binding_mode`
- `registry_binding_version`
- `evidence_registry_keys`
- `target_registry_keys`

#### 건드릴 축

- 새 resolver 모듈 추가
  - 예: `backend/services/learning_registry_resolver.py`
- audit 확장
  - [learning_apply_connection_audit.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_apply_connection_audit.py)

#### 완료 조건

- direct binding 대상 서비스가 모두 같은 resolver를 쓰게 할 준비가 된다
- detector evidence key와 레지스트리 key의 교차 대조 결과를 snapshot으로 볼 수 있다

---

### DB1. detector direct binding

상태:

- 완료

상세 기준:

- [current_learning_registry_db1_detector_direct_binding_detailed_plan_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_db1_detector_direct_binding_detailed_plan_ko.md)

#### 목표

detector가 만드는 evidence가 중앙 레지스트리 `registry_key`를 직접 싣게 한다.

#### 왜 첫 단계인가

- detector는 현재 가장 많은 evidence를 surface하는 생산자다
- 여기서 key가 먼저 고정되면 feedback/propose/review가 자연스럽게 따라온다

#### 해야 할 일

- detector row에 `registry_key` 또는 `evidence_registry_keys` 추가
- detector summary는 유지하되, label resolution은 resolver 기준으로 전환
- detector가 raw field를 바로 내보내지 않고 중앙 registry의 label을 우선 사용하게 정리

#### 대상 파일

- [improvement_log_only_detector.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/improvement_log_only_detector.py)

#### 완료 조건

- detector surfaced row가 `registry_key` 또는 `evidence_registry_keys`를 가진다
- 동일 evidence는 detector/report에서 같은 label로 보인다

---

### DB2. state25 weight review direct binding

상태:

- 완료

상세 기준:

- [current_learning_registry_db2_weight_review_direct_binding_detailed_plan_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_db2_weight_review_direct_binding_detailed_plan_ko.md)

#### 목표

weight proposal/review 문구를 중앙 레지스트리 기준으로 직접 읽는다.

#### 이유

- 이미 weight 카탈로그가 잘 정리돼 있고
- bounded review/apply 루프가 안정적이다
- 사용자 체감이 큰 영역이라 통일 효과가 크다

#### 해야 할 일

- weight review candidate에 `target_registry_keys` 추가
- weight row label을 registry 기준으로 읽기
- raw `weight_key`만으로 summary를 만들지 않게 정리

#### 대상 파일

- [state25_weight_patch_review.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/state25_weight_patch_review.py)

#### 완료 조건

- weight review 보고서가 중앙 레지스트리 기준 label/description을 우선 사용한다
- proposal payload가 `target_registry_keys`를 가진다

---

### DB3. feedback/proposal runtime direct binding

상태:

- 완료

상세 기준:

- [current_learning_registry_db3_feedback_proposal_runtime_direct_binding_detailed_plan_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_db3_feedback_proposal_runtime_direct_binding_detailed_plan_ko.md)

#### 목표

detector에서 본 항목과 `/propose`에서 검토하는 항목이 같은 key와 같은 언어로 읽히게 만든다.

#### 해야 할 일

- feedback promotion row에 registry 기반 식별 추가
- proposal summary/priority 문구가 detector의 `registry_key`를 참조하도록 정리
- `evidence_registry_keys`와 `target_registry_keys`를 함께 읽어
  “무엇을 보고 / 무엇을 바꾸려는지”를 분리

#### 대상 파일

- [trade_feedback_runtime.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_feedback_runtime.py)

#### 완료 조건

- detector에서 보던 항목과 proposal에서 검토하는 항목이 언어적으로 바로 이어진다
- feedback-aware promotion이 registry 기반으로 추적 가능해진다

---

### DB4. forecast/report direct binding

상태:

- 완료

상세 기준:

- [current_learning_registry_db4_forecast_report_direct_binding_detailed_plan_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_db4_forecast_report_direct_binding_detailed_plan_ko.md)

#### 목표

forecast 보조 판단 축과 report 문구를 중앙 레지스트리 기준으로 수렴시킨다.

#### 이유

- forecast는 보조 판단 축으로 이미 중요하지만
- detector/proposal보다 문장 실험성이 높다
- 그래서 가장 늦게 들어가는 편이 안전하다

#### 해야 할 일

- forecast summary field에 대응되는 registry row 연결
- report renderer가 forecast 항목 label을 registry 기준으로 우선 읽게 정리
- 필요 시 forecast evidence에도 `registry_key` 계열 필드 추가

#### 대상 파일

- [forecast_state25_runtime_bridge.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/forecast_state25_runtime_bridge.py)
- report renderer 계열

#### 완료 조건

- forecast 보조 판단 축이 detector/proposal/report와 같은 언어를 쓴다

---

### DB5. audit / progress 계층 확장

#### 목표

바인딩이 얼마나 진행됐는지 수치로 본다.

#### 해야 할 일

- audit에 binding progress 추가
- category별 bound/unbound 상태 집계
- key coverage snapshot 추가

#### 권장 지표

- `total_registry_keys`
- `bound_registry_keys`
- `unbound_registry_keys`
- `binding_rate_pct`
- `bound_by_component`

#### 대상 파일

- [learning_apply_connection_audit.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_apply_connection_audit.py)

#### 완료 조건

- “지금 어디까지 묶였는지”를 audit artifact에서 바로 볼 수 있다

## 단계별 완료 순서

권장 순서:

1. `DB0` schema + resolver
2. `DB1` detector direct binding
3. `DB2` state25 weight review direct binding
4. `DB3` feedback/proposal runtime direct binding
5. `DB4` forecast/report direct binding
6. `DB5` audit/progress 확장

## 지금 하지 말아야 할 것

- detector scoring을 registry로 이동
- forecast 계산식을 registry로 이동
- proposal priority 계산식을 registry로 이동
- approval/apply 로직을 registry로 이동
- direct binding과 동시에 자동 apply 범위를 넓히기

## 성공 기준

이 로드맵의 성공은 아래로 판단한다.

1. 같은 항목이 detector/proposal/review/report에서 같은 `registry_key`를 가진다
2. 운영자가 같은 항목을 같은 한국어 label로 읽는다
3. 계산과 실행 로직은 각 레이어에 그대로 남아 있다
4. audit에서 binding progress를 수치로 볼 수 있다

## 현재 판단

지금은 이 작업을 시작하기에 적절한 시점이다.

이유:

- 루프 자체는 이미 연결돼 있다
- 중앙 레지스트리도 이미 생겼다
- 남은 병목은 기능이 아니라 의미 정합성이다

즉 이제부터는

`새 기능 개발`

보다

`같은 개념을 같은 키와 같은 언어로 직접 보게 만드는 정리`

가 더 가치가 큰 단계다.
