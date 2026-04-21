# D6 XAU pilot mapping 상세 계획

## 1. 목적

D6의 목적은 지금까지 만든 공용 decomposition 언어를
**XAU retained evidence window에 실제로 입혀보는 파일럿 단계**를 고정하는 것이다.

이번 단계는 아직 row-level execution/state25를 바꾸지 않는다.
우선 문서, 코드, runtime detail이 같은 XAU pilot mapping 언어를 보게 만드는 것이 목표다.

---

## 2. 왜 필요한가

XAU는 현재 retained evidence가 가장 선명한 파일럿이다.

- 상승 recovery continuation window가 반복적으로 보인다
- 하락 rejection continuation window가 반복적으로 보인다
- `should-have-done`, `dominance`, `symbol-direction-subtype` scaffold와 바로 연결할 수 있다

즉 D6은 XAU 전용 예외를 만드는 단계가 아니라,
**공용 slot / stage / rejection / location / tempo / ambiguity 언어가 실제 retained window에 설명력 있게 붙는지 시험하는 단계**다.

---

## 3. D6에서 고정할 핵심 규칙

### 3-1. XAU pilot은 공용 프레임 검증용이다

- XAU는 파일럿 심볼이지만 영구 예외 심볼이 아니다
- XAU pilot mapping은 common slot language를 먼저 검증하는 용도다

### 3-2. 양방향 evidence를 동시에 유지한다

pilot catalog에는 최소 아래 두 계열이 같이 살아 있어야 한다.

- `BULL / RECOVERY`
- `BEAR / REJECTION`

즉 XAU pilot은 상승만 보는 것도 아니고 하락만 보는 것도 아니다.

### 3-3. pilot mapping은 read-only다

- `dominant_side`를 바꾸지 못한다
- execution/state25를 바꾸지 않는다
- row-level bias override를 하지 않는다

즉 D6은 retained window를 공용 언어로 재설명하는 단계다.

---

## 4. D6에서 surface할 계약

runtime/detail에서는 아래를 읽을 수 있어야 한다.

- `xau_pilot_mapping_contract_v1`
- `xau_pilot_mapping_summary_v1`
- `xau_pilot_mapping_artifact_paths`

contract 핵심 필드:

- `pilot_window_catalog_v1`
- `common_slot_mapping_fields_v1`
- `pilot_status_enum_v1`

pilot window row 예시 필드:

- `window_id_v1`
- `linked_profile_key_v1`
- `polarity_slot_v1`
- `intent_slot_v1`
- `stage_slot_v1`
- `texture_slot_v1`
- `location_context_v1`
- `tempo_profile_v1`
- `ambiguity_level_v1`
- `state_slot_core_v1`
- `state_slot_modifier_bundle_v1`
- `mapping_reason_summary_v1`

이번 버전은 current row 계산을 붙이기보다,
먼저 XAU retained window와 common slot mapping을 공용 artifact로 고정하는 데 집중한다.

---

## 5. 파일럿 window 기준

이번 D6에서는 최소 아래 XAU retained window를 pilot catalog에 고정한다.

- `xau_up_recovery_1_0200_0300`
- `xau_up_recovery_2_0500_0642`
- `xau_down_core_1_0030_0200`
- `xau_down_core_2_0330_0430`

이 catalog는 지금까지 축적된 XAU profile scaffold와 직접 연결된다.

---

## 6. 산출물

shadow artifact:

- `xau_pilot_mapping_latest.json`
- `xau_pilot_mapping_latest.md`

runtime detail:

- `xau_pilot_mapping_contract_v1`
- `xau_pilot_mapping_summary_v1`
- `xau_pilot_mapping_artifact_paths`

---

## 7. 완료 기준

- XAU retained window가 common slot language로 pilot mapping된 공용 계약이 문서/코드/runtime에 동시에 존재한다
- runtime detail에서 같은 contract와 summary를 읽을 수 있다
- 양방향 XAU evidence가 catalog에 모두 포함된다
- execution/state25 change는 여전히 `false`로 잠겨 있다

---

## 8. 상태 기준

- `READY`: XAU pilot mapping 계약, summary, artifact가 정상 surface됨
- `HOLD`: pilot window catalog는 있으나 common slot mapping이 흔들림
- `BLOCKED`: XAU pilot mapping이 dominance ownership을 침범하거나 runtime export가 누락됨
