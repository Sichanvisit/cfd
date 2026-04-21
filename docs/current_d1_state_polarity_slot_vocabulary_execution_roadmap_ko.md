# D1 공용 slot vocabulary 실행 로드맵

## 1. 목적

D1은 decomposition의 계산보다 먼저,
공용 slot vocabulary를 문서와 코드에서 동시에 고정하는 단계다.

---

## 2. 실행 순서

### D1-1. 공용 enum 고정

core:

- `polarity`
- `intent`
- `stage`

modifier:

- `texture`
- `location`
- `ambiguity`
- `tempo(raw/count based)`

### D1-2. core/modifier 규칙 고정

- core slot = `polarity + intent + stage`
- modifier = `texture + location + tempo + ambiguity`
- core slot은 행동 차이를 만들 정도일 때만 승격

### D1-3. control rule 고정

- decomposition은 dominant_side를 바꾸지 못함
- stage와 texture를 분리
- ambiguity는 mode/caution 조정용
- execution interface는 선언만 함

### D1-4. summary artifact 생성

아래 artifact를 생성한다.

- `state_polarity_slot_vocabulary_latest.json`
- `state_polarity_slot_vocabulary_latest.md`

### D1-5. runtime detail export

`runtime_status.detail.json`에 아래를 surface한다.

- `state_polarity_slot_vocabulary_contract_v1`
- `state_polarity_slot_vocabulary_summary_v1`
- `state_polarity_slot_vocabulary_artifact_paths`

### D1-6. unit test 추가

최소 테스트:

- contract가 core/modifier 규칙을 포함
- summary artifact가 정상 생성
- runtime detail에 contract/summary/path가 export됨

---

## 3. 완료 기준

- 공용 slot vocabulary와 통제 규칙이 코드/문서/runtime에 동시에 고정된다.

---

## 4. 상태 기준

- `READY`: vocabulary와 control rule 고정
- `HOLD`: 일부 필드나 설명이 흔들림
- `BLOCKED`: 공용 slot보다 심볼 예외가 먼저 지배함
