# 외부 조언 요청서: 중앙 학습 변수 레지스트리 직접 바인딩 단계

## 1. 이 문서를 만든 이유

현재 자동매매 시스템은 단순 실행 엔진을 넘어서 아래 루프까지 이미 갖춘 상태다.

- 자동 진입 / 대기 / 청산 / 반전 런타임
- checkpoint -> review -> canary -> closeout -> handoff 승격축
- Telegram check / report / PnL / runtime DM control plane
- `/detect -> /detect_feedback -> /propose` 학습 루프
- state25 weight patch review / approval / apply 통로
- forecast / belief / barrier 보조 판단 축
- 구조형 오판 detector (`P4-6`)까지 포함한 설명/학습 surface

즉 지금 단계의 핵심 문제는 “구조 부재”가 아니라,
**학습과 제안에 쓰이는 변수/근거/설명 언어가 여러 파일과 레이어에 분산되어 있다는 점**이다.

사용자 입장에서는 이미 다음과 같은 것이 동시에 보인다.

- detector evidence
- state25 weight 조정 제안
- forecast decision hint
- scene / transition / reason 한국어 설명
- feedback-aware promotion
- proposal envelope

그런데 같은 의미의 항목이

- raw key
- detector 내부 field
- 한국어 문구
- proposal summary
- weight patch label

로 흩어져 있기 때문에,
운영자가 “이게 정확히 어떤 변수이고 어디까지 연결되는지”를 한 번에 추적하기 어렵다.

그래서 이번 단계는

1. 이미 있는 한국어 기준면과 학습 변수를 중앙 레지스트리로 모으고
2. 그 레지스트리를 실제 detector / proposal / review 문구가 직접 참조하도록 좁게 수렴시키는 것

을 목표로 잡았다.

## 2. 현재 시스템에 대해 중요한 전제

이번 작업은 “기존 시스템이 고장났다”는 전제에서 출발한 것이 아니다.

오히려 현재 판단은 아래에 가깝다.

- 실행/관찰/제안/승격 루프는 이미 대부분 살아 있음
- detector feedback과 proposal promotion도 실제로 연결돼 있음
- state25 weight review는 active candidate state 반영까지 이어짐
- 문제는 **같은 의미의 항목이 아직 중앙 기준면을 직접 참조하지 않는다는 점**

즉 질문은 “학습 루프가 없느냐”가 아니라,
**“이미 있는 루프가 같은 언어와 같은 registry_key를 직접 보게 만들어야 하느냐, 그리고 그 순서를 어떻게 잡는 게 맞느냐”**이다.

## 3. 현재까지 이미 구축된 것

### 3-1. 한국어 기준면

현재 이미 존재하는 한국어 기준면:

- [reason_label_map.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\reason_label_map.py)
  - runtime reason / scene / transition 한국어 맵
- [teacher_pattern_active_candidate_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_active_candidate_runtime.py)
  - state25 teacher weight label_ko / description_ko 카탈로그

즉 한국어 번역 기준은 완전히 없는 상태가 아니라,
이미 여러 곳에 상당 부분 쌓여 있었다.

### 3-2. 중앙 학습 변수 레지스트리

이번에 새로 추가한 중앙 기준 파일:

- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)
- [current_learning_parameter_registry_master_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_learning_parameter_registry_master_ko.md)

이 레지스트리는 현재 아래 카테고리를 한 군데로 모은다.

- 한국어 번역 기준면
- state25 teacher 가중치
- forecast 보조 판단 축
- 구조형 오판 관찰 증거
- detector 운영 정책
- feedback 승격 정책

최신 snapshot:

- [learning_parameter_registry_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\learning_parameter_registry_latest.json)
- [learning_parameter_registry_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\learning_parameter_registry_latest.md)

현재 row 수:

- `64개`

### 3-3. 학습/제안/반영 연결 감사

이번에 실제 연결 여부를 audit로 점검했다.

- [learning_apply_connection_audit.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_apply_connection_audit.py)
- [current_learning_apply_connection_audit_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_learning_apply_connection_audit_ko.md)
- [learning_apply_connection_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\learning_apply_connection_audit_latest.json)

현재 audit 결과는 아래다.

- `registry_snapshot_present = PASS`
- `state25_weight_registry_coverage = PASS`
- `detector_to_propose_connection = PASS`
- `feedback_promotion_connection = PASS`
- `review_bridge_connection = PASS`
- `state25_apply_connection = PASS`
- `registry_direct_runtime_binding = WARN`

즉 핵심 해석은 이렇다.

- 학습 / 제안 / review / apply 루프 자체는 이미 연결돼 있다
- 하지만 중앙 레지스트리가 아직 runtime 서비스들의 직접 참조점으로 강제 수렴된 것은 아니다

## 4. 왜 이제 “직접 바인딩”을 건드리려 하는가

이 작업을 하려는 이유는 단순 미관 정리가 아니다.

### 4-1. 운영자가 같은 항목을 한 번에 추적하기 어렵다

예를 들어 현재 동일한 의미권이 아래처럼 분산될 수 있다.

- detector evidence line
- `/propose` summary
- state25 weight patch review line
- forecast explain line
- runtime DM 설명

모두 관련은 있는데,
raw key와 한국어 label의 기준점이 한 군데로 직접 연결되어 있지 않다.

### 4-2. proposal과 detector가 같은 언어를 쓰는지 보장하기 어렵다

지금은 이미 한국어로 잘 surface되지만,
새 변수가 추가될 때마다

- detector는 한 표현
- report는 다른 표현
- proposal은 또 다른 표현

이 될 수 있다.

즉 지금 필요한 것은 새 detector가 아니라
**같은 의미를 같은 registry_key와 같은 label_ko로 직접 보게 만드는 작업**이다.

### 4-3. 앞으로 학습 가능한 변수는 더 늘어난다

사용자 관점에서도 이미 다음이 중요해졌다.

- scene / transition / reason
- box / wick / 3bar 구조형 evidence
- state25 teacher weight
- forecast decision hint / false_break / continuation
- feedback narrowing / fast promotion 기준

이제 이 축들은 계속 늘어날 가능성이 높다.
지금 직접 바인딩 기준을 세워두지 않으면, 나중에 더 정리하기 어려워진다.

## 5. 왜 “전체 통합”이 아니라 “단계적 직접 바인딩”인가

여기서 중요한 판단이 하나 있다.

이번 작업은 **전체 계산 로직을 한 파일로 몰아넣는 작업이 아니다.**

권장 구조는 아래와 같다.

### 중앙화해야 하는 것

- `registry_key`
- `label_ko`
- `description_ko`
- source field
- runtime/proposal 역할 설명

### 각 레이어에 남겨야 하는 것

- detector 계산 로직
- forecast branch 계산
- proposal 우선순위 계산
- apply executor / approval 절차
- state25 patch merge 방식

즉 목표는

`계산과 실행을 중앙화`

가 아니라,

`의미와 표현을 중앙화`

이다.

이 구분을 유지하지 않으면,
중앙 레지스트리가 너무 많은 로직을 끌어안아 오히려 결합도가 높아질 위험이 있다.

## 6. 현재 생각하는 다음 바인딩 순서

현재 가장 안전하다고 보는 순서는 아래와 같다.

### 1단계. [state25_weight_patch_review.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_review.py)

목표:
- weight proposal 문구를 중앙 레지스트리 기준으로 읽기

이유:
- 이미 `label_ko`, `description_ko` 카탈로그가 존재하고
- bounded review/apply 루프가 안정적이며
- 사용자에게 보이는 proposal 문구 통일 효과가 큼

### 2단계. [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

목표:
- detector evidence의 label/description을 `registry_key` 기준으로 수렴

이유:
- detector는 지금 가장 많은 evidence를 surface하는 layer라서
- 여기서 registry_key 기반 근거가 잡히면
- feedback / hindsight / promotion까지 같은 언어를 쓰기 쉬워진다

### 3단계. [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)

목표:
- proposal summary / priority 문구를 중앙 기준으로 수렴

이유:
- detector 쪽 언어가 정리된 뒤 proposal까지 맞춰야
- “detect에서 보던 항목”과 “propose에서 검토하는 항목”이 같은 것으로 읽힌다

### 4단계. forecast / report 쪽

대상 예시:

- [forecast_state25_runtime_bridge.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\forecast_state25_runtime_bridge.py)
- report renderer 계열

목표:
- forecast 보조 판단 축을 중앙 레지스트리 기준으로 읽게 하고
- report 문구도 같은 label 체계로 맞춘다

이유:
- forecast는 지금도 보조 판단 축으로 많이 쓰이고 있지만
- 먼저 detector/proposal 쪽을 묶고 나서 들어가는 편이 더 안전하다

## 7. 현재 연결 상태에 대한 해석

현재 audit 결과를 기준으로 한 해석은 아래와 같다.

### 이미 연결된 것

- detector -> feedback/propose
- feedback confusion / narrowing / promotion
- proposal envelope
- approval bridge
- apply executor
- state25 weight patch review -> active candidate state 반영

즉 “학습하고 제안하고 review/apply까지 가는 큰 루프”는 이미 살아 있다.

### 아직 직접 수렴하지 않은 것

- 중앙 레지스트리를 detector/proposal/report가 직접 import해 공통 label source로 쓰는 단계

즉 지금 남은 작업은 구조를 새로 만드는 것이 아니라,
**이미 있는 루프가 같은 언어와 같은 registry_key를 직접 보게 만드는 정제 작업**이다.

## 8. 이번 단계에서 의도적으로 하지 않으려는 것

아래는 이번 직접 바인딩 단계에서도 여전히 하지 않으려 한다.

- detector 계산 로직 전체를 중앙 레지스트리로 이동
- forecast 수식/점수 계산을 중앙 파일로 통합
- apply executor 로직 중앙화
- detector 결과의 자동 apply
- weight/forecast/scene의 wide automatic rollout

즉 이번 단계도 끝까지

- 표현 / 의미 / registry_key / label 정리

에 머무르며,
실행 권한을 넓히는 단계는 아니다.

## 9. 외부에 묻고 싶은 핵심 질문

### 질문 1

지금처럼

- 학습 / proposal / review / apply 루프는 이미 연결돼 있고
- 중앙 레지스트리는 막 만들어졌으며
- 다음 단계로 direct binding을 하려는 상태

에서,
위 1 -> 2 -> 3 -> 4 순서가 안전하고 적절한가?

### 질문 2

직접 바인딩의 범위를

- label / description / registry_key / source field

까지만 중앙화하고,

- 계산 로직 / 점수 계산 / apply 절차

는 각 레이어에 남기는 것이 맞는가?

### 질문 3

`state25_weight_patch_review -> detector evidence -> trade_feedback proposal -> forecast/report`

이 순서 외에 더 나은 수렴 순서가 있는가?

### 질문 4

direct binding을 시작할 때,
현재처럼 audit가 `WARN`인 상태에서 바로 들어가도 되는가?
아니면 먼저 registry 기반 field를 proposal envelope나 detector row에 더 명시적으로 싣는 intermediate step이 필요한가?

### 질문 5

중앙 레지스트리가 단순 용어집을 넘어서 실제 source of truth로 기능하려면,
어떤 필드를 최소 공통 계약으로 강제하는 것이 좋은가?

예:

- `registry_key`
- `label_ko`
- `description_ko`
- `component_key`
- `source_file`
- `source_field`
- `runtime_role_ko`
- `proposal_role_ko`

이 정도가 충분한가?

### 질문 6

direct binding을 너무 빨리 강하게 하면
오히려 detector/proposal/report 문구 실험성이 떨어질 수 있는데,
이 균형을 어떻게 잡는 게 좋을까?

## 10. 외부 검토자에게 붙여넣을 요청문

```text
현재 자동매매 시스템은 이미

- detector -> feedback -> propose
- proposal -> approval bridge
- approval -> apply executor
- state25 weight patch review -> active candidate state 반영

까지는 연결된 상태입니다.

최근에는 학습/제안에 쓰이는 변수와 한국어 설명 기준을 한 군데로 모으기 위해
중앙 학습 변수 레지스트리를 추가했습니다.

관련 파일:
- learning_parameter_registry.py
- current_learning_parameter_registry_master_ko.md
- learning_apply_connection_audit_latest.json

현재 audit 결과는
- 학습/제안/반영 루프 자체는 PASS
- 중앙 레지스트리의 runtime 직접 바인딩은 WARN

입니다.

즉 문제는 루프 부재가 아니라,
같은 의미의 항목이 detector / proposal / report / weight proposal에서
아직 중앙 registry_key와 한국어 label을 직접 참조하도록 수렴되지 않았다는 점입니다.

현재 생각하는 다음 직접 바인딩 순서는 아래와 같습니다.

1. state25_weight_patch_review.py
   - weight proposal 문구를 중앙 레지스트리 기준으로 읽기
2. improvement_log_only_detector.py
   - detector evidence의 label/description을 registry_key 기준으로 수렴
3. trade_feedback_runtime.py
   - proposal summary/priority 문구를 중앙 기준으로 수렴
4. forecast/report 쪽

중요한 전제는,
이번 단계의 목적은 계산 로직이나 apply 로직을 중앙화하는 것이 아니라
label / description / registry_key / source field / 역할 설명을 중앙 기준으로 묶는 것입니다.

즉 “계산과 실행은 각 레이어에 남기고,
의미와 표현만 중앙화”하려는 시도입니다.

이 방향과 순서가 적절한지,
그리고 direct binding을 어디까지/어떤 속도로 넣는 것이 좋은지 조언을 받고 싶습니다.
```

## 11. 현재 내 판단

현 시점의 판단은 아래와 같다.

- 중앙 레지스트리 추가는 적절했다
- 전체 루프는 이미 충분히 연결돼 있다
- 지금 필요한 것은 새 루프가 아니라 “같은 변수/같은 의미를 같은 언어로 직접 보게 만드는 정제”
- 전체 통합은 위험하고, 단계적 직접 바인딩이 맞다

즉 이번 질문의 핵심은

`이 binding 시도가 적절한가`

보다 더 구체적으로,

`무엇을 중앙화하고 무엇은 각 레이어에 남겨야 하는가`

그리고

`어떤 순서로 수렴시키는 것이 운영 리스크가 가장 낮은가`

이다.
