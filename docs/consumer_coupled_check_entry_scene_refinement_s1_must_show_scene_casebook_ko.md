# Consumer-Coupled Check/Entry Scene Refinement
## S1. Must-Show Scene Casebook

### 기준

이번 casebook은 아래 두 축을 함께 사용해 정리했다.

- 사용자 thread에서 직접 지적한 chart 장면
- `entry_decisions.csv` recent row 기준 runtime mapping

즉 S1은 purely automatic casebook이 아니라,
`manual chart impression + runtime row`
를 같이 묶은 hybrid casebook이다.

---

### S1 핵심 결론

현재 must-show 관점에서 먼저 고정할 장면은 아래다.

1. `BTC / NAS lower rebound probe family`
- 현재는 잘 보이는 편이다
- 다만 weak check가 아니라 `PROBE`로 너무 강하게 남는 문제가 같이 있다

2. `XAU middle_sr_anchor_required_observe`
- 현재는 weak sell observe로 잘 살아 있다
- 즉 must-show 관점에서는 `good`

3. `XAU upper_reject_probe_observe + energy_soft_block`
- 사용자가 보기엔 약한 sell check라도 남아야 할 장면이 일부 있다
- 현재는 `display=false`로 사라지는 row가 반복된다
- 즉 S1의 대표 `missing` 후보

4. `NAS lower_rebound_confirm + energy_soft_block`
- 사용자가 보기엔 최소 observe는 남길 수 있는 장면이 일부 있다
- 현재는 `BLOCKED + display=false`
- 즉 보수적으로는 `missing` 또는 `debatable` 후보

---

## Family Summary

### 1. lower rebound family

대표 reason:

- `lower_rebound_probe_observe`
- `lower_rebound_confirm`
- `outer_band_reversal_support_required_observe`

현재 해석:

- BTC/NAS에서는 buy-side로 강하게 살아남는다
- XAU에서는 같은 family보다 conflict/upper 쪽 family로 자주 갈라진다

must-show 기준:

- 최소 `OBSERVE` 또는 `WATCH/WAIT`
- 하단 edge에서 side가 clear하면 완전 hidden은 피해야 한다

### 2. upper reject family

대표 reason:

- `upper_reject_probe_observe`
- `upper_reject_confirm`
- `upper_break_fail_confirm`

현재 해석:

- XAU에서 주요 scene으로 잡힌다
- `probe_promotion_gate`이면 `PROBE/display=true`로 남기도 한다
- 그러나 `energy_soft_block`이면 완전히 숨겨지는 구간이 많다

must-show 기준:

- 진입 막힘과 별개로
- 구조적 상단 reject는 약한 sell observe가 남아야 하는 case가 있다

### 3. middle reclaim / middle reject family

대표 reason:

- `middle_sr_anchor_required_observe`

현재 해석:

- XAU에서 최근 repeated weak sell observe로 잘 보인다
- 사용자가 “가운데 기다림도 떠야 한다”고 느낀 장면과 연결되는 family다

must-show 기준:

- 방향성이 clear하고
- generic noise가 아니라 anchor scene이면
- 최소 `OBSERVE`는 남아야 한다

---

## Case Table

### Case S1-01

- `case_id`: S1-01
- `symbol`: BTCUSD
- `scene_family`: lower rebound
- `user_chart_impression`: 하단 반등 시도 자리라 약한 buy check는 있어야 함
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: `lower_rebound_probe_observe`
- `blocked_by`: `probe_promotion_gate`
- `action_none_reason`: `probe_not_promoted`
- `probe_scene_id`: `btc_lower_buy_conservative_probe`
- `consumer_check_stage`: `PROBE`
- `consumer_check_display_ready`: `true`
- `entry_ready`: `false`
- `current_status`: `good`
- `why_must_show`: 하단 edge 반등 family는 최소 약한 directional check가 있어야 사용자가 구조를 읽을 수 있음

평가:

- must-show 기준은 충족한다
- 다만 현재는 `PROBE`로 너무 강하게 남아 leakage 쪽 문제와 겹친다

### Case S1-02

- `case_id`: S1-02
- `symbol`: NAS100
- `scene_family`: lower rebound
- `user_chart_impression`: 하단 반등 시도 자리라 약한 buy check는 있어야 함
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: `lower_rebound_probe_observe`
- `blocked_by`: `probe_promotion_gate`
- `action_none_reason`: `probe_not_promoted`
- `probe_scene_id`: `nas_clean_confirm_probe`
- `consumer_check_stage`: `PROBE`
- `consumer_check_display_ready`: `true`
- `entry_ready`: `false`
- `current_status`: `good`
- `why_must_show`: 구조적 lower rebound family는 display-worthy scene이다

평가:

- must-show 기준은 충족한다
- 다만 BTC와 마찬가지로 너무 강한 단계에서 남는다

### Case S1-03

- `case_id`: S1-03
- `symbol`: XAUUSD
- `scene_family`: middle reject / anchor observe
- `user_chart_impression`: 중간 구간에서도 구조적 기다림은 약한 sell check로 보여야 함
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: `middle_sr_anchor_required_observe`
- `blocked_by`: `middle_sr_anchor_guard`
- `action_none_reason`: `observe_state_wait`
- `probe_scene_id`: `""`
- `consumer_check_stage`: `OBSERVE`
- `consumer_check_display_ready`: `true`
- `entry_ready`: `false`
- `current_status`: `good`
- `why_must_show`: middle anchor scene은 진입이 아니어도 관찰 continuity를 위해 약한 체크가 필요함

평가:

- 현재 must-show 기준을 잘 충족하는 대표 case다

### Case S1-04

- `case_id`: S1-04
- `symbol`: XAUUSD
- `scene_family`: upper reject
- `user_chart_impression`: 상단 reject가 분명한데 약한 sell check라도 남아야 함
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: `upper_reject_probe_observe`
- `blocked_by`: `energy_soft_block`
- `action_none_reason`: `execution_soft_blocked`
- `probe_scene_id`: `xau_upper_sell_probe`
- `consumer_check_stage`: `BLOCKED`
- `consumer_check_display_ready`: `false`
- `entry_ready`: `false`
- `current_status`: `missing`
- `why_must_show`: 진입은 막혀도 상단 reject 자체는 사용자가 구조적 sell setup으로 읽는 장면이다

평가:

- 현재는 blocked가 되면서 완전히 hidden되는 구간이 많다
- S4에서 “blocked라도 약한 observe는 남길지”를 정해야 한다

### Case S1-05

- `case_id`: S1-05
- `symbol`: NAS100
- `scene_family`: lower rebound confirm
- `user_chart_impression`: 하단 confirm 계열이면 최소 observe는 남겨야 할 수 있음
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: `lower_rebound_confirm`
- `blocked_by`: `energy_soft_block`
- `action_none_reason`: `execution_soft_blocked`
- `probe_scene_id`: `""`
- `consumer_check_stage`: `BLOCKED`
- `consumer_check_display_ready`: `false`
- `entry_ready`: `false`
- `current_status`: `debatable`
- `why_must_show`: confirm family라면 완전 hidden보다 약한 check가 나을 가능성이 있음

평가:

- 사용자의 체감상 must-show일 수 있지만
- 현재는 에너지 soft block이 강해서 noisy false positive일 수도 있다
- S4에서 바로 열기보다 debatable bucket으로 둔다

### Case S1-06

- `case_id`: S1-06
- `symbol`: BTCUSD
- `scene_family`: upper reject manual carry-over
- `user_chart_impression`: 상단 sell 자리 3곳은 약한 sell check라도 있었어야 함
- `expected_min_display`: `OBSERVE`
- `runtime_observe_reason`: thread상 manual case, runtime exact row는 후속 보강 필요
- `blocked_by`: pending
- `action_none_reason`: pending
- `probe_scene_id`: pending
- `consumer_check_stage`: pending
- `consumer_check_display_ready`: pending
- `entry_ready`: pending
- `current_status`: `debatable`
- `why_must_show`: 사용자가 직접 반복적으로 지적한 manual case라 screenshot 기준 carry-over 대상

평가:

- recent automatic mapping만으로는 exact row를 아직 못 붙였다
- 하지만 사용자 관찰 기반으로는 반드시 S1에 남겨야 하는 수동 케이스다

---

## Good / Missing / Debatable Summary

### good

- S1-01 BTC lower rebound probe
- S1-02 NAS lower rebound probe
- S1-03 XAU middle anchor observe

### missing

- S1-04 XAU upper reject + energy soft block hidden

### debatable

- S1-05 NAS lower rebound confirm + energy soft block hidden
- S1-06 BTC upper reject manual carry-over

---

## Contract Candidate

S1을 기준으로 다음 contract candidate를 S4에 넘긴다.

### Candidate A

- `upper_reject_probe_observe`
- `blocked_by=energy_soft_block`
- `probe_scene_id=xau_upper_sell_probe`

질문:

- 이런 row는 진입은 막더라도
- 최소 `OBSERVE/display=true`는 남길 것인가

### Candidate B

- `lower_rebound_confirm`
- `blocked_by=energy_soft_block`

질문:

- confirm family는 blocked여도 약한 observe는 남길 것인가
- 아니면 hidden 유지할 것인가

### Candidate C

- `middle_sr_anchor_required_observe`

질문:

- must-show middle anchor observe의 최소 조건을 무엇으로 볼 것인가
- XAU에서 살아 있는 기준을 BTC/NAS로 일부 확장할 것인가

### Candidate D

- manual carry-over upper reject family

질문:

- screenshot상 upper reject인데 runtime이 default-side conflict로 숨길 때
- 최소 watch를 남길지 여부를 어떤 조건으로 열 것인가

---

## S1 결론

S1 기준 현재 그림은 아래와 같다.

- `lower rebound family`
  - must-show 자체는 대부분 충족
  - 문제는 오히려 너무 강하게 남는 것
- `middle anchor family`
  - XAU에서 must-show가 잘 살아 있음
- `upper reject family`
  - XAU에서 blocked hidden으로 너무 쉽게 사라지는 case가 있다
  - 이것이 현재 가장 명확한 must-show missing 후보

즉 S1은 아래를 확정한다.

1. must-show 핵심 missing family는 `XAU upper reject blocked-hidden`
2. `BTC/NAS lower rebound`는 must-show 문제보다 leakage 문제에 더 가깝다
3. screenshot/manual carry-over case는 다음 단계에서도 계속 참조해야 한다

---

## 다음 단계

1. `S2 must-hide scene casebook`
  - BTC/NAS leakage 정리
2. `S3 visually similar scene alignment audit`
  - BTC/NAS vs XAU divergence 정리
3. `S4 consumer_check_state contract refinement`
  - S1/S2/S3 결과를 contract로 반영
