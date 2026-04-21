# DB1 Detector Direct Binding 상세 계획
## 목표

`improvement_log_only_detector.py`가 만드는 detector row가 중앙 학습 변수 레지스트리의 직접 바인딩 계약을 실제로 싣도록 만든다.

이번 단계의 목적은 detector 계산 로직을 중앙화하는 것이 아니라,

- detector가 본 증거를 `registry_key` 기준으로 다시 식별하고
- detector가 제안하려는 조절 대상을 `target_registry_keys`로 분리하고
- 이후 feedback / propose / review가 같은 언어를 쓰게 만드는 것

이다.

## 왜 지금 DB1인가

현재 상태는 다음과 같다.

- 중앙 레지스트리와 resolver는 이미 있다
- audit도 루프 연결 자체는 `PASS`다
- 아직 `registry_direct_runtime_binding`만 `WARN`이다

즉 지금 병목은 기능 부족이 아니라 detector가 만든 증거를 proposal/review와 같은 key로 이어붙이지 못하는 점이다.

detector는 direct binding의 생산자이므로 여기부터 묶는 것이 가장 안전하다.

## 이번 단계에서 하는 일

### 1. detector row에 canonical evidence field를 명시적으로 남긴다

scene/candle detector는 이미 박스 위치, 캔들 구조, 최근 3봉 흐름을 설명 문장으로 surface하고 있다.

DB1에서는 이걸 문장으로만 두지 않고 row field로도 남긴다.

대표 필드:

- `position_dominance`
- `structure_alignment`
- `structure_alignment_mode`
- `box_relative_position`
- `box_zone`
- `range_too_narrow`
- `upper_wick_ratio`
- `lower_wick_ratio`
- `doji_ratio`
- `recent_3bar_direction`

이 필드들은 detector scoring을 바꾸기 위한 것이 아니라, registry direct binding과 downstream proposal 연결을 위한 canonical evidence shape다.

### 2. 각 row에 direct binding metadata를 붙인다

각 detector row는 다음 계약을 따른다.

- `registry_key`
- `registry_label_ko`
- `registry_category`
- `registry_component_key`
- `registry_binding_mode`
- `registry_binding_version`
- `evidence_registry_keys`
- `target_registry_keys`
- `evidence_bindings`
- `target_bindings`
- `registry_binding_ready`

### 3. binding mode를 3단계로 나눈다

#### `exact`

- 단일 구조형 evidence가 row를 대표할 때
- 예: 특정 row가 사실상 `misread:box_relative_position` 한 축으로 읽힐 때

#### `derived`

- 여러 구조형 evidence가 함께 row를 구성할 때
- 예: `box + wick + recent_3bar`가 묶인 복합 불일치

#### `fallback`

- reverse row처럼 구조 evidence보다 결과/설명 축이 먼저 보이는 경우
- 아직 완전한 구조형 direct binding이 아닌 최소 연결

### 4. detector row에서 evidence와 target을 분리한다

#### `evidence_registry_keys`

detector가 실제로 관찰한 증거 키.

예:

- `misread:structure_alignment`
- `misread:box_relative_position`
- `misread:upper_wick_ratio`
- `misread:recent_3bar_direction`
- `misread:result_type`

#### `target_registry_keys`

이 detector row가 proposal/review에서 조절 대상으로 삼으려는 키.

초기 DB1에서는 candle/weight detector의 `weight_patch_preview` override를 기준으로만 붙인다.

예:

- `state25_weight:upper_wick_weight`
- `state25_weight:reversal_risk_weight`

즉 이번 단계에서 detector는

- 무엇을 봤는지
- 무엇을 바꾸고 싶어 하는지

를 같은 row 안에서 분리해서 전달한다.

## 적용 범위

### scene-aware detector

- runtime row에서 구조 evidence를 끌어와 direct binding field를 만든다
- 기본적으로 `structure_alignment`, `position_dominance`, `context_flag` 계열을 증거로 삼는다
- `scene trace missing`, `preview changed` 같은 row도 최소 fallback binding은 갖게 한다

### candle/weight detector

- `box/wick/3bar/composite` evidence를 중심으로 direct binding 한다
- `weight_patch_preview`가 있으면 `target_registry_keys`도 같이 싣는다

### reverse detector

- 이번 단계에서는 최소 fallback binding만 한다
- 구조형 direct binding보다 `result_type` 중심의 안전한 연결을 우선한다

## 구현 순서

1. detector에 resolver import 추가
2. runtime evidence를 row field로 남기는 helper 추가
3. detector row -> binding metadata 후처리 helper 추가
4. snapshot pipeline에 direct binding 후처리 연결
5. feedback issue refs에도 binding 요약 노출
6. 테스트 추가

## 테스트 기준

### scene row

- `registry_key`가 비어 있지 않다
- `evidence_registry_keys`에 구조형 misread key가 들어 있다

### candle row

- `target_registry_keys`에 state25 weight key가 들어 있다
- 복합 불일치 row는 `registry_binding_mode = derived`

### reverse row

- `registry_binding_mode = fallback`
- 최소한 `misread:result_type` 수준의 binding은 갖는다

## 완료 조건

- surfaced detector row가 direct binding metadata를 가진다
- detector가 본 evidence와 proposal target이 같은 row에서 분리되어 보인다
- audit에서 detector direct binding 단계로 넘어갈 준비가 끝난다
- 기존 detector summary/why_now/report 문구는 유지된다

## 이번 단계에서 하지 않는 것

- detector scoring 중앙화
- proposal priority 중앙화
- forecast direct binding
- apply executor 중앙화

즉 DB1은 detector를 중앙 두뇌로 묶는 단계가 아니라,
detector가 만든 증거를 중앙 의미 허브와 같은 언어로 연결하는 단계다.
