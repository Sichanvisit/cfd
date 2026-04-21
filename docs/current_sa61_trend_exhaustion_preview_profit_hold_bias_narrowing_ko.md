# SA6.1 Trend-Exhaustion Preview Narrowing for Profit-Hold Bias

## 목적

- `SA6 preview`에서 `trend_exhaustion -> PARTIAL_THEN_HOLD` 변경이 아직 과한 구간을 더 줄인다
- 특히 `profit_hold_bias` row에서
  - 실제로 trim이 맞았던 `XAU/NAS` 케이스만 남기고
  - healthy hold였던 `XAU` runner hold 케이스는 건드리지 않게 한다

## 현재 관찰

최신 preview artifact 기준:

- `eligible_row_count = 890`
- `preview_changed_row_count = 17`
- `improved = 6`
- `worsened = 11`

즉 preview는 이미 많이 줄었지만,
바뀐 17건 중 `XAUUSD HOLD -> PARTIAL_THEN_HOLD` 일부가 아직 과하다.

## casebook 해석

좋아진 케이스 특징:

- `profit_hold_bias`
- `partial_exit_ev`가 `hold_quality`보다 뚜렷하게 높음
- 일부는 `protective` 문맥
- `PARTIAL_THEN_HOLD` hindsight와 실제로 맞음

나빠진 케이스 특징:

- `profit_hold_bias`
- `partial_exit_ev`와 `hold_quality` 차이가 작음
- `giveback_ratio` 거의 0
- hindsight는 `HOLD`

즉 핵심 차이는

- 단순히 `trend_exhaustion`이냐가 아니라
- `partial_exit`가 `hold`보다 얼마나 우세한가다

## 구현 원칙

- `trend_exhaustion preview`는 계속 preview-only
- baseline `HOLD`를 `PARTIAL_THEN_HOLD`로 바꾸는 건 더 엄격히 제한

## 세부 규칙

### preview trim 허용

`HOLD -> PARTIAL_THEN_HOLD`는 아래를 모두 만족할 때만 허용:

- `unrealized_pnl_state = OPEN_PROFIT` 또는 `current_profit >= 0.04`
- `runtime_partial_exit_ev >= runtime_hold_quality_score + 0.05`
- 그리고 아래 중 하나
  - `exit_stage_family = protective`
  - `runtime_hold_quality_score <= 0.50`
  - `giveback_ratio >= 0.18`

### preview trim 차단

아래면 baseline `HOLD` 유지:

- `runner_secured_continuation` 또는 `exit_stage_family = runner` 이고 `giveback_ratio < 0.20`
- `partial_exit_ev - hold_quality < 0.05`
- `giveback_ratio = 0`에 가깝고 hold_quality가 아직 높음

## 기대 효과

- changed row 수는 더 줄어든다
- `XAUUSD`의 과한 `HOLD -> PARTIAL_THEN_HOLD`가 줄어든다
- preview hindsight match가 baseline에 더 가까워지거나 일부 개선된다

## 완료 기준

- preview_changed_row_count 감소
- worsened_row_count 감소
- `XAUUSD RUNNER_CHECK` changed slice 감소
