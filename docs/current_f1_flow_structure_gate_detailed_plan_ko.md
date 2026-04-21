# F1. `flow_structure_gate_v1` 상세 계획

## 1. 목적

F1의 목적은 `aggregate_conviction`과 `flow_persistence`를 보기 전에,

> 이 장면이 directional flow 후보가 될 자격이 있는가

를 구조만으로 먼저 판정하는 공용 gate를 만드는 것이다.

즉 F1은 threshold 단계가 아니라 **후보 자격 단계**다.

## 2. 왜 F1이 먼저 필요한가

현재 시스템은 이미 아래 층을 갖고 있다.

- dominance
- local structure
- decomposition slot
- symbol calibration
- common slot extension
- lifecycle/canary 진단

하지만 `aggregate directional flow`로 넘어가려면, 숫자를 해석하기 전에 먼저

- polarity가 맞는지
- reversal rejection인지
- override veto인지
- ambiguity가 너무 높은지
- stage/tempo/hold/structure support가 최소 자격을 주는지

를 공용 언어로 잘라야 한다.

이걸 하지 않으면:

- 숫자가 구조보다 위로 올라가고
- threshold tuning 지옥으로 돌아가고
- decomposition이 쌓아둔 설명력이 gate에서 사라진다.

## 3. F1의 권한

F1은 아래까지만 한다.

1. directional flow 후보 자격 부여
2. `ELIGIBLE / WEAK / INELIGIBLE` 분류
3. hard disqualifier와 soft qualifier를 분리 surface

F1은 아래를 하지 않는다.

- flow 확정
- threshold band 적용
- exact match bonus 적용
- execution/state25 변경

즉 F1은 `Structure Gate` 그 자체다.

## 4. Hard Disqualifier

F1에서 즉시 탈락시키는 조건은 아래다.

### 4-1. `UNMAPPED_SLOT`

- 공용 slot core가 비어 있음
- polarity가 없음

이 경우는 directional flow 후보로 읽을 구조 자체가 아직 없다.

### 4-2. `POLARITY_MISMATCH`

- slot polarity와 dominant side가 충돌

예:

- slot은 `BULL`
- dominance는 `BEAR`

이 경우는 flow 후보가 아니다.

### 4-3. `REVERSAL_REJECTION`

- rejection이 friction이 아니라 reversal rejection으로 분류됨

이 경우는 continuation/recovery flow 후보 자격을 즉시 잃는다.

### 4-4. `REVERSAL_OVERRIDE`

- consumer veto가 `REVERSAL_OVERRIDE`

이 경우도 구조상 directional flow 후보 자격이 없다.

### 4-5. `AMBIGUITY_HIGH`

- ambiguity가 `HIGH`

이 경우는 구조가 충분히 directional하지 않다.

## 5. Soft Qualifier

Hard disqualifier가 없으면 그다음은 자격의 강도를 본다.

### 5-1. `STAGE_FLOW_ELIGIBLE`

- `stage in {INITIATION, ACCEPTANCE}`

이 경우는 fresh directional candidate에 가깝다.

### 5-2. `STAGE_EXTENSION_CAP`

- `stage == EXTENSION`

이 경우는 완전 탈락은 아니지만, fresh eligibility가 아니라 late continuation 후보로 본다.
즉 기본적으로 `WEAK` 상한을 갖는다.

### 5-3. `TEMPO_PERSISTING`

- `tempo in {PERSISTING, REPEATING}`

지속성 근거가 충분한 경우다.

### 5-4. `TEMPO_EARLY_BUILDING`

- `tempo == EARLY`
- 그리고 `stage == INITIATION`

아직 persistence는 덜 쌓였지만 flow candidate로 보기 시작할 수 있는 초기 상태다.

### 5-5. `BREAKOUT_HOLD_OK`

- `breakout_hold_quality in {STABLE, STRONG}`

### 5-6. `BREAKOUT_HOLD_WEAK`

- `breakout_hold_quality == WEAK`

### 5-7. `STRUCTURE_BIAS_SUPPORT`

- `few_candle_structure_bias == CONTINUATION_FAVOR`

### 5-8. `STRUCTURE_BIAS_MIXED`

- `few_candle_structure_bias == MIXED`

### 5-9. `SWING_STRUCTURE_INTACT`

- bull이면 `higher_low in {HELD, CLEAN_HELD}`
- bear이면 `lower_high in {HELD, CLEAN_HELD}`

### 5-10. `BODY_DRIVE_SUPPORT`

- `body_drive_state in {WEAK_DRIVE, STRONG_DRIVE}`

## 6. F1 상태 정의

### `ELIGIBLE`

- hard disqualifier 없음
- soft support가 충분히 쌓임
- fresh stage 또는 acceptance stage 기준으로 directional flow 후보 자격이 강함

### `WEAK`

- hard disqualifier 없음
- soft support는 일부 있으나 약함
- 또는 `EXTENSION`이라 late candidate로만 인정

### `INELIGIBLE`

- hard disqualifier가 있거나
- soft support가 너무 약해서 directional flow 후보 자격을 주기 어려움

## 7. 이번 v1 운영 규칙

1. hard disqualifier는 항상 soft qualifier보다 우선한다.
2. `EXTENSION`은 hard fail은 아니지만 기본적으로 `ELIGIBLE`이 아니라 `WEAK` 상한이다.
3. `REVERSAL_REJECTION`, `REVERSAL_OVERRIDE`, `AMBIGUITY_HIGH`는 즉시 탈락이다.
4. `MIXED` 구조나 `EARLY` tempo는 `WEAK` 쪽 근거로만 쓴다.
5. F1은 공용 gate이며 XAU/NAS/BTC에 같은 구조를 적용한다.
6. 심볼별 조정은 threshold band 단계에서 하고, F1 hard disqualifier는 심볼별 예외를 허용하지 않는다.

## 8. Surface 설계

### Row-level

- `flow_structure_gate_v1`
- `flow_structure_gate_primary_reason_v1`
- `flow_structure_gate_hard_disqualifiers_v1`
- `flow_structure_gate_soft_qualifiers_v1`
- `flow_structure_gate_soft_score_v1`
- `flow_structure_gate_slot_core_v1`
- `flow_structure_gate_slot_polarity_v1`
- `flow_structure_gate_stage_v1`
- `flow_structure_gate_rejection_type_v1`
- `flow_structure_gate_tempo_v1`
- `flow_structure_gate_ambiguity_v1`
- `flow_structure_gate_reason_summary_v1`

### Summary

- `flow_structure_gate_state_count_summary`
- `flow_structure_gate_primary_reason_count_summary`
- `flow_structure_gate_hard_disqualifier_count_summary`
- `flow_structure_gate_slot_core_count_summary`

## 9. 공용 vs 심볼별 경계

공용으로 유지할 것:

- hard disqualifier 규칙
- soft qualifier 의미
- `ELIGIBLE / WEAK / INELIGIBLE`
- extension 상한 규칙

심볼별로 여기서 아직 허용하지 않을 것:

- ambiguity high 통과
- reversal rejection 완화
- polarity mismatch 완화
- override veto 무시

즉 F1은 공용 gate여야 한다.

## 10. 완료 기준

- XAU/NAS/BTC 모두에서 `flow_structure_gate_v1`가 공통 계약으로 surface된다
- 왜 어떤 row가 `INELIGIBLE`인지 hard disqualifier 기준으로 설명 가능하다
- 왜 어떤 row가 `WEAK`인지 late stage / weak hold / mixed structure 기준으로 설명 가능하다
- runtime detail에 contract/summary/artifact가 올라간다
