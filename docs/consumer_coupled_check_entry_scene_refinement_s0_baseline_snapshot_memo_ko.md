# Consumer-Coupled Check/Entry Scene Refinement
## S0. Baseline Snapshot Memo

### Baseline 시각

- runtime 기준: `2026-03-27 21:20:20 KST`
- chart distribution / rollout 기준: `2026-03-27 21:20:30 KST`
- recent tail row 확인 기준: `2026-03-27 21:21 KST` 부근

이번 memo는 아래 입력을 기준으로 작성했다.

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`
- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`

---

### 1. 전체 baseline 요약

현재 baseline은 다음처럼 읽힌다.

- `consumer-coupled check / entry` 연결 자체는 살아 있다
- `wrong_ready_count = 0`이라서 예전의 “blocked인데 READY처럼 보이던 버그”는 baseline상 정리된 상태다
- 하지만 scene refinement 관점에서는 아직 편향이 뚜렷하다
  - `BTCUSD`: buy-side structural probe가 너무 넓게 남아 있다
  - `NAS100`: BTC보다 덜하지만 여전히 buy-side probe가 강하다
  - `XAUUSD`: 반대로 conflict/observe_wait 계열이 많아 hidden 비중이 높다

즉 현재 baseline의 핵심 문제는:

- `BTC/NAS는 leakage 쪽`
- `XAU는 suppression 쪽`

으로 나뉜다.

---

### 2. Recent 200 기준 stage snapshot

`runtime_status.json` recent summary 기준:

- `PROBE = 101`
- `OBSERVE = 58`
- `BLOCKED = 1`
- `NONE = 40`

display 기준:

- `display_ready_true = 146`
- `display_ready_false = 54`
- `entry_ready_true = 0`
- `entry_ready_false = 200`
- `wrong_ready_count = 0`

blocked reason 상위:

- `forecast_guard = 90`
- `observe_state_wait = 40`
- `outer_band_guard = 34`
- `middle_sr_anchor_guard = 25`
- `probe_promotion_gate = 11`

이 baseline은 현재 시스템이
`진입 직전 READY`보다는 `PROBE / OBSERVE / BLOCKED` 중심의 pre-entry 차트 체계에 머물고 있다는 뜻이다.

---

### 3. Symbol별 recent baseline

#### BTCUSD

recent summary:

- `rows = 66`
- `PROBE = 42`
- `OBSERVE = 24`
- `display_ready_true = 66`
- `display_ready_false = 0`

최근 대표 row:

- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = barrier_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `box_state = BELOW`
- `bb_state = LOWER_EDGE`
- `consumer_check_stage = PROBE`
- `consumer_check_side = BUY`
- `display_ready = true`
- `display_score = 0.86`
- `display_repeat_count = 2`

chart window 16 기준:

- `BUY_WAIT = 12`
- `BUY_PROBE = 3`
- `WAIT = 1`
- `buy_presence_ratio = 0.9375`

해석:

- BTC는 현재 baseline에서 `하단 반등 buy probe`를 매우 넓게 살린 상태다
- 사용자가 보기엔 “계속 내려가는데 buy 가능성 표기가 너무 남는다”는 체감이 생기기 쉬운 구조다
- 즉 BTC는 현재 `must-hide leakage` 후보가 가장 강하다

#### NAS100

recent summary:

- `rows = 67`
- `PROBE = 57`
- `OBSERVE = 10`
- `display_ready_true = 54`
- `display_ready_false = 13`

최근 대표 row:

- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = barrier_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `box_state = BELOW`
- `bb_state = LOWER_EDGE`
- `consumer_check_stage = PROBE`
- `consumer_check_side = BUY`
- `display_ready = true`
- `display_score = 0.86`
- `display_repeat_count = 2`

chart window 16 기준:

- `BUY_WAIT = 8`
- `BUY_PROBE = 4`
- `WAIT = 4`
- `buy_presence_ratio = 0.75`

해석:

- NAS도 현재 baseline에선 BTC와 같은 방향으로 읽히고 있다
- 다만 BTC보다 neutral `WAIT`가 더 섞여 있어서 완전한 leakage 과다는 아니다
- 그래도 `lower_rebound_probe_observe + barrier_guard + probe_not_promoted`가 반복된다는 점에서 S2 must-hide 검토 대상이다

#### XAUUSD

recent summary:

- `rows = 67`
- `PROBE = 2`
- `OBSERVE = 24`
- `BLOCKED = 1`
- `NONE = 40`
- `display_ready_true = 26`
- `display_ready_false = 41`

최근 대표 row:

- `observe_reason = conflict_box_upper_bb20_lower_lower_dominant_observe`
- `blocked_by = ""`
- `action_none_reason = observe_state_wait`
- `probe_scene_id = ""`
- `box_state = UPPER`
- `bb_state = UNKNOWN`
- `consumer_check_stage = ""`
- `consumer_check_side = ""`
- `display_ready = false`
- `display_score = 0.0`
- `display_repeat_count = 0`

chart window 16 기준:

- `BUY_WAIT = 2`
- `SELL_WAIT = 1`
- `BUY_PROBE = 4`
- `SELL_PROBE = 2`
- `WAIT = 7`
- `buy_presence_ratio = 0.375`
- `sell_presence_ratio = 0.1875`
- `neutral_ratio = 0.4375`

해석:

- XAU는 BTC/NAS와 반대로 `conflict + observe_state_wait`가 매우 넓다
- 즉 “비슷한 하락 말단처럼 보이는데 XAU만 숨겨진다”는 사용자의 체감과 연결된다
- XAU는 현재 `must-show missing`보다 먼저 `visually similar divergence` 핵심 축으로 봐야 한다

---

### 4. Display ladder snapshot

현재 latest row 기준 ladder는 아래처럼 보인다.

#### BTC / NAS

- `stage = PROBE`
- `display_score = 0.86`
- `display_repeat_count = 2`

즉 현재 ladder 규칙상

- `0.80 ~ 0.89` 구간의 2중 체크

로 실제로 내려오고 있다.

#### XAU

- `check_candidate = false`
- `display_score = 0.0`
- `display_repeat_count = 0`

즉 현재 ladder에서 XAU latest scene은

- 방향성 체크 자체를 만들지 않는 hidden scene

으로 읽히고 있다.

정리하면:

- ladder 자체는 동작 중이다
- 지금 문제는 ladder가 아니라
  - 어떤 scene을 `0.86 PROBE`로 살릴지
  - 어떤 scene을 `0.0 hidden`으로 보낼지
  를 정하는 upstream scene contract다

---

### 5. Must-show missing 후보

이번 baseline의 data-only recent scan에서는
`고신뢰 must-show missing` 후보가 충분히 모이지 않았다.

즉 최근 row만 보면:

- 현재는 “떠야 할 구조 observe가 전부 죽는다”보다는
- “BTC/NAS의 weak buy probe가 너무 넓게 남는다”가 더 두드러진다

이 말은 곧:

- S1 must-show scene casebook은
  - recent row 자동 추출만으로는 부족하고
  - 사용자가 실제 차트에서 표시한 screenshot/manual case를 같이 써야 한다

는 뜻이다.

현재 상태에서 기록할 수 있는 보수적 결론은:

- `must-show missing`은 이번 baseline에서 “강한 자동 후보 없음”
- 대신 S1에서 screenshot 기반 수동 casebook이 필요함

---

### 6. Must-hide leakage 후보

이번 baseline에서 가장 명확한 leakage는 아래다.

#### 후보 A. BTC lower rebound probe leakage

- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = barrier_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `display_ready = true`
- recent repeated count 다수

해석:

- 실제 진입은 안 되는데
- 하단 반등 buy 가능성 표기가 계속 남는 구조다
- 사용자가 “계속 내려가는데 buy 표기가 너무 많다”고 느끼는 직접 원인이다

#### 후보 B. NAS lower rebound probe leakage

- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = barrier_guard`
- `action_none_reason = probe_not_promoted`
- `probe_scene_id = nas_clean_confirm_probe`
- `display_ready = true`

해석:

- BTC와 같은 계열의 leakage지만
- NAS는 neutral `WAIT`가 일부 섞여 있어 BTC보다 조금 덜 심하다
- 그래도 S2에서 반드시 다뤄야 할 대표 후보다

#### 후보 C. structural observe leakage seed

- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `action_none_reason = probe_not_promoted`

이번 baseline에선 반복 수가 적지만,
S2에서 generic structural observe가 어디까지 살아야 하는지 판단할 때 seed로 쓸 수 있다.

---

### 7. Visually similar divergence seed

이번 baseline에서 가장 중요한 divergence seed는 아래다.

#### Seed 1. BTC vs NAS

- 둘 다 `BELOW + LOWER_EDGE`
- 둘 다 `lower_rebound_probe_observe`
- 둘 다 `BUY / PROBE / display=true`
- 차이는 scene label만
  - BTC: `btc_lower_buy_conservative_probe`
  - NAS: `nas_clean_confirm_probe`

해석:

- BTC와 NAS는 현재 거의 같은 family로 읽힌다
- 따라서 이 둘을 S3에서 먼저 같은 cluster로 묶고, leakage 보정 차이만 볼 수 있다

#### Seed 2. BTC/NAS vs XAU

- 사용자 체감상 비슷한 하락 말단처럼 보이는 장면이 존재한다
- 하지만 엔진은
  - BTC/NAS: `lower_rebound_probe_observe`
  - XAU: `conflict_box_upper_bb20_lower_*`
  로 갈라 읽는다

해석:

- 이게 지금 scene refinement의 핵심 축이다
- S3에서는 “XAU를 BTC/NAS 쪽으로 일부 정렬할지” 또는 “실제로 다르게 봐야 하는지”를 casebook으로 판단해야 한다

---

### 8. Chart rollout snapshot

`chart_flow_rollout_status_latest.json` 기준:

- `Stage A = advance`
- `Stage B = advance`
- `Stage C = advance`
- `Stage D = pending`
- `Stage E = hold`

hold 이유:

- `baseline-only comparison report unavailable`
- calibration targets:
  - `BTCUSD`
  - `NAS100`
  - `XAUUSD`

즉 scene refinement baseline 관점에서도
현재 세 심볼 모두 refinement 대상인 상태가 맞다.

---

### 9. S0 결론

이번 baseline에서 드러난 현재 위치는 아래와 같다.

1. `BTCUSD`
- 가장 강한 `must-hide leakage` 대상
- `lower_rebound_probe_observe`가 너무 넓게 보인다

2. `NAS100`
- BTC보다 덜하지만 같은 leakage family
- S2에서 같이 정리해야 한다

3. `XAUUSD`
- leakage보다 `divergence`가 핵심
- BTC/NAS와 비슷하게 보여도 내부에선 conflict hidden으로 읽힌다

4. `display ladder`
- 자체는 정상 동작
- 문제는 scene selection이지 ladder가 아니다

5. `must-show missing`
- 이번 data-only baseline에선 고신뢰 자동 후보가 충분하지 않다
- S1은 screenshot/manual casebook 기반으로 가야 한다

---

### 10. 다음 단계 우선순위

#### 다음 1순위: S1 must-show scene casebook

방향:

- recent row 자동 추출만으로는 부족하므로
- 사용자가 직접 표시한 차트 screenshot case를 baseline casebook에 반영

#### 다음 2순위: S2 must-hide scene casebook

대상:

- `BTC lower_rebound_probe_observe`
- `NAS lower_rebound_probe_observe`

#### 다음 3순위: S3 visually similar alignment audit

대상:

- `BTC/NAS lower rebound family`
- `XAU conflict_box_upper_bb20_lower_* family`

즉 S0 baseline은
“어디를 먼저 고쳐야 하는가”를 아래 순서로 고정한다.

- `must-show`: screenshot/manual 기반
- `must-hide`: BTC/NAS leakage 우선
- `alignment`: BTC/NAS vs XAU divergence 우선
