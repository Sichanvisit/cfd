# D1 공용 slot vocabulary 상세 계획

## 1. 목적

D1의 목적은 decomposition을 실제 계산하기 전에,
공용 slot 언어를 먼저 고정하는 것이다.

즉 D1은 "어떤 심볼에서 어떤 장면이 나왔다"보다 먼저,
그 장면을 앞으로 어떤 공용 언어로 부를지 정하는 단계다.

---

## 2. 왜 필요한가

지금 상태에서 바로 XAU/NAS/BTC subtype를 늘리면
심볼별 예외 규칙과 이름만 늘어나고,
공용 비교가 어려워질 수 있다.

그래서 D1은 아래를 먼저 고정한다.

- `polarity`
- `intent`
- `stage`
- `texture`
- `location`
- `ambiguity`

그리고 다음 규칙도 함께 고정한다.

- core slot은 `polarity + intent + stage`
- modifier는 `texture + location + tempo + ambiguity`
- core slot은 execution decision이 실제로 달라질 만큼 구조 차이가 있을 때만 승격
- decomposition은 dominant_side를 바꾸지 못함

---

## 3. D1에서 고정할 것

### 3-1. core layers

- `polarity = BULL / BEAR`
- `intent = CONTINUATION / RECOVERY / REJECTION / BREAKDOWN / BOUNDARY`
- `stage = INITIATION / ACCEPTANCE / EXTENSION / NONE`

### 3-2. modifier layers

- `texture = CLEAN / WITH_FRICTION / DRIFT / EXHAUSTING / FAILED_RECLAIM / POST_DIP / NONE`
- `location = IN_BOX / AT_EDGE / POST_BREAKOUT / EXTENDED / NONE`
- `ambiguity = LOW / MEDIUM / HIGH`
- `tempo = raw persistence/count based`

### 3-3. field catalog

- `polarity_slot_v1`
- `intent_slot_v1`
- `stage_slot_v1`
- `texture_slot_v1`
- `location_context_v1`
- `tempo_profile_v1`
- `ambiguity_level_v1`
- `state_slot_core_v1`
- `state_slot_modifier_bundle_v1`
- `state_slot_reason_summary_v1`

---

## 4. 통제 규칙

- core slot은 장면 이름이 아니라 행동 차이를 만들 정도의 구조 차이일 때만 승격
- stage는 언제, texture는 어떻게
- ambiguity는 side를 바꾸지 않고 boundary/caution만 조정
- rejection 분리는 reversal과 friction으로 반드시 나눔
- execution interface는 선언만 하고, 적용은 뒤로 미룸

---

## 5. 산출물

runtime/detail에서 아래를 볼 수 있어야 한다.

- `state_polarity_slot_vocabulary_contract_v1`
- `state_polarity_slot_vocabulary_summary_v1`
- `state_polarity_slot_vocabulary_artifact_paths`

shadow artifact:

- `state_polarity_slot_vocabulary_latest.json`
- `state_polarity_slot_vocabulary_latest.md`

---

## 6. 완료 기준

- 공용 slot vocabulary가 코드와 문서에 동시에 고정된다.
- runtime detail에서 같은 contract와 summary를 읽을 수 있다.

---

## 7. 상태 기준

- `READY`: core/modifier vocabulary와 통제 규칙이 고정됨
- `HOLD`: vocabulary는 있으나 field catalog나 rule 설명이 흔들림
- `BLOCKED`: 심볼별 예외가 공용 slot을 압도해 공용 vocabulary가 성립하지 않음
