# D11-2. State Slot Position Lifecycle Policy 상세 계획

## 목적

- `state_slot -> execution interface bridge`에서 한 단계 더 내려가, 해석 슬롯을 실제 포지션 운영 언어로 읽을 수 있는 read-only lifecycle policy 층을 만든다.
- 이 단계의 핵심은 execution을 직접 바꾸는 것이 아니라, 현재 slot 해석이 `entry / hold / add / reduce / exit`에 어떤 posture를 주는지 안정적으로 번역하는 것이다.

## 왜 필요한가

- D11-1은 bias를 선언했다.
  - `entry_bias_v1`
  - `hold_bias_v1`
  - `add_bias_v1`
  - `reduce_bias_v1`
  - `exit_bias_v1`
- 하지만 실제 운영 언어는 bias보다 한 단계 더 아래여야 한다.
- 예를 들어 `entry_bias = LOW`는 사람이 읽기엔 아직 추상적이다.
- 반면 아래처럼 policy로 내려가면 훨씬 운영 가능해진다.
  - `DELAYED_ENTRY`
  - `HOLD_FAVOR`
  - `NO_ADD`
  - `REDUCE_FAVOR`
  - `EXIT_WATCH`

## 이 단계의 위치

- 이 단계는 여전히 read-only다.
- order placement, cancel, resize, exit를 직접 실행하지 않는다.
- state25도 바꾸지 않는다.
- 즉 이 층은 **행동 실행이 아니라 행동 posture surface**다.

## 핵심 원칙

- lifecycle policy는 `dominant_side`를 바꾸지 않는다.
- decomposition layer를 다시 해석하지 않고, 이미 나온 slot/bridge 결과를 행동 언어로 번역만 한다.
- XAU는 기존 bridge bias를 우선 upstream으로 사용한다.
- NAS/BTC는 D10 common slot surface에서 같은 규칙으로 policy를 파생한다.

## 예상 row-level surface

- `state_slot_position_lifecycle_policy_profile_v1`
- `state_slot_lifecycle_policy_state_v1`
- `state_slot_execution_policy_source_v1`
- `entry_policy_v1`
- `hold_policy_v1`
- `add_policy_v1`
- `reduce_policy_v1`
- `exit_policy_v1`
- `state_slot_lifecycle_policy_reason_summary_v1`

## 예상 정책 enum

### entry

- `NO_NEW_ENTRY`
- `DELAYED_ENTRY`
- `SELECTIVE_ENTRY`
- `ACTIVE_ENTRY`

### hold

- `NO_HOLD_EDGE`
- `LIGHT_HOLD`
- `HOLD_FAVOR`
- `STRONG_HOLD`

### add

- `NO_ADD`
- `PROBE_ADD_ONLY`
- `SELECTIVE_ADD`
- `ADD_FAVOR`

### reduce

- `HOLD_SIZE`
- `LIGHT_REDUCE`
- `REDUCE_FAVOR`
- `REDUCE_STRONG`

### exit

- `NO_EXIT_EDGE`
- `EXIT_WATCH`
- `EXIT_PREP`
- `EXIT_FAVOR`

## 번역 규칙

### XAU

- XAU row는 D11-1 bridge bias를 그대로 사용한다.
- 즉 XAU는
  - bridge bias
  - XAU slot
  - ambiguity / texture 반영 완료 상태
  에서 lifecycle policy로만 변환한다.

### NAS / BTC

- NAS/BTC는 D10 common slot surface에서 lifecycle bias를 파생한다.
- stage 기본값:
  - `INITIATION` -> entry 강, hold 중간, add 낮음
  - `ACCEPTANCE` -> hold 강, add 중간
  - `EXTENSION` -> reduce/exit 쪽 강화, 신규 entry 약화
- modifier 조정:
  - `WITH_FRICTION` -> entry/add 약화, reduce 강화
  - `DRIFT` -> entry 약화, reduce 강화
  - `HIGH ambiguity` -> entry/add 억제, reduce/exit 강화
  - `REVIEW_PENDING` -> entry/add 보수화

## 완료 기준

- `XAU / NAS100 / BTCUSD` 세 심볼 모두 lifecycle policy row가 surface된다.
- `entry / hold / add / reduce / exit`가 실행 언어로 읽힌다.
- 여전히 execution/state25는 바뀌지 않는다.

## 상태 기준

- `READY`
  - 세 심볼 모두 lifecycle policy surface 가능
- `HOLD`
  - 일부 심볼만 policy surface 가능
- `BLOCKED`
  - upstream slot/bridge 필드 부족으로 lifecycle translation 불가
