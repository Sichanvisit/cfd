# CA1 Continuation Accuracy Tracking + Execution Diff Logging

## 1. 목적

이번 단계의 목적은 두 가지다.

1. `continuation_direction`가 실제로 이후 가격 진행과 얼마나 맞는지 계측한다.
2. 실행층에서 원래 하려던 행동이 `guard`와 `promotion`을 거치며 어떻게 바뀌었는지 구조적으로 남긴다.

즉 이번 단계는 새 규칙을 더 넣는 단계가 아니라,
이미 붙어 있는 continuation / execution 배선이 실제로 맞는지 숫자로 검증하기 위한 계측 단계다.

## 2. 구현 위치

### 2-1. continuation accuracy tracker

- 서비스: [directional_continuation_accuracy_tracker.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\directional_continuation_accuracy_tracker.py)
- 런타임 연결: [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

핵심 역할:

- `latest_signal_by_symbol`의 `directional_continuation_overlay_*`를 읽는다.
- `current_close / live_price`를 기준가로 저장한다.
- 동일 `symbol + candidate_key + direction`는 `5분 spacing`으로만 샘플링한다.
- `10 / 20 / 30 bars` horizon으로 pending observation을 만든다.
- 시간이 지나면 `max_price_seen / min_price_seen`을 기준으로
  - `CORRECT`
  - `INCORRECT`
  - `UNRESOLVED`
  로 평가한다.

### 2-2. execution diff logging

- 실행층: [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- 런타임 trace: [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

핵심 역할:

- `original_action_side`
- `guarded_action_side`
- `promoted_action_side`
- `final_action_side`

를 남긴다.

즉 "원래 SELL이었는데 guard가 SKIP으로 내렸고, promotion이 BUY로 올렸는가"를 로그로 바로 볼 수 있게 만든다.

## 3. continuation accuracy tracker 세부 동작

### 입력

- `directional_continuation_overlay_direction`
- `directional_continuation_overlay_candidate_key`
- `directional_continuation_overlay_score`
- `current_close`
- `live_price`
- `time`
- `timestamp`

### 상태 파일

- state:
  - `data/analysis/shadow_auto/directional_continuation_accuracy_tracker_state.json`
- latest artifact:
  - `data/analysis/shadow_auto/directional_continuation_accuracy_tracker_latest.json`
  - `data/analysis/shadow_auto/directional_continuation_accuracy_tracker_latest.md`

### 평가 기준

- primary horizon: `20 bars`
- 참고 horizon: `10 / 30 bars`
- decisive move threshold:
  - `0.05%`

판정:

- continuation 방향으로 유리한 움직임이 임계값 이상이면 `CORRECT`
- 반대 움직임이 더 크고 임계값 이상이면 `INCORRECT`
- 둘 다 약하면 `UNRESOLVED`

## 4. execution diff 세부 동작

### 생성 필드

- nested:
  - `execution_action_diff_v1`
- flat:
  - `execution_diff_original_action_side`
  - `execution_diff_guarded_action_side`
  - `execution_diff_promoted_action_side`
  - `execution_diff_final_action_side`
  - `execution_diff_changed`
  - `execution_diff_guard_applied`
  - `execution_diff_promotion_active`
  - `execution_diff_reason_keys`

### 저장 위치

- `entry_decision_result_v1.metrics`
- `latest_signal_by_symbol[symbol]`
- `ai_entry_traces`

즉 detail row, slim row, recent trace 모두에서 확인 가능하게 했다.

## 5. 런타임 surface

### latest_signal_by_symbol

row에는 아래 accuracy surface가 붙는다.

- `directional_continuation_accuracy_horizon_bars`
- `directional_continuation_accuracy_sample_count`
- `directional_continuation_accuracy_measured_count`
- `directional_continuation_accuracy_correct_rate`
- `directional_continuation_accuracy_false_alarm_rate`
- `directional_continuation_accuracy_unresolved_rate`
- `directional_continuation_accuracy_last_state`
- `directional_continuation_accuracy_last_candidate_key`

### runtime_status

top-level에는 아래 summary가 붙는다.

- `directional_continuation_accuracy_summary_v1`
- `directional_continuation_accuracy_artifact_paths`

## 6. 이번 단계의 의미

이제부터는 다음 질문에 숫자로 답할 수 있다.

- continuation이 실제로 맞았는가
- wrong-side guard가 실제로 행동을 바꿨는가
- promotion이 실제로 BUY/SELL 전환을 만들었는가
- state25 bounded live를 켜기 전에 충분한 검증이 쌓였는가

즉 이번 단계는 "잘 보이는 것 같다"를
"이 정도 비율로 맞는다 / 실제로 이렇게 행동이 바뀌었다"로 바꾸는 단계다.
