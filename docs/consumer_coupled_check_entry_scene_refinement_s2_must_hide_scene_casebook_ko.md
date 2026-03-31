# Consumer-Coupled Check/Entry Scene Refinement
## S2. Must-Hide Scene Casebook

### 기준

이번 casebook은 아래 두 축을 함께 사용해 정리했다.

- S0 baseline에서 드러난 leakage family
- recent runtime row 기준 actual `consumer_check_state_v1`

즉 S2는
`지금 실제로 너무 많이 남는 장면`
을 `hide / downgrade / reduce`로 분리한 문서다.

---

### S2 핵심 결론

현재 leakage 관점에서 먼저 고정할 장면은 아래다.

1. `BTC lower buy structural observe`
- `outer_band_guard + probe_not_promoted`인데도 같은 signature가 계속 남는다
- 현재는 `OBSERVE 1개 체크`라 stage는 낮지만,
  반복 시그니처가 너무 많아 `hide` 후보가 된다

2. `NAS lower rebound probe`
- `probe_promotion_gate + probe_not_promoted`인데도 `PROBE 2개 체크`로 남는다
- 현재는 가장 전형적인 `downgrade` 후보다

3. `XAU middle anchor sell observe`
- must-show 성격은 있지만
- 같은 signature가 너무 반복되면 over-display가 된다
- 따라서 `reduce` 후보다

즉 현재 S2에서 가장 중요한 분리는:

- `BTC = hide`
- `NAS = downgrade`
- `XAU = reduce`

이다.

---

## Family Summary

### 1. lower rebound probe leakage

대표 reason:

- `lower_rebound_probe_observe`
- `probe_not_promoted`
- `probe_promotion_gate`

대표 심볼:

- `NAS100`

현재 해석:

- 구조적으로는 lower rebound family라서 display-worthy 요소가 있다
- 하지만 현재는 `PROBE + 2개 체크`로 너무 강하게 남는다

권장 suppression:

- `downgrade`

즉 hidden이 아니라
`PROBE -> OBSERVE`
쪽이 더 맞다.

### 2. structural observe over-display

대표 reason:

- `outer_band_reversal_support_required_observe`
- `middle_sr_anchor_required_observe`
- `outer_band_guard`
- `middle_sr_anchor_guard`

대표 심볼:

- `BTCUSD`
- `XAUUSD`

현재 해석:

- 구조적으로는 must-show 성격이 일부 있다
- 하지만 같은 signature가 너무 반복되면 display leakage가 된다

권장 suppression:

- BTC는 `hide`
- XAU는 `reduce`

---

## Case Table

### Case S2-01

- `case_id`: S2-01
- `symbol`: BTCUSD
- `chart_time`: `2026-03-27 21:47:23 ~ 21:47:57`
- `scene_family`: structural observe over-display
- `user_chart_impression`: 계속 하락 중인데 buy 쪽 약한 체크가 너무 많이 남는다
- `current_display`: `OBSERVE`, `display_score=0.75`, `repeat_count=1`
- `expected_suppression`: `hide`
- `runtime_observe_reason`: `outer_band_reversal_support_required_observe`
- `blocked_by`: `outer_band_guard`
- `action_none_reason`: `probe_not_promoted`
- `probe_scene_id`: `btc_lower_buy_conservative_probe`
- `consumer_check_stage`: `OBSERVE`
- `consumer_check_display_ready`: `true`
- `consumer_check_display_score`: `0.75`
- `consumer_check_display_repeat_count`: `1`
- `entry_ready`: `false`
- `why_must_hide`: 같은 signature가 연속 반복되고, 현재 구간은 사용자가 “buy 가능성”으로 읽기엔 과도하게 낙관적으로 보인다

평가:

- stage는 이미 약하지만
- 반복 시그니처가 너무 자주 남아서 noise가 된다
- 이 family는 “첫 1회만 허용하고 이후 hide” 같은 suppression이 맞다

### Case S2-02

- `case_id`: S2-02
- `symbol`: NAS100
- `chart_time`: `2026-03-27 21:44:05 ~ 21:47:26`
- `scene_family`: lower rebound probe leakage
- `user_chart_impression`: 계속 하락 중인데 buy probe가 너무 강하게 남는다
- `current_display`: `PROBE`, `display_score=0.86`, `repeat_count=2`
- `expected_suppression`: `downgrade`
- `runtime_observe_reason`: `lower_rebound_probe_observe`
- `blocked_by`: `probe_promotion_gate`
- `action_none_reason`: `probe_not_promoted`
- `probe_scene_id`: `nas_clean_confirm_probe`
- `consumer_check_stage`: `PROBE`
- `consumer_check_display_ready`: `true`
- `consumer_check_display_score`: `0.86`
- `consumer_check_display_repeat_count`: `2`
- `entry_ready`: `false`
- `why_must_hide`: family 자체는 must-show 성격이 있지만, 현재 단계는 실제 상태보다 너무 공격적으로 보인다

평가:

- 완전 hidden은 과할 수 있다
- 하지만 `PROBE 2개`는 지나치다
- `OBSERVE 1개`로 낮추는 방향이 맞다

### Case S2-03

- `case_id`: S2-03
- `symbol`: XAUUSD
- `chart_time`: `2026-03-27 21:37:06 ~ 21:37:26`
- `scene_family`: structural observe over-display
- `user_chart_impression`: XAU 쪽 sell observe가 너무 빈번하게 반복된다
- `current_display`: `OBSERVE`, `display_score=0.75`, `repeat_count=1`
- `expected_suppression`: `reduce`
- `runtime_observe_reason`: `middle_sr_anchor_required_observe`
- `blocked_by`: `middle_sr_anchor_guard`
- `action_none_reason`: `observe_state_wait`
- `probe_scene_id`: `""`
- `consumer_check_stage`: `OBSERVE`
- `consumer_check_display_ready`: `true`
- `consumer_check_display_score`: `0.75`
- `consumer_check_display_repeat_count`: `1`
- `entry_ready`: `false`
- `why_must_hide`: middle anchor observe는 must-show 성격이 있지만, 동일 시그니처가 너무 자주 반복되면 XAU sell bias가 과하게 보인다

평가:

- hidden은 과하다
- stage downgrade도 불필요하다
- 대신 반복/빈도 suppression이 맞다

### Case S2-04

- `case_id`: S2-04
- `symbol`: XAUUSD
- `chart_time`: `2026-03-27 21:43:43`, `21:46:32`
- `scene_family`: upper reject probe boundary
- `user_chart_impression`: 상단 reject는 보여야 하지만 너무 강하면 과장된다
- `current_display`: `PROBE`, `display_score=0.82`, `repeat_count=2`
- `expected_suppression`: `defer`
- `runtime_observe_reason`: `upper_reject_probe_observe`
- `blocked_by`: `probe_promotion_gate`
- `action_none_reason`: `probe_not_promoted`
- `probe_scene_id`: `xau_upper_sell_probe`
- `consumer_check_stage`: `PROBE`
- `consumer_check_display_ready`: `true`
- `consumer_check_display_score`: `0.82`
- `consumer_check_display_repeat_count`: `2`
- `entry_ready`: `false`
- `why_must_hide`: 이 family는 S1에서 must-show와도 연결되므로, S2 단독으로 suppression을 확정하면 안 된다

평가:

- leakage라기보다 must-show와 must-hide 경계에 있는 family다
- S4 contract refinement에서 S1 결과와 합쳐서 판단해야 한다

---

## Hide / Downgrade / Reduce Summary

### hide

- S2-01 BTC repeated structural lower-buy observe

권장 처리:

- 동일 signature 반복 run에서는 hide
- 최소 첫 1회만 허용하는 방향 검토

### downgrade

- S2-02 NAS lower rebound probe leakage

권장 처리:

- `PROBE -> OBSERVE`
- `0.86 / repeat 2`를 `0.75 / repeat 1` 쪽으로 낮추는 계약 검토

### reduce

- S2-03 XAU middle anchor repeated observe

권장 처리:

- stage 유지
- repetition / cadence suppression

### defer

- S2-04 XAU upper reject probe

권장 처리:

- S1 must-show와 충돌하므로 S4에서 통합 판단

---

## Boundary Note

아래 family는 이번 S2에서 `must-hide leakage`가 아니라
오히려 hidden이 잘 작동한 boundary-good case로 본다.

- `NAS100 lower_rebound_confirm + energy_soft_block + execution_soft_blocked`
  - `BLOCKED`
  - `display=false`
  - `display_score=0.0`

즉 모든 blocked confirm을 다시 눌러야 하는 건 아니고,
현재 이미 잘 숨겨진 family도 있다는 뜻이다.

---

## Suppression Contract Candidate

### Candidate A

- `outer_band_reversal_support_required_observe`
- `blocked_by=outer_band_guard`
- `action_none_reason=probe_not_promoted`
- `symbol=BTCUSD`

질문:

- 같은 signature 반복 시
- 첫 1회 이후 hidden으로 내릴 것인가

### Candidate B

- `lower_rebound_probe_observe`
- `blocked_by=probe_promotion_gate`
- `action_none_reason=probe_not_promoted`
- `symbol=NAS100`

질문:

- 이 family는 must-show는 유지하되
- `PROBE -> OBSERVE`로 낮출 것인가

### Candidate C

- `middle_sr_anchor_required_observe`
- `blocked_by=middle_sr_anchor_guard`
- `action_none_reason=observe_state_wait`
- `symbol=XAUUSD`

질문:

- must-show는 유지하되
- 동일 run 반복만 줄일 것인가

### Candidate D

- `upper_reject_probe_observe`
- `blocked_by=probe_promotion_gate`
- `action_none_reason=probe_not_promoted`
- `symbol=XAUUSD`

질문:

- 이 family는 leakage suppression 대상이 아니라
- S1/S2 충돌 family로 별도 보류할 것인가

---

## S2 결론

S2 기준 현재 그림은 아래와 같다.

1. `BTC structural lower-buy observe`
- hide가 맞다

2. `NAS lower rebound probe`
- downgrade가 맞다

3. `XAU middle anchor observe`
- reduce가 맞다

4. `XAU upper reject probe`
- S1과 함께 보는 defer family다

즉 S2는 다음을 확정한다.

- leakage를 하나로 보지 않고
- `hide / downgrade / reduce / defer`
로 분리해서 다뤄야 한다

---

## 다음 단계

1. `S3 visually similar scene alignment audit`
2. `S4 consumer_check_state contract refinement`

즉 S2는
“무엇을 얼마나 눌러야 하는가”
를 먼저 고정해 주는 단계다.
