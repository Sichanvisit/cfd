# State Polarity Decomposition v1.5 실행 로드맵

## 1. 로드맵 목적

이 로드맵은 XAU를 더 잘게 나누는 작업을 하되,
그 목적을 `XAU 전용 subtype 확장`이 아니라
`공용 state polarity decomposition 프레임 구축`으로 고정하기 위한 실행 순서 문서다.

즉 이 로드맵의 목표는 아래와 같다.

1. 기존 S0~S7과 CA2/R0~R6-A를 깨지 않게 유지한다.
2. XAU를 파일럿으로 사용해 `polarity / intent / stage / texture / context / tempo`를 시험한다.
3. decomposition slot이 실제로 over-veto와 under-promotion 문제를 줄이는지 shadow-only로 검증한다.
4. 검증이 끝난 뒤에만 NAS/BTC 일반화와 execution/state25 연결을 검토한다.

---

## 2. 현재 출발점

이미 구축된 층:

- `CA2 / R0 ~ R6-A`
- `should-have-done`
- `canonical surface`
- `session split / shadow bias`
- `state_strength_profile_v1`
- `local_structure_profile_v1`
- `runtime read-only surface`
- `state_structure_dominance_profile_v1`
- `dominance validation / accuracy shadow`
- `symbol × direction × subtype` calibration scaffold

즉 지금은 foundation을 새로 만들 단계가 아니라,
그 위에 `state decomposition` 층을 올릴 단계다.

---

## 3. 단계별 로드맵

### D0. 기존 계측 안정 유지

목적:

- 새 decomposition 층이 들어와도 기존 summary와 runtime detail이 깨지지 않게 유지한다.

핵심 작업:

- `runtime_signal_wiring_audit_summary_v1`
- `ca2_r0_stability_summary_v1`
- `should_have_done_summary_v1`
- `canonical_surface_summary_v1`
- `state_structure_dominance_summary_v1`
- `dominance_accuracy_summary_v1`
- `symbol_specific_state_strength_calibration_summary_v1`

의 freshness와 surface 상태를 계속 확인한다.

완료 기준:

- 기존 artifact와 runtime detail 필드가 계속 정상 갱신된다.

상태 기준:

- `READY`: 기존 계측 유지
- `HOLD`: freshness나 일부 surface 흔들림
- `BLOCKED`: decomposition 추가 때문에 기존 계측 깨짐

### D1. 공용 slot vocabulary 고정

목적:

- 심볼 전용 subtype보다 먼저 공용 state slot 언어를 고정한다.

핵심 작업:

- Layer A `polarity`
- Layer B `intent`
- Layer C `stage`
- Layer D `texture`
- Layer E `context`

를 enum 수준으로 고정한다.

v1.5 핵심 후보:

- `polarity`: `BULL / BEAR`
- `intent`: `CONTINUATION / RECOVERY / REJECTION / BREAKDOWN / BOUNDARY`
- `stage`: `INITIATION / ACCEPTANCE / EXTENSION / NONE`
- `texture`: `CLEAN / WITH_FRICTION / DRIFT / EXHAUSTING / FAILED_RECLAIM / POST_DIP / NONE`

추가 원칙:

- core slot은 `polarity + intent + stage`
- modifier는 `texture + location + tempo + ambiguity`
- core slot은 execution decision을 실제로 바꿀 정도의 구조 차이가 있을 때만 승격
- 설명만 다른 장면은 modifier 또는 raw evidence로 남김

완료 기준:

- XAU/NAS/BTC를 모두 같은 slot 언어로 설명할 수 있는 최소 vocabulary가 문서로 고정된다.

### D2. rejection 분리 규칙 고정

목적:

- `rejection`이 reversal evidence인지 friction인지 섞이지 않게 한다.

핵심 작업:

- `REVERSAL_REJECTION`
- `FRICTION_REJECTION`

두 타입을 공용 규칙으로 분리한다.

핵심 원칙:

- structure-breaking rejection -> reversal evidence
- non-breaking rejection -> friction

완료 기준:

- 단일 `upper_reject`가 곧바로 reversal로 소비되는 길이 문서와 계약에서 차단된다.

### D3. continuation stage 분해 추가

목적:

- continuation 내부를 `INITIATION / ACCEPTANCE / EXTENSION`으로 분리한다.

핵심 작업:

- `continuation_stage_v1` 계약 정의
- stage 판단 재료 정의
  - breakout 직후 여부
  - hold bar 수
  - higher low 유지 정도
  - extension 과열 여부

완료 기준:

- 같은 continuation이라도 initiation, acceptance, extension이 구분되어 runtime에서 설명 가능해진다.

### D4. location_context_v1 추가

목적:

- 같은 signal이 어디에서 발생했는지를 별도 층으로 surface한다.

핵심 작업:

- `location_context_v1` 계약 정의
- 최소 enum:
  - `IN_BOX`
  - `AT_EDGE`
  - `POST_BREAKOUT`
  - `EXTENDED`

완료 기준:

- rejection, friction, continuation stage가 위치 문맥과 함께 읽힌다.

### D5. tempo_profile_v1 추가

목적:

- hold, reject, higher low 등의 지속성을 카운트 기반으로 surface한다.

핵심 작업:

- raw persistence field 추가
  - `breakout_hold_bars_v1`
  - `higher_low_count_v1`
  - `reject_repeat_count_v1`
  - `counter_drive_repeat_count_v1`

완료 기준:

- snapshot이 아니라 흐름 지속성까지 해석에 들어간다.

### D5b. ambiguity modifier 추가

목적:

- continuation도 reversal도 아닌 애매한 상태를 friction이나 continuation에 억지로 흡수하지 않게 한다.

핵심 작업:

- `ambiguity_level_v1 = LOW / MEDIUM / HIGH`
- `ambiguity_reason_summary_v1`

계약 추가

중요 원칙:

- ambiguity는 core slot이 아니다
- ambiguity는 side를 바꾸지 않는다
- ambiguity는 `BOUNDARY` bias와 `caution_level`을 강화하는 modifier다

완료 기준:

- 애매한 장면이 continuation 또는 reversal로 과잉 확정되지 않고 별도 조정축으로 남는다.

### D6. XAU pilot mapping

목적:

- 위 공용 slot을 XAU retained window에 먼저 적용한다.

핵심 작업:

- XAU 상승 recovery window
- XAU 하락 rejection window
- XAU mixed/boundary window

를 공용 slot 언어로 다시 맵핑한다.

질문:

- `RECOVERY_RECLAIM` 안에서 initiation/acceptance/extension이 구분되는가?
- `UPPER_REJECT_REJECTION` 안에서 reversal rejection과 friction rejection이 구분되는가?
- drift와 failed reclaim을 별도 texture로 분리할 가치가 있는가?

완료 기준:

- XAU retained evidence가 공용 slot 언어로 설명된다.

### D7. XAU-specific read-only surface

목적:

- XAU에서 공용 slot 결과를 row-level read-only로 surface한다.

예상 필드:

- `polarity_slot_v1`
- `intent_slot_v1`
- `continuation_stage_v1`
- `rejection_type_v1`
- `texture_slot_v1`
- `location_context_v1`
- `tempo_profile_v1`
- `state_slot_v1`

완료 기준:

- XAU row에서 장면이 공용 slot 기준으로 직접 읽힌다.

### D8. XAU should-have-done / dominance 재검증

목적:

- XAU decomposition이 실제로 오판을 줄이는지 본다.

핵심 작업:

- should-have-done join
- canonical diverged join
- dominance validation join

핵심 지표:

- `over_veto_rate`
- `under_veto_rate`
- `friction_separation_quality`
- `boundary_dwell_quality`
- `slot_alignment_rate`

완료 기준:

- decomposition 추가 후 XAU에서 기존보다 더 정확한 error typing이 가능해지고, over-veto가 줄어드는지 수치로 확인된다.

### D9. 공용화 판정

목적:

- XAU에서 검증된 slot을 NAS/BTC로 일반화할 수 있는지 판정한다.

핵심 작업:

- slot별로 다음을 분리한다.
  - 공용 가능한 slot
  - XAU 고유 해석
  - 공용 slot이지만 심볼별 threshold가 필요한 것

완료 기준:

- NAS/BTC 적용 전 공용 slot 카탈로그가 정리된다.

### D10. NAS/BTC 확장

목적:

- XAU에서 검증된 decomposition을 NAS/BTC에 순차 적용한다.

핵심 작업:

- NAS는 continuation stage와 extension 해석부터
- BTC는 recovery/drift 분리부터

순차 적용한다.

완료 기준:

- 세 심볼 모두 같은 slot 언어로 비교 가능해진다.

### D11. execution/state25 검토

목적:

- decomposition이 충분히 검증된 뒤에만 execution/state25 연결을 검토한다.

핵심 작업:

- read-only recommendation
- shadow bias
- bounded canary

순서로만 간다.

중요 원칙:

- decomposition이 검증되기 전에는 execution override 금지
- state25 bias 확대 금지

### D11-1. execution interface bridge 정의

목적:

- decomposition 결과를 나중의 행동 레이어로 넘길 최소 인터페이스를 고정한다.

예상 인터페이스:

- `entry_bias_v1`
- `hold_bias_v1`
- `add_bias_v1`
- `reduce_bias_v1`
- `exit_bias_v1`

중요 원칙:

- 지금 단계에서는 이 인터페이스를 정의만 한다
- 아직 execution을 직접 바꾸지 않는다
- interface는 lifecycle 연결을 위한 bridge일 뿐이다

완료 기준:

- decomposition 결과가 이후 execution policy layer와 연결될 수 있는 안정적인 전달 포맷이 문서로 고정된다.

---

## 4. XAU pilot에서 먼저 물어야 할 질문

1. `RECOVERY_RECLAIM` 내부에 실제로 서로 다른 stage가 존재하는가?
2. `UPPER_REJECT_REJECTION` 내부에서 reversal rejection과 friction rejection이 반복적으로 구분되는가?
3. XAU 상승/하락 장면에서 `location_context_v1`가 해석 품질을 실제로 바꾸는가?
4. `breakout_hold_bars`, `reject_repeat_count` 같은 tempo가 slot 분리의 핵심 근거가 되는가?
5. XAU에서 유효한 slot이 NAS/BTC에도 같은 언어로 설명 가능한가?

---

## 5. 핵심 운영 원칙

- decomposition은 screenshot variation 수집이 아니라 해석 소비 구조 분리다
- 심볼 전용 subtype보다 공용 slot을 먼저 정의한다
- rejection은 reversal과 friction으로 반드시 나눈다
- continuation은 initiation/acceptance/extension으로 분해한다
- location과 tempo 없이 slot을 확정하지 않는다
- XAU는 파일럿이지 영구 예외가 아니다
- shadow/read-only 검증 전 execution/state25 연결 금지

---

## 6. 한 문장 결론

이 로드맵의 본질은 XAU를 더 잘게 쪼개는 것이 아니라, XAU를 가장 선명한 파일럿으로 삼아 상승/하락 polarity state를 더 작은 공용 해석 슬롯으로 분해하고, 그 결과를 검증한 뒤 NAS/BTC와 execution/state25로 안전하게 일반화하는 것이다.

---

## 7. 추가 통제 규칙

이 로드맵은 "무한히 세분화한다"가 아니라
"세분화하되 통제 가능한 구조로 유지한다"는 전제 위에만 유효하다.

그래서 아래 규칙을 실행 원칙으로 추가 고정한다.

### 7-1. slot 조립 규칙

slot은 완전 조합형으로 만들지 않는다.

실행 원칙:

- core slot = `polarity + intent + stage`
- modifier = `texture + location + tempo`

즉 runtime/read-only surface의 기본 이름은 core slot을 중심으로 두고,
modifier는 별도 필드나 설명 필드로 붙인다.

이 규칙의 목적:

- slot 폭발 방지
- retained evidence 부족 상태에서 과도한 subtype 생성 방지
- NAS/BTC 일반화 가능성 유지

### 7-2. stage와 texture의 역할 분리

실행 원칙:

- stage는 시간 위치
- texture는 실행 품질

따라서 구현과 검증에서 다음을 금지한다.

- texture를 stage처럼 분류하는 것
- stage만으로 실행 품질을 단정하는 것
- extension과 exhausting을 같은 차원으로 취급하는 것

### 7-3. decomposition의 권한 제한

실행 원칙:

- decomposition layer는 `dominant_side`를 바꿀 수 없다
- side 변경은 dominance layer의 결과만 따른다

따라서 다음을 금지한다.

- texture modifier만으로 side 변경
- location modifier만으로 side 변경
- tempo modifier만으로 side 변경
- slot naming만으로 reversal 확정

### 7-4. rejection 분리는 모든 단계의 보호 장치

실행 원칙:

- `REVERSAL_REJECTION`은 reversal evidence 계층에서만 강화
- `FRICTION_REJECTION`은 friction 계층에서만 강화

즉 rejection 관련 구현은 항상

- 구조를 깨는가
- 구조는 유지되고 마찰만 증가하는가

를 먼저 나눈 뒤에만 다음 단계로 간다.

### 7-5. location/tempo는 modifier에서 시작

실행 원칙:

- `location_context_v1`는 초기엔 modifier로만 사용
- `tempo_profile_v1`는 초기엔 raw count + modifier로만 사용
- core slot 승격은 충분한 validation 이후에만 허용

---

## 8. 다음 단계의 연결 방향

v1.5는 해석 계층을 정교화하는 단계다.
하지만 이 로드맵은 그 다음 연결 방향도 미리 고정해둘 필요가 있다.

### 8-1. 향후 연결 방향

다음 단계에서 필요한 것은 아래 매핑이다.

- `state_slot -> execution_policy`

예:

- `CONTINUATION_INITIATION` -> 공격적 진입 후보
- `CONTINUATION_ACCEPTANCE` -> 보유/추가 후보
- `CONTINUATION_EXTENSION` -> 신규 진입 억제/축소 후보
- `WITH_FRICTION` -> 진입 지연 후보
- `EXHAUSTING` -> exit pressure 후보

### 8-2. 하지만 지금은 구현하지 않는다

이 연결은 방향만 정의하고, 현재 로드맵 범위에서는 구현하지 않는다.

이유:

- decomposition 검증 전 실행 정책을 올리면 원인 분석이 흐려짐
- XAU pilot이 아직 `slot quality`를 먼저 증명해야 함
- execution/state25에 너무 빨리 붙이면 과최적화 위험이 커짐

즉 현재 순서는 아래와 같이 고정한다.

1. decomposition slot 정의
2. XAU pilot mapping
3. should-have-done / dominance / canonical 검증
4. NAS/BTC 일반화 가능성 확인
5. 그 뒤 `state_slot -> execution_policy` read-only 힌트
6. 마지막에 bounded canary
