# S7. Symbol x Direction x Subtype State Strength Calibration v1

## 1. 목적

`state strength / dominance` 해석층은 공용 계약으로 유지하되, 실제 calibration은 더 이상 `심볼 1개 = 프로필 1개`로 두지 않는다.

이번 S7의 목적은 다음과 같다.

- `심볼 × 방향 × 구조 subtype` 단위로 read-only calibration surface를 둔다.
- 모든 심볼이 `상승 continuation`과 `하락 continuation`을 둘 다 가질 수 있게 한다.
- 한 심볼에서 배운 세부 분해 방식은 다른 심볼에도 같은 틀로 적용하되, 값 자체는 심볼별로 섞지 않는다.

## 2. 왜 단일 심볼 프로필로는 부족한가

이전 버전은 아래처럼 너무 거칠었다.

- `NAS100 = ACTIVE_CANDIDATE`
- `XAUUSD = SEPARATE_PENDING`
- `BTCUSD = SEPARATE_PENDING`

이 구조에선 다음을 표현하지 못한다.

- NAS의 상승 continuation과 하락 continuation 차이
- XAU의 상승 recovery continuation과 하락 rejection continuation 차이
- BTC의 향후 상승/하락 continuation 분리 대기 상태

즉 문제는 `심볼을 분리했는가`가 아니라, **심볼 안에서 방향과 구조 subtype까지 분리했는가**다.

## 3. 새 구조

S7 v1에서는 registry를 다음처럼 관리한다.

- `symbol`
- `family_v1`
  - `UP_CONTINUATION`
  - `DOWN_CONTINUATION`
- `direction_v1`
  - `UP`
  - `DOWN`
- `subtype_v1`
  - 예: `BREAKOUT_HELD`, `RECOVERY_RECLAIM`, `UPPER_REJECT_REJECTION`, `PENDING_REVIEW`

즉 calibration 단위는 이제:

- `NAS100_UP_CONTINUATION_BREAKOUT_HELD`
- `NAS100_DOWN_CONTINUATION_PENDING`
- `XAUUSD_UP_CONTINUATION_RECOVERY`
- `XAUUSD_DOWN_CONTINUATION_REJECTION`
- `BTCUSD_UP_CONTINUATION_PENDING`
- `BTCUSD_DOWN_CONTINUATION_PENDING`

처럼 관리된다.

## 4. 현재 seeded profile

### NAS100

- `UP_CONTINUATION / BREAKOUT_HELD`
  - `ACTIVE_CANDIDATE`
  - retained NAS overlap numeric audit 기반
- `DOWN_CONTINUATION / PENDING_REVIEW`
  - `SEPARATE_PENDING`

### XAUUSD

- `UP_CONTINUATION / RECOVERY_RECLAIM`
  - `ACTIVE_CANDIDATE`
  - `02:00~03:00`, `05:00~06:42` log review 기반
- `DOWN_CONTINUATION / UPPER_REJECT_REJECTION`
  - `ACTIVE_CANDIDATE`
  - `00:30~02:00`, `03:30~04:30` log review 기반

### BTCUSD

- `UP_CONTINUATION / PENDING_REVIEW`
  - `SEPARATE_PENDING`
- `DOWN_CONTINUATION / PENDING_REVIEW`
  - `SEPARATE_PENDING`

## 5. row-level surface

각 row에는 최소 아래가 붙는다.

- `symbol_specific_state_strength_profile_v1`
- `symbol_state_strength_best_profile_key_v1`
- `symbol_state_strength_profile_family_v1`
- `symbol_state_strength_profile_direction_v1`
- `symbol_state_strength_profile_subtype_v1`
- `symbol_state_strength_profile_status_v1`
- `symbol_state_strength_profile_match_v1`
- `symbol_state_strength_bias_hint_v1`
- `symbol_state_strength_profile_reason_summary_v1`

그리고 nested payload에는:

- `symbol_state_strength_selected_profile_v1`
- `symbol_state_strength_profile_catalog_v1`

가 같이 들어간다.

## 6. match 해석

### ACTIVE_CANDIDATE

해당 profile이 이미 calibration된 family다.

- `MATCH`
  - 방향/strength/structure가 profile과 충분히 맞음
- `PARTIAL_MATCH`
  - 방향은 맞지만 세기나 구조가 경계에 가까움
- `OUT_OF_PROFILE`
  - 현재 row가 그 subtype 장면이 아님

### SEPARATE_PENDING

해당 방향 family는 아직 별도 calibration이 필요하다.

- 이 경우에도 `UP_CONTINUATION`과 `DOWN_CONTINUATION`은 따로 surface된다.
- 즉 “아직 안 됨”도 방향별로 분리해서 보게 된다.

## 7. 중요한 원칙

1. 심볼 간 값 복사는 금지한다.
   - NAS 값이 XAU/BTC에 자동 상속되면 안 된다.

2. 심볼 안의 양방향은 반드시 분리한다.
   - 모든 심볼은 `상승 continuation / 하락 continuation` 둘 다 가질 수 있다.

3. subtype은 같은 틀로 확장한다.
   - `BREAKOUT_HELD`
   - `RECOVERY_RECLAIM`
   - `UPPER_REJECT_REJECTION`
   - `PENDING_REVIEW`

4. execution/state25에는 아직 연결하지 않는다.
   - 이번 S7은 read-only calibration layer다.

## 8. 완료 기준

- NAS/XAU/BTC row 모두 `symbol × direction × subtype` 기준으로 surface된다.
- XAU는 `UP`과 `DOWN`이 서로 다른 active candidate로 분리된다.
- BTC는 아직 pending이어도 `UP`과 `DOWN`이 분리된 pending family로 surface된다.
- detail payload와 artifact에서 best profile과 catalog를 같이 읽을 수 있다.
