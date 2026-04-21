# SA6 Trend-Exhaustion Scene Bias Preview

## 목적

- `time_decay_risk`는 계속 log-only로 둔다
- `trend_exhaustion`만 scene bias 후보로 좁혀서 preview한다
- live action은 바꾸지 않고, "이 bias를 썼다면 action이 어떻게 달라졌는지"만 비교한다

## 왜 trend_exhaustion만 먼저 보나

`SA5.8` 이후 최신 audit 기준:

- `trend_exhaustion`
  - `row_count = 907`
  - `watch_state = action_proxy_useful_watch`
  - `expected_action_alignment_rate = 1.0`
- `time_decay_risk`
  - `row_count = 94`
  - `watch_state = review`

즉 `trend_exhaustion`은 late runner 관리 쪽에서 action bias 후보로 볼 수 있지만,
`time_decay_risk`는 아직 action에 직접 섞기보다 계속 log-only가 맞다.

## preview 대상

아래를 모두 만족하는 row만 preview 대상:

- scene candidate selected label = `trend_exhaustion`
- selected confidence >= `0.75`
- `surface_name = continuation_hold_surface`
- `checkpoint_type in {RUNNER_CHECK, LATE_TREND_CHECK}`
- `position_side != FLAT`

## preview 원칙

- 현재 `management_action_label`은 그대로 둔다
- 별도 `preview_action_label`만 계산한다
- baseline보다 더 공격적인 방향으로 바꾸지 않는다
- 즉:
  - baseline이 이미 `FULL_EXIT / PARTIAL_EXIT / PARTIAL_THEN_HOLD`이면 그대로 둔다
  - baseline이 `HOLD / WAIT`일 때만 trim bias를 검토한다

## trend_exhaustion preview bias 규칙

### 1. runner/open-profit trim bias

아래면 `HOLD -> PARTIAL_THEN_HOLD`

- baseline = `HOLD`
- `OPEN_PROFIT` 또는 `runner_secured = true` 또는 `current_profit >= 0.04`
- `runtime_partial_exit_ev >= 0.40` 또는 `runtime_hold_quality_score >= 0.42`

reason:

- `trend_exhaustion_preview_trim_runner`

### 2. giveback-heavy trim bias

아래면 `HOLD -> PARTIAL_EXIT`

- baseline = `HOLD`
- `giveback_ratio >= 0.28`
- `runtime_partial_exit_ev >= 0.46`

reason:

- `trend_exhaustion_preview_giveback_trim`

### 3. wait-to-trim bias

아래면 `WAIT -> PARTIAL_THEN_HOLD`

- baseline = `WAIT`
- active position
- `OPEN_PROFIT` 또는 `runtime_partial_exit_ev >= 0.44`

reason:

- `trend_exhaustion_preview_wait_to_trim`

## 산출물

- `data/analysis/shadow_auto/checkpoint_trend_exhaustion_scene_bias_preview_latest.json`

## 보고 지표

- eligible row count
- preview changed row count
- `from -> to` action counts
- baseline hindsight match rate
- preview hindsight match rate
- improved / worsened / unchanged row counts
- symbol / checkpoint_type top slices

## 구현 대상

- `backend/services/path_checkpoint_scene_bias_preview.py`
- `scripts/build_checkpoint_trend_exhaustion_scene_bias_preview.py`
- `tests/unit/test_path_checkpoint_scene_bias_preview.py`
- `tests/unit/test_build_checkpoint_trend_exhaustion_scene_bias_preview.py`

## 완료 기준

- `trend_exhaustion`만 대상으로 preview report가 생성된다
- live action은 그대로 유지된다
- preview가 baseline보다 hindsight match를 의미 있게 개선하는지 볼 수 있다
- 다음 단계 판단이 가능해진다
  - `keep preview only`
  - `proceed to SA6 bounded resolver integration review`
