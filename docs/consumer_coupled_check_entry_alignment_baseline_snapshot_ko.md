# Consumer-Coupled Check / Entry Alignment Baseline Snapshot

## 1. 목적

`consumer_check_state_v1`를 붙이기 전, 현재 대표 row가 어떤 식으로 `체크는 애매하고 entry는 안 되는 상태`를 남기는지 baseline으로 고정한다.

기준 시각:

- 2026-03-26 23:59 KST 부근 latest entry rows

입력:

- `data/trades/entry_decisions.csv`

## 2. 대표 row

### 2.1 NAS100

- `time = 2026-03-26T23:59:41`
- `observe_side = BUY`
- `observe_reason = lower_rebound_confirm`
- `blocked_by = forecast_guard`
- `action_none_reason = observe_state_wait`
- `core_reason = core_shadow_observe_wait`
- `core_intended_direction = BUY`
- `probe_scene_id = ""`
- `probe_plan_reason = probe_candidate_inactive`
- `consumer_guard_result = SEMANTIC_NON_ACTION`

해석:

- semantic chain은 BUY 방향을 보고 있다
- 하지만 chart/entry 모두에서 이 방향이 충분히 canonical pre-entry state로 surface되지 않는다

### 2.2 BTCUSD

- `time = 2026-03-26T23:59:44`
- `observe_side = BUY`
- `observe_reason = lower_rebound_probe_observe`
- `blocked_by = forecast_guard`
- `action_none_reason = probe_not_promoted`
- `core_reason = core_shadow_observe_wait`
- `core_intended_direction = BUY`
- `probe_scene_id = btc_lower_buy_conservative_probe`
- `probe_plan_reason = probe_barrier_blocked`
- `probe_candidate_support = 1.0480`
- `probe_pair_gap = 0.1944`
- `consumer_guard_result = SEMANTIC_NON_ACTION`

해석:

- 이 row는 명백히 directional probe 후보다
- 그런데 현재 row surface만 보면 chart와 entry가 같은 canonical pre-entry state를 공유하지 않는다

### 2.3 XAUUSD

- `time = 2026-03-26T23:59:43`
- `observe_side = SELL`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = ""`
- `action_none_reason = probe_not_promoted`
- `core_reason = core_shadow_observe_wait`
- `core_intended_direction = SELL`
- `probe_scene_id = xau_upper_sell_probe`
- `probe_plan_reason = probe_forecast_not_ready`
- `probe_candidate_support = 0.1569`
- `probe_pair_gap = 0.1569`
- `consumer_guard_result = SEMANTIC_NON_ACTION`

해석:

- SELL probe 의미는 살아 있다
- 다만 `entry ready`는 아니고 `forecast not ready` 상태다
- 이 차이를 chart와 entry가 같은 payload로 읽는 구조가 필요하다

## 3. baseline 결론

현재 공통 문제는 다음으로 요약된다.

- `core_intended_direction`는 이미 있다
- `observe_reason / probe_scene_id / probe_plan_reason`도 있다
- 하지만 차트가 직접 소비할 canonical `pre-entry consumer state`는 없다

그래서 다음 구현의 핵심은:

- `consumer_check_state_v1`

를 entry_service에서 canonical surface로 만들고,

- chart는 `check_display_ready`
- entry는 `entry_ready`

를 같은 payload에서 읽게 만드는 것이다.
