# 학습/반영 연결 감사 기준서

## 목적

이 문서는 아래 흐름이 실제로 코드 기준으로 이어져 있는지 확인하기 위한 감사 기준서다.

- detector 관찰
- detector feedback
- feedback-aware proposal promotion
- 수동 proposal
- state25 weight review
- approval bridge
- apply handler

즉 “문서상으로는 이어져 보이는데 실제 코드에서 끊기지 않았는지”를 확인하는 기준면이다.

## 확인하려는 핵심 질문

1. 중앙 학습 변수 레지스트리가 실제로 존재하는가
2. state25 weight 카탈로그가 중앙 레지스트리에 빠짐없이 등록되어 있는가
3. detector가 feedback/proposal/state25 preview/hindsight와 이어져 있는가
4. feedback와 fast promotion이 proposal 우선순위로 이어지는가
5. approval bridge가 proposal envelope와 apply executor를 통해 review/apply로 이어지는가
6. state25 weight review가 실제 active candidate state 반영까지 가는가
7. 중앙 레지스트리가 아직 기준면인지, runtime 직접 참조까지 들어갔는지

## 현재 해석 원칙

이 감사는 두 가지를 구분한다.

### 1. 루프 연결 자체

이 축은 PASS가 나와야 한다.

- detector -> feedback/propose
- proposal -> approval bridge
- approval bridge -> apply executor
- state25 review -> active candidate state 반영

### 2. 중앙 레지스트리의 직접 바인딩

이 축은 PASS가 아니어도 괜찮다.

이유:
- 중앙 레지스트리는 지금 막 만든 기준면이다.
- 아직 모든 runtime 서비스가 직접 import해서 강제 참조하는 단계는 아닐 수 있다.
- 이 경우 WARN으로 보되, “기준면은 생겼고 직접 바인딩은 다음 단계”라고 해석한다.

즉 WARN은 실패가 아니라
`중앙 기준면은 생겼지만 아직 강제 참조점으로 완전히 수렴하진 않았다`
는 뜻이다.

## 관련 코드/산출물

- 감사 코드: [learning_apply_connection_audit.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_apply_connection_audit.py)
- 감사 snapshot json: [learning_apply_connection_audit_latest.json](C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/learning_apply_connection_audit_latest.json)
- 감사 snapshot md: [learning_apply_connection_audit_latest.md](C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/learning_apply_connection_audit_latest.md)

같이 보는 기준:
- [learning_parameter_registry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_parameter_registry.py)
- [current_learning_parameter_registry_master_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_parameter_registry_master_ko.md)
- [current_learning_registry_direct_binding_field_contract_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_field_contract_ko.md)
- [current_learning_registry_direct_binding_execution_roadmap_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_execution_roadmap_ko.md)

## 결과 해석

### PASS

- 연결이 실제로 코드 기준으로 닫혀 있음

### WARN

- 기능은 돌아가지만 기준면 직접 참조까지는 아직 미완
- 예: 중앙 레지스트리가 runtime 서비스에 아직 직접 import되지 않음

### FAIL

- 실제 루프가 끊겨 있음
- proposal, apply, feedback, detector 중 핵심 연결이 누락됨

## 다음 단계

현재 감사에서 WARN으로 남는 항목은

- 중앙 레지스트리 직접 바인딩

이 축일 가능성이 가장 높다.

이 경우 다음 단계는

1. detector/report/proposal builder가 중앙 레지스트리의 `registry_key`를 같이 싣도록 만들고
2. 한국어 label과 description을 중앙 레지스트리에서 먼저 가져오게 하며
3. weight/forecast/misread evidence가 registry 기반으로 수렴하도록 바꾸는 것

이다.

세부 필드 계약과 단계별 순서는 아래 문서를 기준으로 본다.

- [current_learning_registry_direct_binding_field_contract_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_field_contract_ko.md)
- [current_learning_registry_direct_binding_execution_roadmap_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_execution_roadmap_ko.md)

즉 지금 감사의 목적은 “완벽하다”를 선언하는 것이 아니라,
`실제 루프는 연결돼 있고, 중앙 기준면은 이제 강제 참조점으로 키워야 한다`
는 현재 위치를 명확하게 보여주는 것이다.
