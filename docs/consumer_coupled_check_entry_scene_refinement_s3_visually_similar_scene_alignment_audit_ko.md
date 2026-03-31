# Consumer-Coupled Check/Entry Scene Refinement
## S3. Visually Similar Scene Alignment Audit

### 기준

이번 audit은 아래 입력을 기준으로 정리했다.

- 사용자 screenshot에서 반복적으로 지적한 “비슷해 보이는데 다르게 읽히는 장면”
- `entry_decisions.csv` recent row
- `runtime_status.json` latest state

S3의 목적은
`같아 보여서 통일해야 하는 장면`
과
`실제로는 다르게 읽는 게 맞는 장면`
을 구분하는 것이다.

---

### S3 핵심 결론

현재 visually similar scene의 핵심은 아래처럼 정리된다.

1. `BTC lower structural observe`와 `NAS lower blocked confirm`
- 차트상 둘 다 하락 말단 하단 rebound처럼 보일 수 있다
- 하지만 하나는 `OBSERVE/display=true`, 하나는 `BLOCKED/display=false`
- 이 차이는 완전히 intentional이라고 보기 어렵다
- `partial alignment` 후보다

2. `BTC/NAS lower family`와 `XAU upper conflict / upper reject family`
- 사용자는 비슷한 말단 장면으로 읽을 수 있지만,
  내부 context는 `BELOW+LOWER_EDGE` vs `UPPER+UPPER_EDGE/MID`로 크게 다르다
- 즉 이 차이는 상당 부분 intentional divergence다

3. `XAU middle anchor observe`와 `BTC lower structural observe`
- 둘 다 weak structural observe라는 점에서는 유사하다
- 다만 context는 다르고 symbol temperament도 다르다
- stage는 비슷하게 맞출 수 있지만 family 자체를 통일하긴 어렵다
- `partial alignment` 후보다

4. `XAU upper_reject_probe_observe`와 `XAU upper_reject_confirm`
- 같은 upper reject family 안에서도 하나는 `PROBE/display=true`, 하나는 `PROBE/display=false`
- 이건 cross-symbol 차이보다 `rule divergence`에 가깝다
- S4에서 blocked confirm을 weak observe로 남길지 판단해야 한다

---

## Cluster Summary

### Cluster 1. lower rebound end-of-drop

관련 대표 row:

- `BTCUSD`
  - `outer_band_reversal_support_required_observe`
  - `outer_band_guard`
  - `probe_not_promoted`
  - `OBSERVE`
  - `display=true`
  - `display_score=0.75`
  - `box_state=BELOW`, `bb_state=LOWER_EDGE`
- `NAS100`
  - `lower_rebound_confirm`
  - `energy_soft_block`
  - `execution_soft_blocked`
  - `BLOCKED`
  - `display=false`
  - `display_score=0.0`
  - `box_state=BELOW`, `bb_state=LOWER_EDGE`

핵심:

- 차트 체감상으론 둘 다 하락 말단 하단 rebound처럼 읽힌다
- 그런데 BTC는 weak buy observe가 남고
- NAS는 blocked confirm으로 완전히 사라진다

현재 분류:

- `partial alignment`

이유:

- context는 거의 동일하다
- divergence 핵심은
  - `rule divergence`
  - `symbol temperament divergence`
에 가깝다

권고:

- 같은 family 내부에서
  - BTC를 조금 더 눌러서
  - NAS와 display band를 가깝게 맞추거나
- 반대로 NAS blocked confirm을 아주 약한 observe로 남길지 검토

완전 통일보다
`display/stage 수준 partial alignment`
가 맞다.

---

### Cluster 2. lower family vs upper conflict family

관련 대표 row:

- `BTCUSD`
  - `outer_band_reversal_support_required_observe`
  - `OBSERVE`, `BUY`, `display=true`
  - `BELOW + LOWER_EDGE`
- `XAUUSD`
  - `conflict_box_upper_bb20_lower_upper_dominant_observe`
  - `display=false`
  - `UPPER + MID`
- `XAUUSD` latest
  - `upper_reject_confirm`
  - `forecast_guard`
  - `observe_state_wait`
  - `PROBE`, `SELL`, `display=false`
  - `UPPER + UPPER_EDGE`

핵심:

- 사용자 체감상 말단 장면이 유사해 보여도
- 내부 context는 명백히 다르다

현재 분류:

- `intentional divergence`

이유:

- divergence axis가 `context divergence`에 강하게 걸린다
- `BELOW / LOWER_EDGE` vs `UPPER / UPPER_EDGE or MID`는
  scene family를 실제로 다르게 읽는 게 맞다

권고:

- 이 cluster는 억지로 같은 side/family로 맞추지 않는다
- 대신 XAU 쪽 hidden/weak observe 정책만 별도 조정한다

즉 이 cluster는
`scene family alignment 대상이 아니라 display policy calibration 대상`
이다.

---

### Cluster 3. structural observe family

관련 대표 row:

- `BTCUSD`
  - `outer_band_reversal_support_required_observe`
  - `OBSERVE`
  - `display=true`
  - `score=0.75`, `repeat=1`
- `XAUUSD`
  - `middle_sr_anchor_required_observe`
  - `OBSERVE`
  - `display=true`
  - `score=0.75`, `repeat=1`

핵심:

- 구체 family는 다르지만
- 둘 다 `must-show weak structural observe`라는 점에서는 유사하다

현재 분류:

- `partial alignment`

이유:

- family는 다르지만
- display band는 이미 잘 정렬돼 있다
- 남은 차이는 repetition/cadence다

권고:

- family는 분리 유지
- 대신 `weak structural observe = OBSERVE 1개`
  라는 display translation contract는 공통으로 유지

즉 이 cluster는
`scene family alignment`가 아니라
`display translation alignment 성공 사례`
로 볼 수 있다.

---

### Cluster 4. upper reject family 내부 divergence

관련 대표 row:

- `XAUUSD upper_reject_probe_observe`
  - `forecast_guard`
  - `probe_not_promoted`
  - `PROBE`
  - `display=true`
  - `score=0.82`, `repeat=2`
- `XAUUSD upper_reject_confirm`
  - `forecast_guard`
  - `observe_state_wait`
  - `PROBE`
  - `display=false`
  - `score=0.0`, `repeat=0`

핵심:

- 같은 upper reject family인데
- probe observe는 보이고
- confirm은 hidden된다

현재 분류:

- `accidental divergence`

이유:

- context divergence보다 `rule divergence`가 더 크다
- 사용자가 보기엔 같은 family continuity인데
  표시 정책이 너무 급격히 갈린다

권고:

- S4에서
  `upper_reject_confirm + forecast_guard + observe_state_wait`
  를 완전 hidden 대신 약한 observe로 남길지 검토

즉 이 cluster는
S4 contract refinement의 직접 후보다.

---

## Pair Table

### Pair S3-01

- `case_id`: S3-01
- `cluster_name`: lower rebound end-of-drop
- `left_symbol`: BTCUSD
- `right_symbol`: NAS100
- `chart_similarity_summary`: 둘 다 하락 말단 하단 반등 시도처럼 보임
- `left_observe_reason`: `outer_band_reversal_support_required_observe`
- `right_observe_reason`: `lower_rebound_confirm`
- `left_blocked_by`: `outer_band_guard`
- `right_blocked_by`: `energy_soft_block`
- `left_action_none_reason`: `probe_not_promoted`
- `right_action_none_reason`: `execution_soft_blocked`
- `left_probe_scene_id`: `btc_lower_buy_conservative_probe`
- `right_probe_scene_id`: `""`
- `left_stage`: `OBSERVE`
- `right_stage`: `BLOCKED`
- `left_display`: `true`
- `right_display`: `false`
- `left_box_bb_context`: `BELOW + LOWER_EDGE`
- `right_box_bb_context`: `BELOW + LOWER_EDGE`
- `divergence_axis`: `rule divergence`, `symbol temperament divergence`
- `alignment_recommendation`: `align display only`

### Pair S3-02

- `case_id`: S3-02
- `cluster_name`: lower family vs upper conflict family
- `left_symbol`: BTCUSD
- `right_symbol`: XAUUSD
- `chart_similarity_summary`: 사용자에겐 모두 말단 장면처럼 보일 수 있음
- `left_observe_reason`: `outer_band_reversal_support_required_observe`
- `right_observe_reason`: `conflict_box_upper_bb20_lower_upper_dominant_observe`
- `left_blocked_by`: `outer_band_guard`
- `right_blocked_by`: `""`
- `left_action_none_reason`: `probe_not_promoted`
- `right_action_none_reason`: `observe_state_wait`
- `left_probe_scene_id`: `btc_lower_buy_conservative_probe`
- `right_probe_scene_id`: `""`
- `left_stage`: `OBSERVE`
- `right_stage`: `""`
- `left_display`: `true`
- `right_display`: `false`
- `left_box_bb_context`: `BELOW + LOWER_EDGE`
- `right_box_bb_context`: `UPPER + MID`
- `divergence_axis`: `context divergence`
- `alignment_recommendation`: `keep separated`

### Pair S3-03

- `case_id`: S3-03
- `cluster_name`: structural observe family
- `left_symbol`: BTCUSD
- `right_symbol`: XAUUSD
- `chart_similarity_summary`: 둘 다 구조적 약한 체크 family
- `left_observe_reason`: `outer_band_reversal_support_required_observe`
- `right_observe_reason`: `middle_sr_anchor_required_observe`
- `left_blocked_by`: `outer_band_guard`
- `right_blocked_by`: `middle_sr_anchor_guard`
- `left_action_none_reason`: `probe_not_promoted`
- `right_action_none_reason`: `observe_state_wait`
- `left_probe_scene_id`: `btc_lower_buy_conservative_probe`
- `right_probe_scene_id`: `""`
- `left_stage`: `OBSERVE`
- `right_stage`: `OBSERVE`
- `left_display`: `true`
- `right_display`: `true`
- `left_box_bb_context`: `BELOW + LOWER_EDGE`
- `right_box_bb_context`: `UPPER + MID`
- `divergence_axis`: `context divergence`, `display translation alignment`
- `alignment_recommendation`: `align display only`

### Pair S3-04

- `case_id`: S3-04
- `cluster_name`: upper reject family internal divergence
- `left_symbol`: XAUUSD
- `right_symbol`: XAUUSD
- `chart_similarity_summary`: 같은 upper reject family 연속 장면
- `left_observe_reason`: `upper_reject_probe_observe`
- `right_observe_reason`: `upper_reject_confirm`
- `left_blocked_by`: `forecast_guard`
- `right_blocked_by`: `forecast_guard`
- `left_action_none_reason`: `probe_not_promoted`
- `right_action_none_reason`: `observe_state_wait`
- `left_probe_scene_id`: `xau_upper_sell_probe`
- `right_probe_scene_id`: `""`
- `left_stage`: `PROBE`
- `right_stage`: `PROBE`
- `left_display`: `true`
- `right_display`: `false`
- `left_box_bb_context`: `UPPER + UPPER_EDGE`
- `right_box_bb_context`: `UPPER + UPPER_EDGE`
- `divergence_axis`: `rule divergence`, `display translation divergence`
- `alignment_recommendation`: `align display only`

---

## Intentional / Accidental / Partial Summary

### intentional divergence

- `S3-02`

설명:

- BTC lower family와 XAU upper conflict family는
  chart 체감상 혼동될 수 있어도
  context 자체가 달라서 분리 유지가 맞다

### accidental divergence

- `S3-04`

설명:

- 같은 upper reject family 내부에서
  probe observe는 보이고 confirm은 hidden되는 건
  과도한 rule divergence 가능성이 크다

### partial alignment

- `S3-01`
- `S3-03`

설명:

- family 자체를 완전 통일할 필요는 없지만
- stage/display 수준에서는 더 비슷하게 맞출 수 있다

---

## Alignment Contract Candidate

### Candidate A

- `BTC lower structural observe`
- `NAS blocked lower confirm`

질문:

- 같은 lower rebound end-of-drop cluster에서
  display band를 조금 더 가깝게 맞출 것인가

### Candidate B

- `XAU upper_reject_probe_observe`
- `XAU upper_reject_confirm`

질문:

- 같은 upper reject family 내에서
  confirm hidden을 약한 observe로 끌어올릴 것인가

### Candidate C

- weak structural observe family

질문:

- `OBSERVE + score 0.75 + repeat 1`을
  공통 weak structural display contract로 유지할 것인가

---

## S3 결론

S3 기준 현재 그림은 아래와 같다.

1. `BTC/NAS` lower family
- 완전 통일은 아니어도 display/stage partial alignment 대상

2. `BTC/NAS` vs `XAU conflict`
- 의도된 divergence로 보는 게 맞음

3. `XAU upper reject family 내부`
- accidental divergence 가능성이 높음
- S4에서 직접 다뤄야 함

즉 S3는 아래를 확정한다.

- 무엇을 통일해야 하는지
- 무엇은 일부만 정렬해야 하는지
- 무엇은 그대로 분리 유지해야 하는지

를 contract 후보 수준으로 정리했다.

---

## 다음 단계

1. `S4 consumer_check_state contract refinement`
2. `S5 symbol balance tuning`

즉 이제부터는 casebook을 실제 contract로 내리는 단계다.
