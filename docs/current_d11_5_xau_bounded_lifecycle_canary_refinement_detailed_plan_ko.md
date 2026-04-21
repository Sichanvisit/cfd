# D11-5. XAU Bounded Lifecycle Canary Refinement

## 목적

- 기존 `bounded_lifecycle_canary`의 XAU 후보를 더 좁은 `hold-only` / `hold+reduce` slice로 세분화한다.
- XAU canary가 단순 `ALIGNED`만으로 `BOUNDED_READY`가 되지 않도록 위험 게이트를 추가한다.
- 이후 live canary로 가더라도 `XAU_SINGLE_SYMBOL` 범위를 넘지 않게 안전장치를 먼저 고정한다.

## 왜 필요한가

- 현재 D11-4는 XAU에서 `BRIDGE_BIAS + ALIGNED + strong hold`면 비교적 넓게 `BOUNDED_READY`를 줄 수 있다.
- 하지만 XAU는 같은 `hold/reduce`라도
  - 실제 pilot slot과 맞는지
  - ambiguity가 높은지
  - texture가 drift인지
  - entry가 아직 너무 열려 있는지
  - hold 자체가 충분히 강한지
  를 더 봐야 한다.
- 즉 지금 단계의 핵심은 XAU canary를 늘리는 게 아니라, `BOUNDED_READY`를 더 비싸게 만드는 것이다.

## 핵심 원칙

- XAU refinement는 여전히 `read-only`다.
- `bounded lifecycle canary`는 실행, 주문, state25를 바꾸지 않는다.
- `BOUNDED_READY`는 `pilot match + non-high ambiguity + non-drift texture + delayed entry/no new entry + hold support`를 모두 통과한 경우에만 허용한다.
- `HOLD_ONLY`와 `HOLD_REDUCE_ONLY`는 다른 slice다.
- `entry delay observe`는 `observe_only`에 남긴다.

## 새로 surface할 것

- `xau_lifecycle_canary_risk_gate_v1`
- `xau_lifecycle_canary_scope_detail_v1`
- refined `lifecycle_canary_policy_slice_v1`
  - `HOLD_ONLY`
  - `HOLD_REDUCE_ONLY`
  - `ENTRY_DELAY_ONLY`

## XAU 위험 게이트 v1

- `PASS`
- `FAIL_PILOT_MATCH`
- `FAIL_AMBIGUITY`
- `FAIL_TEXTURE_DRIFT`
- `FAIL_ENTRY_TOO_OPEN`
- `FAIL_HOLD_POLICY`
- `NOT_APPLICABLE`

## XAU scope detail v1

- `XAU_HOLD_ONLY`
- `XAU_HOLD_REDUCE`
- `XAU_DELAY_ENTRY_OBSERVE`
- `NONE`

## 판정 흐름

1. upstream shadow audit alignment를 본다.
2. `symbol == XAUUSD` 이고 `source == BRIDGE_BIAS`일 때만 refined XAU gate를 계산한다.
3. 아래 조건을 통과하면 `PASS`
   - `xau_pilot_window_match_v1 in {MATCHED_ACTIVE_PROFILE, PARTIAL_ACTIVE_PROFILE}`
   - `xau_ambiguity_level_v1 != HIGH`
   - `xau_texture_slot_v1 != DRIFT`
   - `entry_policy_v1 in {DELAYED_ENTRY, NO_NEW_ENTRY}`
   - `hold_policy_v1 in {HOLD_FAVOR, STRONG_HOLD}`
4. `PASS + strong hold + strong/favor reduce`면
   - `BOUNDED_READY`
   - `HOLD_REDUCE_ONLY`
   - `XAU_HOLD_REDUCE`
5. `PASS + hold support + light/no reduce`면
   - `BOUNDED_READY`
   - `HOLD_ONLY`
   - `XAU_HOLD_ONLY`
6. 그 외는 `OBSERVE_ONLY`

## 기대 효과

- XAU canary가 한 덩어리 `hold/reduce` 후보가 아니라, 더 좁은 policy slice로 읽힌다.
- `BOUNDED_READY` 오남발을 막는다.
- 이후 XAU canary를 실제 bounded review로 올릴 때 필요한 위험 게이트가 runtime row에 이미 남는다.

## 완료 기준

- XAU row에서 `xau_lifecycle_canary_risk_gate_v1`와 `xau_lifecycle_canary_scope_detail_v1`를 읽을 수 있다.
- `HOLD_ONLY`와 `HOLD_REDUCE_ONLY`가 구분된다.
- `ALIGNED`만으로는 XAU가 자동으로 `BOUNDED_READY`가 되지 않는다.

## 상태 기준

- `READY`: refined XAU gate가 row/summary/artifact에 정상 surface됨
- `HOLD`: XAU row는 있으나 gate 정보가 부분 surface
- `BLOCKED`: 기존 bounded canary surface를 깨뜨리거나 XAU row를 읽지 못함
