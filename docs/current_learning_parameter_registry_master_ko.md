# 학습/제안 변수 중앙 레지스트리 기준서

## 목적

지금 시스템은 이미

- runtime 설명 surface
- detector evidence
- detector feedback
- `/propose`
- state25 weight patch review
- forecast/belief/barrier 보조 판단

까지 이어진 상태다.

이 단계에서 가장 중요한 것은

- 학습에 쓰이는 변수
- 제안에 쓰이는 변수
- 운영자가 읽는 한국어 라벨

이 서로 다른 이름으로 흩어지지 않게 만드는 것이다.

즉 이 문서와 레지스트리의 목적은

1. 조절 가능한 항목과 관찰 항목을 한 군데에서 본다.
2. raw key 대신 운영자가 이해할 수 있는 한국어 기준면을 유지한다.
3. detector / feedback / proposal / review가 같은 언어를 쓰게 만든다.

## 중앙 기준 파일

- 코드 기준: [learning_parameter_registry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_parameter_registry.py)
- snapshot json: [learning_parameter_registry_latest.json](C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/learning_parameter_registry_latest.json)
- snapshot markdown: [learning_parameter_registry_latest.md](C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/learning_parameter_registry_latest.md)
- direct binding 필드 계약: [current_learning_registry_direct_binding_field_contract_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_field_contract_ko.md)
- direct binding 실행 로드맵: [current_learning_registry_direct_binding_execution_roadmap_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_execution_roadmap_ko.md)

## 왜 지금 이게 필요한가

지금은 학습과 제안이 아래처럼 여러 축에서 동시에 일어난다.

- state25 teacher weight proposal
- forecast 기반 wait/confirm/hold/fast-cut 보조 판단
- 구조형 오판 detector
- detector feedback promotion
- hindsight validator

문제는 이 축들이 각자 다른 파일 안에서

- raw key
- 임시 label
- 영어 field name
- 한국어 설명 문장

으로 흩어지기 쉽다는 점이다.

이 상태가 길어지면

- 같은 항목을 서로 다른 이름으로 부르게 되고
- proposal 보고서와 detector evidence가 어긋나고
- 운영자가 “이게 정확히 어떤 변수를 말하는지” 추적하기 어려워진다.

그래서 이제부터는 새 변수나 새 proposal surface가 생길 때
먼저 이 중앙 레지스트리에 넣고,
그다음 feature-specific file에서 쓰는 흐름으로 가는 것이 기준이다.

## 카테고리 구성

중앙 레지스트리는 아래 6개 카테고리로 나눈다.

### 1. 한국어 번역 기준면

목적:
- 한국어 label의 source of truth

포함:
- runtime reason 한글 맵
- runtime scene 한글 맵
- runtime transition 한글 맵
- state25 teacher weight 한글 카탈로그

원칙:
- user-facing 문자열은 가능한 한 이 기준면을 우선 사용한다.
- 새 runtime reason / scene / transition / weight key가 생기면 여기부터 보강한다.

### 2. state25 teacher 가중치

목적:
- 실제 조절 가능한 weight patch 대상 정리

대표 항목:
- 캔들 몸통 비중
- 윗꼬리 반응 비중
- 아랫꼬리 반응 비중
- 도지 민감도
- 연속 캔들 비중
- 압축 구간 비중
- 거래량 급증/감쇠 비중
- 방향 우세 비중
- 대기 상태 비중
- 반전 위험 비중
- 갭 문맥 비중
- 박스 반전 비중

원칙:
- weight proposal은 raw key만 보내지 않는다.
- 반드시 `label_ko`, `description_ko`를 같이 surface한다.

### 3. forecast 보조 판단 축

목적:
- forecast가 어떤 branch bias를 통해 runtime을 보조하는지 정리

대표 항목:
- 확정 우세 방향
- 확정 우세 점수
- 가짜 돌파 경계 점수
- 지속 성공 점수
- 보유 선호 점수
- 즉시 실패 경계 점수
- 대기-확정 간극
- 보유-청산 간극
- 동일방향-반전 간극
- 빌리프-베리어 긴장 간극
- forecast 결정 힌트
- 지금 진입 선호 / 지금 대기 선호 / 진입 후 보유 선호 / 진입 후 빠른 청산 선호

원칙:
- forecast는 메인 방향 결정권이 아니라 보조 판단 축으로 유지한다.
- proposal과 detector 설명에서 forecast 항목을 근거로 쓸 때도 raw field 대신 한국어 label을 먼저 쓴다.

### 4. 구조형 오판 관찰 증거

목적:
- 사람이 차트에서 보는 좌표계를 detector evidence로 통일

대표 항목:
- 위치 우세 방향
- 구조 정합 상태
- 문맥 플래그
- 문맥 신뢰도
- 박스 상대 위치
- 박스 영역
- 좁은 박스 예외
- 윗꼬리 비율
- 아랫꼬리 비율
- 도지 비율
- 최근 3봉 흐름
- 결과 축
- 설명 축
- 오판 신뢰도
- 설명 스냅샷
- detector cooldown 분
- 구조 복합 불일치

원칙:
- `P4-6` detector evidence는 가능한 한 같은 canonical shape를 공유한다.
- same scope 반복 surface는 cooldown으로 억제한다.
- box/wick/3bar가 같이 어긋날 때는 복합 불일치 한 건으로 묶는다.

### 5. detector 운영 정책

목적:
- detector를 유용한 관찰기로 유지하고 양치기 소년이 되지 않게 함

대표 항목:
- detector별 일 surface 한도
- detector별 최소 반복 표본

원칙:
- detector는 observe/report 우선이다.
- 자동 apply를 열지 않는다.
- detector가 많이 뜬다고 좋은 것이 아니라, feedback 가능한 issue만 남기는 것이 목표다.

### 6. feedback 승격 정책

목적:
- feedback과 hindsight를 proposal 우선순위로 연결

대표 항목:
- 빠른 승격 최소 피드백 수
- 빠른 승격 최소 긍정 비율
- 빠른 승격 최소 거래일 분산
- 빠른 승격 최소 오판 신뢰도
- 사후 hindsight 상태

원칙:
- fast promotion은 proposal 우선 검토까지만 허용한다.
- 자동 apply, 자동 전략 변경, wide rollout은 금지다.

## 새 변수 추가 규칙

새로 생기는 변수나 조절 항목은 아래 순서로 추가한다.

1. 중앙 레지스트리에 row를 추가한다.
2. 한국어 label/description을 먼저 정의한다.
3. source file / source field / 역할을 적는다.
4. detector evidence인지, weight patch 대상인지, forecast 보조축인지 분류한다.
5. 그다음 feature-specific file에서 실제 surface/제안/feedback에 연결한다.

## proposal과 detector에서의 사용 규칙

- raw key만 단독으로 사용자에게 노출하지 않는다.
- 가능하면 `label_ko + description_ko + 왜 지금(surface reason)` 조합으로 보낸다.
- 같은 항목을 proposal/detect/report에서 다른 이름으로 부르지 않는다.
- detector evidence와 proposal summary는 같은 registry_key를 기준으로 묶는 방향을 우선한다.

## 운영자 관점의 기대 효과

이 레지스트리가 있으면 운영자는

- “이 detector가 정확히 어떤 변수를 말하는지”
- “이 proposal이 어떤 weight 또는 어떤 evidence 축을 건드리는지”
- “forecast/belief/barrier가 어디까지는 설명축이고 어디서부터 조절축인지”

를 한 번에 추적할 수 있다.

즉 이 문서는 단순 용어집이 아니라,
학습과 제안을 운영자가 이해 가능한 언어로 고정하는 기준면이다.

## 다음 원칙

이제부터는 새 학습 변수, 새 detector evidence, 새 proposal knob가 생기면
먼저 [learning_parameter_registry.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/learning_parameter_registry.py)에 넣고,
그 다음 실제 구현으로 연결하는 흐름을 기본으로 한다.

그리고 중앙 기준면을 실제 runtime 서비스의 직접 참조점으로 수렴시키는 다음 단계는

- [current_learning_registry_direct_binding_field_contract_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_field_contract_ko.md)
- [current_learning_registry_direct_binding_execution_roadmap_ko.md](C:/Users/bhs33/Desktop/project/cfd/docs/current_learning_registry_direct_binding_execution_roadmap_ko.md)

를 기준으로 진행한다.
