# D7. XAU-specific read-only surface 상세 계획

## 목적

지금까지 잠근 공용 decomposition 계약을 XAU runtime row에 실제로 보이게 만드는 단계다.

이 단계의 목표는 XAU 전용 예외 규칙을 늘리는 것이 아니라, 아래 공용 언어가 XAU row에서 어떻게 소비되는지 read-only로 surface하는 것이다.

- `polarity`
- `intent`
- `stage`
- `rejection split`
- `texture`
- `location`
- `tempo`
- `ambiguity`

## 왜 필요한가

`D1 ~ D6`에서 vocabulary, rejection 분리, continuation stage, location, tempo, ambiguity, XAU pilot mapping까지는 고정됐다.

하지만 아직 XAU runtime row를 볼 때는 “지금 이 장면이 XAU 공용 decomposition 언어로 정확히 어떻게 읽히는가”가 한 번에 보이지 않는다.

그래서 D7은:

1. XAU row를 공용 decomposition 언어로 묶어 보여주고
2. pilot profile과 현재 row가 얼마나 맞는지 read-only로 surface하고
3. 이후 D8 검증에서 should-have-done / dominance error와 바로 연결될 수 있게 만든다.

## 핵심 원칙

- XAU surface는 `dominant_side`를 바꾸지 않는다.
- XAU surface는 `execution/state25`를 바꾸지 않는다.
- XAU 전용 규칙을 만드는 것이 아니라 공용 decomposition 언어를 XAU에서 읽기 좋게 표면화한다.
- XAU가 아닌 심볼은 `NOT_APPLICABLE`로 남겨 schema를 흔들지 않는다.

## row-level surface

- `xau_readonly_surface_profile_v1`
- `xau_polarity_slot_v1`
- `xau_intent_slot_v1`
- `xau_continuation_stage_v1`
- `xau_rejection_type_v1`
- `xau_texture_slot_v1`
- `xau_location_context_v1`
- `xau_tempo_profile_v1`
- `xau_ambiguity_level_v1`
- `xau_state_slot_core_v1`
- `xau_state_slot_modifier_bundle_v1`
- `xau_pilot_window_match_v1`
- `xau_surface_reason_summary_v1`

## surface 해석 기준

### polarity / intent

- `XAUUSD_UP_CONTINUATION_RECOVERY_V1` profile이면 `BULL / RECOVERY`
- `XAUUSD_DOWN_CONTINUATION_REJECTION_V1` profile이면 `BEAR / REJECTION`
- profile이 비어 있어도 raw row의 rebound / reject / breakdown 흔적으로 약한 fallback 해석은 허용

### stage

- recovery/rejection가 막 시작된 probe 성격이면 `INITIATION`
- held 구조와 edge/box 정착이 보이면 `ACCEPTANCE`
- 지나친 연장 의미가 강할 때만 `EXTENSION`

### rejection split

- `BREAKDOWN_HELD`처럼 구조 파손 증거가 붙으면 `REVERSAL_REJECTION`
- 단순 reject/probe면 `FRICTION_REJECTION`
- recovery 장면이면 `NONE`

### texture / location / tempo / ambiguity

- texture는 read-only 품질 설명층
- location은 `IN_BOX / AT_EDGE / POST_BREAKOUT / EXTENDED`
- tempo는 `EARLY / PERSISTING / REPEATING / EXTENDED`
- ambiguity는 `LOW / MEDIUM / HIGH`

## 요약 artifact

- `xau_readonly_surface_summary_v1`
- `xau_readonly_surface_latest.json`
- `xau_readonly_surface_latest.md`

## 완료 기준

- XAU row에서 공용 decomposition 언어가 read-only로 한 번에 읽힌다.
- pilot profile match와 실제 slot surface가 같이 보인다.
- NAS/BTC는 `NOT_APPLICABLE`로 남아 schema가 흔들리지 않는다.

## 상태 기준

- `READY`: XAU row surface와 summary가 정상 생성됨
- `HOLD`: XAU row는 있으나 surface 일부가 비어 있음
- `BLOCKED`: XAU row surface 자체가 누락되거나 runtime payload가 깨짐
