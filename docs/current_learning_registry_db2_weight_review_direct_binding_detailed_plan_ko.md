# DB2 State25 Weight Review Direct Binding 상세 계획
## 목표

`state25_weight_patch_review.py`가 만드는 weight review 후보가 중앙 학습 변수 레지스트리의 `state25_weight:*` key를 직접 싣도록 만든다.

이번 단계의 핵심은 두 가지다.

- weight review 문구가 중앙 registry의 한국어 label/description을 우선 사용하게 만들기
- review candidate가 `target_registry_keys`를 직접 가져서 detector / feedback / proposal과 같은 target 언어를 쓰게 만들기

## 왜 DB2가 지금 순서인가

DB1에서 detector row는 이미 direct binding metadata를 갖게 됐다.

즉 이제 detector는

- 무엇을 봤는지: `evidence_registry_keys`
- 무엇을 바꾸려는지: `target_registry_keys`

를 한 row 안에서 분리해서 전달할 수 있다.

DB2는 그 다음 단계로, weight review candidate가 이 `target_registry_keys`를 자기 payload와 report line에 실제로 유지하도록 만드는 단계다.

## 이번 단계에서 하는 일

### 1. weight override를 registry key로 변환한다

기존:

- `upper_wick_weight`
- `compression_weight`

DB2 이후:

- `state25_weight:upper_wick_weight`
- `state25_weight:compression_weight`

즉 review candidate는 raw `weight_key`만이 아니라 중앙 registry 기준 key를 직접 가진다.

### 2. binding mode를 review 대상 수에 따라 분기한다

#### `exact`

- 조절 대상 weight가 1개일 때

#### `derived`

- 조절 대상 weight가 2개 이상일 때

#### `fallback`

- override가 비어 있어 직접 target key를 만들 수 없을 때

### 3. report line은 registry label/description을 우선 읽는다

기존 report line은 teacher catalog의 label/description으로도 충분히 읽혔지만,
DB2 이후부터는 중앙 registry row를 우선 참조한다.

즉 같은 `state25_weight:*` 항목은

- detector preview
- weight review
- proposal 요약

에서 같은 한국어명으로 보이게 된다.

### 4. review candidate에 direct binding metadata를 붙인다

추가 필드:

- `registry_key`
- `registry_label_ko`
- `registry_category`
- `registry_component_key`
- `registry_binding_mode`
- `registry_binding_version`
- `registry_binding_ready`
- `evidence_registry_keys`
- `target_registry_keys`
- `evidence_bindings`
- `target_bindings`

### 5. detector에서 올라온 evidence key도 같이 받을 수 있게 연다

이번 단계에서는 `evidence_registry_keys`를 optional 입력으로 받는다.

즉 detector가 이미 본 증거 key를 weight review candidate에 같이 실어,

- 무엇을 보고
- 무엇을 조절하려는지

를 같은 review payload 안에서 유지할 수 있게 한다.

## 구현 범위

대상 파일:

- [state25_weight_patch_review.py](C:/Users/bhs33/Desktop/project/cfd/backend/services/state25_weight_patch_review.py)

주요 변경:

- resolver import
- override -> target registry key helper
- registry 기반 report line helper
- candidate builder에 direct binding metadata 추가

## 테스트 기준

### 단일 weight review

- `registry_key = state25_weight:<key>`
- `registry_binding_mode = exact`
- `target_registry_keys` 길이 1

### 복수 weight review

- `registry_binding_mode = derived`
- `target_registry_keys`에 복수 key가 들어감
- `target_bindings`가 registry row를 실제로 resolve함

### evidence 연동

- `evidence_registry_keys`를 넣으면 candidate payload에 그대로 유지됨

## 완료 조건

- weight review candidate가 중앙 registry 기준 key와 label을 직접 가진다
- report line이 중앙 registry label/description을 우선 사용한다
- audit에서 `weight_review_direct_binding = true`가 된다
- binding progress가 detector 단계보다 더 올라간다

## 이번 단계에서 하지 않는 것

- state25 apply 로직 중앙화
- weight merge/executor 변경
- detector scoring/priority 계산 변경

즉 DB2는 review 표현과 target 계약을 중앙화하는 단계이지,
실제 apply 행동을 중앙화하는 단계가 아니다.
