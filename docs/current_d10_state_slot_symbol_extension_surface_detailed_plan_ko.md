# D10. State Slot Symbol Extension Surface 상세 계획

## 목적

- XAU 파일럿에서 검증한 decomposition 언어가 `NAS100`, `BTCUSD`에도 같은 core slot + modifier 구조로 surface되는지 확인한다.
- 이 단계의 목적은 NAS/BTC를 실행에 연결하는 것이 아니라, 공용 vocabulary가 실제로 다른 심볼 row에서도 읽히는지 확인하는 것이다.

## 왜 필요한가

- D6~D9까지는 XAU를 기준으로 공용 slot 언어를 시험했다.
- 하지만 실제 공용화는 `XAU에서 예쁘게 설명된다`가 아니라 `다른 심볼 row에서도 같은 언어로 읽힌다`가 확인되어야 의미가 있다.
- 특히 로드맵에서 이미 정한 것처럼:
  - `NAS100`은 continuation stage / extension 해석을 먼저 본다.
  - `BTCUSD`는 recovery / drift 분리를 먼저 본다.

## 핵심 원칙

- D10은 read-only surface다.
- D10은 `dominant_side`를 바꾸지 않는다.
- D10은 `execution`, `state25`를 바꾸지 않는다.
- `XAU exact slot match`와 `common vocabulary compatibility`는 분리해서 본다.
  - exact match가 없더라도 공용 vocabulary는 compatible할 수 있다.

## 공용 surface 목표

- XAU:
  - 기존 `xau_*` decomposition surface를 common field로 mirror
- NAS100:
  - continuation / acceptance / extension 쪽이 공용 언어로 읽히는지 확인
- BTCUSD:
  - recovery / drift 쪽이 공용 언어로 읽히는지 확인

## 예상 row-level surface

- `state_slot_symbol_extension_surface_profile_v1`
- `state_slot_symbol_extension_state_v1`
- `common_state_polarity_slot_v1`
- `common_state_intent_slot_v1`
- `common_state_continuation_stage_v1`
- `common_state_rejection_type_v1`
- `common_state_texture_slot_v1`
- `common_state_location_context_v1`
- `common_state_tempo_profile_v1`
- `common_state_ambiguity_level_v1`
- `common_state_slot_core_v1`
- `common_state_slot_modifier_bundle_v1`
- `common_vocabulary_compatibility_v1`
- `xau_commonization_slot_match_v1`
- `xau_commonization_verdict_v1`
- `common_state_slot_reason_summary_v1`

## 상태 해석 기준

### XAU

- XAU는 기존 pilot mapping / readonly surface 결과를 그대로 common surface에 옮긴다.
- 이 row는 `XAU_PILOT` 상태로 표시한다.

### NAS100

- symbol extension 초점:
  - continuation stage
  - extension 해석
- 이 row는 `NAS_STAGE_EXTENSION` 상태로 표시한다.
- exact XAU slot이 없어도 공용 vocabulary가 읽히면 compatible로 본다.

### BTCUSD

- symbol extension 초점:
  - recovery
  - drift
- 이 row는 `BTC_RECOVERY_DRIFT_EXTENSION` 상태로 표시한다.
- 현재 calibration이 pending이어도, slot core와 modifier가 읽히면 vocabulary surface 자체는 진행된 것으로 본다.

## D9와의 관계

- D9는 XAU pilot 기반으로 `exact slot commonization`을 판단했다.
- D10은 그 위에서 다음을 분리해 보여준다.
  - `xau_commonization_slot_match_v1`
    - XAU pilot exact slot과 일치하는가
  - `common_vocabulary_compatibility_v1`
    - exact match가 없어도 공용 언어 자체가 다른 심볼 row에 먹히는가

즉 D10은 “XAU에서 검증한 슬롯이 정확히 재등장하는가”보다,
“같은 decomposition 문법이 NAS/BTC에서도 무리 없이 surface되는가”를 더 중요하게 본다.

## 완료 기준

- `XAU / NAS100 / BTCUSD` 세 row가 모두 common slot 언어로 surface된다.
- `common_state_slot_core_v1`와 modifier bundle이 세 심볼 모두 읽힌다.
- XAU exact slot match 여부와 공용 vocabulary compatibility가 분리돼 보인다.
- runtime detail과 artifact에서 세 심볼 비교가 가능하다.

## 상태 기준

- `READY`
  - 세 심볼 모두 common slot 언어로 surface됨
- `HOLD`
  - 일부 심볼은 surface되지만 core slot이 비거나 pending이 큼
- `BLOCKED`
  - extension surface가 runtime payload에 안 올라오거나 기존 decomposition field와 충돌
