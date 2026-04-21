# SA5.7 Continuation-Hold RUNNER_CHECK Time-Decay Refinement

## 목적

- `SA5.6` 이후에도 남아 있는 `time_decay_risk` 과잉 선택을 한 번 더 줄인다
- 특히 `continuation_hold_surface + RUNNER_CHECK` 내부에서 아래 3가지를 분리한다
  - `active_flat_profit`
  - `runner_secured_continuation`
  - `true late stall`
- `time_decay_risk`는 "늦게 멈춘 관리 row"에만 남기고, healthy runner/secured runner는 suppress한다

## 현재 상태

`SA5.6` 이후 최신 audit 기준:

- `time_decay_risk` disagreement row: `300`
- 주요 top slice:
  - `NAS100 + continuation_hold_surface + RUNNER_CHECK = 243`
  - `XAUUSD + continuation_hold_surface + RUNNER_CHECK = 24`
  - `BTCUSD + continuation_hold_surface + RUNNER_CHECK = 17`

즉 큰 문제는 더 이상 `protective_exit_surface`가 아니라,
`continuation_hold_surface` 안에서 late stall과 runner family가 잘 안 갈리는 점이다.

## 해석

현재 남아 있는 `time_decay_risk`는 대체로 세 부류다.

### 1. runner_secured_continuation

- `checkpoint_rule_family_hint = runner_secured_continuation`
- 또는 `exit_stage_family = runner`
- 또는 `runner_secured = true`

이 부류는 이미 일부 이익을 잠갔고, 장면상 `time_decay`보다 `runner_hold / trend_exhaustion` 쪽이 더 가깝다.

### 2. active_flat_profit

- `checkpoint_rule_family_hint = active_flat_profit`
- `unrealized_pnl_state = FLAT`
- `current_profit ~= 0`

이 부류는 일부가 true late stall이지만, 일부는 단지 flat한 중간 관리 row일 수 있다.
그래서 전부 `time_decay_risk`로 보내면 과잉 태깅이 된다.

### 3. true late stall

이 부류만 `time_decay_risk`를 유지한다.

최소 특징:

- late checkpoint (`LATE_TREND_CHECK` or `RUNNER_CHECK`)
- `continuation_hold_surface`
- `unrealized_pnl_state = FLAT`
- runner secured가 아님
- `giveback_ratio` 높음
- `bars_since_last_push` / `bars_since_last_checkpoint`가 충분히 큼
- continuation/hold score가 약함
- reversal이 thesis break 수준으로 강하지는 않음

즉 "깨진 건 아니지만, 너무 오래 안 가는 늦은 정체"일 때만 time-decay를 유지한다.

## 구현 대상

- `backend/services/path_checkpoint_scene_runtime_bridge.py`
- `tests/unit/test_path_checkpoint_scene_runtime_bridge.py`

## 세부 규칙

### A. runner-secured guard

아래 중 하나면 `time_decay_risk` 선택을 suppress:

- `checkpoint_rule_family_hint = runner_secured_continuation`
- `exit_stage_family = runner`
- `runner_secured = true`

reason:

- `time_decay_runner_secured_guard`

### B. active-flat-profit guard

아래를 만족하는 flat row는 기본적으로 `time_decay_risk`를 suppress:

- `surface_name = continuation_hold_surface`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `unrealized_pnl_state = FLAT`
- `checkpoint_rule_family_hint = active_flat_profit`

단, 아래 `true late stall` 조건을 만족하면 예외적으로 허용한다.

reason:

- `time_decay_active_flat_profit_guard`

### C. true-late-stall allow rule

아래를 모두 만족하면 `time_decay_risk` 허용:

- `surface_name = continuation_hold_surface`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `unrealized_pnl_state = FLAT`
- runner-secured 아님
- `abs(current_profit) <= 0.05`
- `giveback_ratio >= 0.85`
- `bars_since_last_push >= 4`
- `bars_since_last_checkpoint >= 2`
- `runtime_continuation_odds <= 0.58` 또는 `runtime_hold_quality_score <= 0.42`
- `runtime_reversal_odds < runtime_continuation_odds + 0.15`

의미:

- 완전히 깨진 것도 아니고
- 계속 건강한 runner도 아니고
- 늦은 정체로 설명하는 게 가장 가까운 경우만 남긴다

## 기대 효과

- `time_decay_risk` selected count가 추가로 감소
- `runner_secured_continuation` row는 `time_decay` 대신 unresolved 또는 다른 late scene으로 남는다
- `active_flat_profit` 중 true late stall만 남는다
- `trend_exhaustion`과 `time_decay_risk`의 역할 분리가 조금 더 선명해진다

## 테스트

### 추가할 테스트

1. `runner_secured_continuation` row는 `time_decay_risk`가 suppress되는가
2. `active_flat_profit`이지만 true late stall 조건을 만족하는 row는 `time_decay_risk`가 유지되는가
3. `active_flat_profit`인데 true late stall이 아닌 row는 suppress되는가

## 완료 기준

- bridge report에서 `time_decay_risk` selected count가 더 줄어든다
- disagreement audit에서 `time_decay_risk overpull_watch` row_count가 감소한다
- top slice에서 `runner_secured_continuation` 사례가 줄어든다
- 테스트가 모두 통과한다
