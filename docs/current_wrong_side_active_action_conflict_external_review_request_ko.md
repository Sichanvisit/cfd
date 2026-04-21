# Current Wrong-Side Active-Action Conflict External Review Request

## 목적

이 문서는 현재 runtime에서 반복 관측되는

- `old baseline active action`
- `directional continuation owner`

사이의 충돌을 외부 조언용으로 상세 정리한 요청서다.

핵심 질문은 단순하지 않다.

> 시스템이 반대 방향 힌트를 이미 보고 있는데도
> 왜 old baseline이 실행권을 계속 쥐는가?
> 그리고 이 문제를 `CL 운영층`보다 먼저 어떤 형태로 고쳐야 하는가?

## 왜 이 문제가 지금 가장 먼저인가

현재 전체 로드맵은 이미 많이 진행되었다.

- `PF0` 성능 baseline hold 완료
- `MF1 ~ MF16` 구현 완료
- `MF17` 구조 구현 완료
- `BTCUSD / NAS100 / XAUUSD initial_entry_surface` 3개가 모두 공통 signoff packet과 공통 activation contract에 올라와 있음

즉 원래 다음은

- manual signoff
- bounded activation
- CL orchestrator

로 가는 것이 자연스러웠다.

하지만 최근 runtime audit에서
`wrong-side active-action conflict`
가 반복적으로 확인되었다.

이 상태에서 signoff나 CL 운영층을 먼저 열면,
현재 잘못된 baseline active action을 더 체계적으로 운영하게 될 수 있다.

그래서 이 문제를 `P0 hotfix`로 승격해서 먼저 해결하려고 한다.

## 현재 문제를 한 줄로 요약

현재 시스템은 상승 continuation을 못 보는 것이 아니다.

- 같은 row에서 directional layer는 이미 `UP_PROBE / BUY`를 만든다
- 그런데 old baseline이 `SELL`을 이미 잡고 있으면,
  현재 bridge는 그 active baseline을 뒤집지 못한다

즉 문제는

- `센서 부재`

가 아니라

- `owner precedence + active-action conflict resolution 부재`

다.

## 최근 runtime에서 확인된 구체 사례

대표 사례:

- 시간: `2026-04-09T20:36:48`
- symbol: `XAUUSD`
- 실제 실행:
  - `action = SELL`
  - `outcome = entered`
  - `entry_candidate_action_source = baseline_score`
- baseline scene:
  - `setup_id = range_upper_reversal_sell`
  - `setup_reason = shadow_upper_break_fail_confirm`
  - `bb_state = UPPER_EDGE`
- 같은 row의 directional layer:
  - `countertrend_action_state = UP_PROBE`
  - `countertrend_directional_candidate_action = BUY`
  - `countertrend_directional_state_reason = up_probe::anti_short_strong_plus_pro_up_supportive`
  - `countertrend_directional_up_bias_score = 0.912`

즉 같은 row 안에서

- baseline은 `SELL`
- directional은 `BUY`

를 동시에 말하고 있었는데,
실제 실행권은 baseline이 가져간다.

## 최근 conflict 분포

최근 runtime slice 점검 기준:

- recent 2500 rows:
  - `XAUUSD SELL vs directional BUY conflict = 310`
- recent 5000 XAU upper-reversal sell slice:
  - `range_upper_reversal_sell rows = 549`
  - `countertrend_action_state = UP_PROBE 324 / DO_NOTHING 225`
  - `actual outcome = entered 53 / skipped 483 / wait 13`
  - blocker top:
    - `clustered_entry_price_zone = 473`
    - empty blocker = `53`

중요한 점:

- repeated-entry blocker가 일부를 막긴 한다
- 하지만 이건 방향 교정이 아니라 spacing guard일 뿐이라,
  조건이 열리면 wrong-side `SELL`은 여전히 들어갈 수 있다

## 핵심 원인 가설

### 1. Old baseline reversal-sell family가 너무 강하다

관련 경로:

- [consumer_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_contract.py)
- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

현재 구조는

- `upper_reject_sell`
- `mid_lose_sell`

를 `range_upper_reversal_sell`로 강하게 묶는다.

즉 XAU가 위쪽에서 조금만 흔들려도
`상단 반전 숏`
으로 읽는 오래된 baseline 성향이 아직 남아 있다.

### 2. Directional layer는 살아 있지만 advisory다

관련 경로:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

현재는 directional state machine이

- `UP_WATCH`
- `UP_PROBE`
- `DOWN_WATCH`
- `DOWN_PROBE`

를 실제로 만든다.

하지만 이건 현재

- log/bridge candidate
- 보조 owner

에 가깝고,
active baseline을 강하게 veto하지 못한다.

### 3. Candidate bridge가 아직 baseline_no_action rescue에만 머문다

관련 경로:

- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)

현재 bridge는

- baseline action이 비어 있을 때만 candidate를 골라준다

즉

- `baseline SELL`
- `directional BUY`

처럼 이미 baseline이 action을 잡은 active conflict는
bridge가 다루지 못한다.

### 4. Current validation도 실제 문제 장면을 완전히 잡지 못한다

관련 경로:

- [countertrend_materialization_check.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/countertrend_materialization_check.py)
- [countertrend_down_bootstrap_validation.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/countertrend_down_bootstrap_validation.py)

기존 validation은 주로

- `range_lower_reversal_buy`
- `trend_pullback_buy`

쪽을 target family로 잡는다.

그래서 실제로 지금 문제가 되는

- `range_upper_reversal_sell -> UP_PROBE conflict`

는 검증 타깃 밖에 있는 부분이 있다.

## 현재 내부 설계 업데이트

이번 문제는 단순 가드 추가가 아니라,
`execution precedence layer`를 한 층 추가하는 것으로 보고 있다.

즉 구조를 아래처럼 본다.

```text
[baseline owner]
[directional owner]
[breakout owner]
[state25 owner]
        ↓
[conflict resolver / precedence layer]
        ↓
[final executable action]
```

핵심은:

- 좋은 판단을 하나 더 만드는 것이 아니라
- 이미 존재하는 owner들 사이에서 누가 실행권을 가질지 정하는 것

또한 첫 단계는 `override`보다 `downgrade`가 우선이라고 본다.

권장 초기 action state:

- `KEEP`
- `WATCH`
- `PROBE`
- `OVERRIDE`

초기 P0에서는

- wrong-side baseline action을 먼저 `WATCH/PROBE/WAIT`로 강등
- 그 다음 opposite directional candidate를 bounded하게 승격

순서가 더 안전하다고 본다.

## 우리가 현재 생각하는 우선 수정 방향

### P0A. Wrong-Side Active-Action Conflict Audit

필요한 이유:

- 현재 conflict가 어느 symbol/setup/setup_reason/action pair에 집중되는지
- owner/source가 어떻게 갈리는지

를 latest artifact로 고정해야 한다.

### P0B. Active-Action Conflict Guard

핵심 아이디어:

- `baseline SELL`
- `directional BUY / UP_PROBE or UP_ENTER`
- 높은 `up_bias`

면 `SELL`을 그냥 실행하지 말고

- `WAIT`
- 또는 `WATCH/PROBE only`

로 강등한다.

대칭 규칙:

- `baseline BUY`
- `directional SELL / DOWN_PROBE or DOWN_ENTER`

도 같은 방식으로 강등한다.

외부 조언이 듣고 싶은 세부 포인트:

- 어느 구간까지는 `KEEP`
- 어느 구간부터 `WATCH`
- 어느 구간부터 `PROBE`
- 어느 구간에서만 bounded `OVERRIDE`

가 맞는지

### P0C. Baseline-vs-Directional Bridge Conflict Resolution

핵심 아이디어:

현재 bridge는 `baseline_no_action`일 때만 후보를 고른다.

이를

- `baseline active-action conflict`

도 다루는 bridge로 확장해야 한다.

즉 bridge는 앞으로

- no-action rescue
- active-action conflict resolution

두 모드를 모두 가져야 한다.

추가로 내부적으로는 아래 중간 상태를 생각하고 있다.

- `baseline_action_conflict`
- `conflict_guard_downgrade`
- `directional_override_candidate`

즉 bridge는 단순 candidate picker가 아니라
`execution precedence resolver`의 일부가 되어야 한다.

### P0D. Wrong-Side Conflict Harvest

핵심 아이디어:

이 문제를 단순 runtime guard에서 끝내지 않고,
다음 rebuild/eval에 들어갈 failure label로 자동 수집해야 한다.

예:

- `wrong_side_sell_pressure`
- `wrong_side_buy_pressure`
- `missed_up_continuation`
- `missed_down_continuation`

추가 context label 후보:

- `false_down_pressure_in_uptrend`
- `false_up_pressure_in_downtrend`

현재 내부 판단은 이 라벨들을 `initial_entry regret`보다는

- `follow_through_negative`
- `directional_conflict_failure`

쪽에 두는 것이 더 맞다는 쪽이다.

### P0E. XAU Upper-Reversal Conflict Validation

핵심 아이디어:

기존 lower-reversal 중심 validation과 별도로,
실제 문제 장면인 upper-reversal sell family를 직접 validation 범위에 포함한다.

## 외부 조언이 특히 필요한 질문

### 질문 1. Active baseline과 directional owner가 충돌할 때, 가장 안전한 first guard는 무엇인가

예:

- 바로 `WAIT`로 강등
- `WATCH only`
- `PROBE only`
- 일정 bias threshold를 넘을 때만 guard

중 어떤 형태가 가장 안전하고 실용적인가?

### 질문 2. Bridge를 no-action rescue에서 active-action conflict resolution으로 확장할 때 어떤 state machine이 가장 좋은가

예:

- `baseline_action_conflict`
- `conflict_guard_downgrade`
- `directional_override_candidate`

같은 중간 상태가 필요한가?

### 질문 3. XAU upper-reversal sell family에서 어떤 구조 증거를 더 넣어야 `UP_PROBE`가 진짜 상승 continuation인지 더 잘 구분할 수 있는가

현재는 일부 `forecast_wait_bias`, `belief_fragile_thesis`, `barrier_relief_watch`가
`anti_short + pro_up`로 변환된다.

이게 너무 느슨할 가능성이 있다.

그래서:

- higher high / higher low
- reclaim success/failure
- upside continuation persistence
- bars since failed reject

같은 실제 구조 증거를 더 넣어야 하는지 조언이 필요하다.

현재 내부 판단은
`anti_short` 보강보다 `pro_up structure` 강화가 더 중요하다는 쪽이다.

### 질문 4. Wrong-side conflict harvest를 어떤 label 체계로 묶는 것이 좋은가

예:

- `wrong_side_sell_pressure`
- `missed_up_continuation`
- `false_down_pressure_in_uptrend`

이런 failure label을

- `initial_entry regret`
- `follow_through negative`
- `directional conflict failure`

중 어디에 두는 것이 가장 좋은가?

### 질문 5. 이 P0 트랙을 `MF17 signoff / CL1 orchestrator`보다 먼저 두는 판단이 맞는가

현재 내부 판단은

- `P0 runtime correction`
- `MF17 manual signoff`
- `bounded activation`
- `CL1~CL9`

순서가 맞다는 것이다.

이 순서가 실용적인지 조언이 필요하다.

## 현재 내부 제안 순서

1. `P0A Wrong-Side Active-Action Conflict Audit`
2. `P0B Active-Action Conflict Guard`
3. `P0C Baseline-vs-Directional Bridge Conflict Resolution`
4. `P0D Wrong-Side Conflict Harvest`
5. `P0E XAU Upper-Reversal Conflict Validation`
6. 그 다음 `MF17 manual signoff`
7. 그 다음 `bounded activation`
8. 그 다음 `CL1 Continuous Learning Orchestrator`

## 아주 짧은 복붙용 질문

현재 CFD 자동매매 시스템에서 XAU recent runtime row를 보면, 같은 row 안에 `baseline_score = SELL`이 실제 실행권을 가지고 있는데 directional layer는 `UP_PROBE / BUY`와 높은 `up_bias_score`를 동시에 남기고 있습니다. 최근 conflict row는 거의 전부 `XAUUSD range_upper_reversal_sell` family에 집중되어 있고, 현재 candidate bridge는 `baseline_no_action`일 때만 후보를 선택해서 active baseline conflict를 해결하지 못합니다. 이 문제를 `CL 운영층`보다 먼저 `P0 hotfix`로 다뤄서, `baseline active-action conflict guard -> bridge conflict resolution -> wrong-side harvest -> upper-reversal validation` 순서로 가려는데, 이 우선순위와 상태기계 설계, 그리고 필요한 구조 증거/probe/harvest 라벨 체계에 대해 조언해 주세요.
