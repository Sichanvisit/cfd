# 중앙 학습 변수 레지스트리 직접 바인딩 필드 계약서

## 목적

이 문서는 중앙 학습 변수 레지스트리와 runtime/detector/proposal/report 레이어가
직접 바인딩될 때 어떤 필드를 공통 계약으로 삼을지 정의한다.

이번 단계의 핵심은 계산과 실행을 중앙화하는 것이 아니라,

- 같은 개념은 같은 `registry_key`
- 같은 항목은 같은 `label_ko`
- 같은 의미권은 같은 `category`

로 읽히게 만드는 것이다.

즉 이 문서는 “행동 규칙”이 아니라 “의미 계약” 문서다.

## 기본 원칙

### 1. 계산과 실행은 각 레이어에 남긴다

중앙 레지스트리로 올리지 않는 것:

- detector scoring
- forecast branch 계산
- proposal priority score 계산
- approval/apply 절차
- patch merge 로직

중앙 레지스트리로 올리는 것:

- 식별자
- 한국어 표시명
- 설명
- 카테고리
- source mapping
- 역할 메타데이터

### 2. 강제 / 권장 / 자유를 구분한다

#### 강제 바인딩

- `registry_key`
- `label_ko`
- `category`
- `component_key`

이 4개는 같은 항목이면 어디서든 같아야 한다.

#### 권장 바인딩

- `description_ko`
- `runtime_role_ko`
- `proposal_role_ko`
- `canonical_value_type`
- `boundary_note`

이 항목은 레지스트리에 기본값을 두고,
특정 서비스가 문맥에 맞게 짧게 변형할 수 있다.

#### 자유 영역

- detector summary 문장
- proposal priority 설명
- report 문장 스타일
- DM 전체 메시지 문장 구성

즉 핵심 식별은 통일하되, 문장 실험은 계속 허용한다.

## 공통 계약 필드

### A. 필수 필드

#### `registry_key`

- 역할: 항목의 유일 식별자
- 예:
  - `state25_weight:upper_wick_weight`
  - `misread:box_relative_position`
  - `forecast:false_break_score`

#### `label_ko`

- 역할: 운영자가 보는 공식 한국어 이름
- 예:
  - `윗꼬리 반응 비중`
  - `박스 상대 위치`
  - `가짜 돌파 경계 점수`

#### `category`

- 역할: 같은 의미권끼리 묶는 분류 키
- 예:
  - `translation_source`
  - `state25_teacher_weight`
  - `forecast_runtime`
  - `misread_observation`
  - `detector_policy`
  - `feedback_promotion_policy`

#### `component_key`

- 역할: 소속 컴포넌트
- 예:
  - `state25_teacher_weight`
  - `structure_aware_misread_detector`
  - `forecast_runtime_summary`
  - `trade_feedback_runtime`

### B. 권장 필드

#### `description_ko`

- 역할: 기본 설명 문장
- 사용 원칙:
  - detector/report/proposal이 기본적으로 참고
  - 필요하면 서비스별 summary는 더 자연스럽게 변형 가능

#### `runtime_role_ko`

- 역할: 런타임에서 이 항목이 어떤 역할인지

#### `proposal_role_ko`

- 역할: 제안과 review에서 이 항목이 어떤 역할인지

#### `source_file`

- 역할: 원본 계산/정의가 있는 파일

#### `source_field`

- 역할: 원본 field 또는 mapping 지점

### C. 선택 필드

#### `canonical_value_type`

- 예:
  - `float`
  - `bool`
  - `enum`
  - `mapping`
  - `string`

#### `value_range`

- 예:
  - `[0.0, 1.0]`
  - `[-1.0, 1.0]`
  - `null 가능`

#### `boundary_note`

- 예:
  - `0.0=하단, 1.0=상단`
  - `range_too_narrow면 null 가능`

#### `binding_version`

- 역할: direct binding 기준 버전

#### `is_experimental`

- 역할: 실험 단계 항목 표시

## 바인딩 대상 row/envelope 필드

직접 바인딩이 시작되면 detector row, proposal payload, report item은 가능하면 아래 필드를 같이 싣는다.

### 공통 출력 필드

- `registry_key`
- `registry_label_ko`
- `registry_category`
- `registry_component_key`
- `registry_binding_mode`
- `registry_binding_version`

### 증거 묶음이 필요한 경우

단일 항목이 아니라 여러 증거가 함께 작동할 때는 아래 2축을 분리한다.

#### `evidence_registry_keys`

- detector가 실제로 참고한 근거 항목 목록
- 예:
  - `misread:box_relative_position`
  - `misread:upper_wick_ratio`
  - `misread:recent_3bar_direction`

#### `target_registry_keys`

- proposal이나 review가 실제로 조절 대상으로 보는 항목 목록
- 예:
  - `state25_weight:upper_wick_weight`
  - `state25_weight:reversal_risk_weight`

이 분리를 통해

- “무엇을 보고”
- “무엇을 바꾸려는지”

를 섞지 않고 유지한다.

## binding_mode 정의

### `exact`

- 레지스트리 row 하나와 1:1로 직접 연결

### `derived`

- 레지스트리의 여러 항목을 조합해 만든 summary

### `fallback`

- 아직 완전 direct binding은 아니고,
- 기존 로컬 문구를 유지하되 registry label을 우선 참고

## 서비스별 적용 원칙

### detector

- 우선 `registry_key`와 `evidence_registry_keys`를 먼저 싣는다
- summary 문장은 자유 영역으로 둔다

### weight review

- `target_registry_keys`를 먼저 싣는다
- 표시명은 중앙 레지스트리 `label_ko`를 우선 사용한다

### proposal runtime

- detector에서 올라온 `registry_key`와 `target_registry_keys`를 읽어
  proposal summary/priority를 구성한다

### forecast/report

- 가장 늦게 direct binding한다
- 이유:
  - forecast는 보조 판단 축이고 아직 문장 실험성이 높음
  - 먼저 detector/proposal의 개념 언어가 정리돼야 함

## 적용 금지

아래는 direct binding 단계에서도 하지 않는다.

- detector 계산식을 레지스트리로 이동
- forecast 계산식을 레지스트리로 이동
- proposal 점수 계산식을 레지스트리로 이동
- approval/apply 실행 로직을 레지스트리로 이동

즉 registry는 끝까지 **의미 허브**로 유지하고,
실행 허브가 되지 않게 한다.
