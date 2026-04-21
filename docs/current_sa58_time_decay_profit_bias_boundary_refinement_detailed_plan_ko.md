# SA5.8 Time-Decay Profit-Bias Boundary Refinement

## 목적

- `SA5.7` 이후에도 남아 있는 `time_decay_risk` 과잉 선택을 한 번 더 줄인다
- 특히 `continuation_hold_surface + RUNNER_CHECK` 안에서
  - `profit_trim_bias`
  - `profit_hold_bias`
  - `wait_bias`
  - `true late stall`
  의 경계를 더 분리한다

## 현재 관찰

최신 resolved audit 기준 `time_decay_risk` selected row는 아래 쪽으로 몰려 있다.

- `profit_trim_bias = 179`
- `profit_hold_bias = 64`
- `wait_bias = 2`
- `active_position = 7`

또한 대부분:

- `unrealized_pnl_state = OPEN_PROFIT`
- `runtime_proxy_management_action_label = PARTIAL_THEN_HOLD / HOLD / PARTIAL_EXIT`
- `hindsight_best_management_action_label = PARTIAL_THEN_HOLD / PARTIAL_EXIT / HOLD`

즉 이 부류는 "늦게 안 가는 죽은 자리"보다
"이미 수익 중인 관리 row"에 더 가깝다.

## 해석

`time_decay_risk`는 원래 아래 쪽에 더 가까워야 한다.

- near-flat
- late checkpoint
- continuation/hold 품질 약화
- 크게 망가진 건 아니지만 오래 안 가는 stalled 관리 row

반면 아래는 `time_decay`보다 `profit management` 쪽이다.

- `profit_trim_bias`
- `profit_hold_bias`
- `OPEN_PROFIT`
- `HOLD / PARTIAL_THEN_HOLD / PARTIAL_EXIT`
- continuation/hold score가 아직 괜찮음

## 구현 대상

- `backend/services/path_checkpoint_scene_runtime_bridge.py`
- `tests/unit/test_path_checkpoint_scene_runtime_bridge.py`

## 세부 규칙

### A. profit-bias suppression

아래를 만족하면 `time_decay_risk`를 suppress:

- `surface_name = continuation_hold_surface`
- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `unrealized_pnl_state = OPEN_PROFIT`
- `checkpoint_rule_family_hint in {profit_trim_bias, profit_hold_bias}`
- `current_profit >= 0.03`
- `runtime_continuation_odds >= 0.70`
- `runtime_hold_quality_score >= 0.45`
- `giveback_ratio <= 0.75`

reason:

- `time_decay_profit_bias_guard`

### B. wait-bias keep rule

아래는 여전히 `time_decay_risk`를 허용:

- `checkpoint_rule_family_hint = wait_bias`
- `current_profit <= 0.02`
- `unrealized_pnl_state in {FLAT, OPEN_PROFIT}`

즉 "살아 있다기보다 애매하게 멈춘 row"는 유지한다.

### C. true late stall 유지

`SA5.7`에서 정의한 `true late stall` 규칙은 유지한다.

즉 `active_flat_profit`은 여전히 true late stall일 때만 허용한다.

## 기대 효과

- `time_decay_risk` selected count가 추가 감소
- `profit_trim_bias / profit_hold_bias` row는 `time_decay` 대신 unresolved로 돌아간다
- `wait_bias`와 일부 true late stall만 남는다
- `time_decay_risk overpull_watch` row_count가 추가 감소

## 테스트

1. `profit_trim_bias + OPEN_PROFIT + healthy continuation` row는 suppress되는가
2. `profit_hold_bias + OPEN_PROFIT + healthy continuation` row는 suppress되는가
3. `wait_bias + tiny profit` row는 유지되는가

## 완료 기준

- bridge report에서 `time_decay_risk` selected count가 더 감소
- disagreement audit에서 `time_decay_risk` row_count와 `NAS100 + RUNNER_CHECK` slice가 더 감소
- focused test와 영향권 회귀가 모두 통과한다
