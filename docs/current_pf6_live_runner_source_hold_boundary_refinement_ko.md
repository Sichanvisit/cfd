# PF6 Live Runner Source / Hold Boundary Refinement

## 목적

- `exit_manage_runner` live source가 실제 hold/no-exit loop에서도 남도록 기록 경로를 넓힌다.
- `runner_secured` 이후의 `HOLD`와 `PARTIAL_THEN_HOLD` 경계를 한 번 더 다듬는다.
- observation artifact에 `live_runner_source_row_count`를 추가해서, 이후 실제 loop에서 live source 비중이 올라오는지 바로 볼 수 있게 한다.

## 핵심 변경

### 1. hold/no-exit -> runner source 승격

대상 파일:

- `backend/services/exit_manage_positions.py`

추가 helper:

- `_resolve_hold_checkpoint_recording(...)`

적용 위치:

- `recovery_wait_hold`
- `adverse_hold_delay`
- `adverse_wait_delay`
- `allow_long_blocked`
- `no_exit`

규칙:

- `partial_done` 또는 `be_moved`가 이미 켜져 있으면
- 기존 `exit_manage_hold` 대신 `exit_manage_runner`
- `final_stage = runner_observe:<base_stage>`
- `outcome = runner_hold`

즉 한 번 runner preservation이 적용된 뒤의 후속 hold loop는
이제 live checkpoint row에서도 runner-family로 남는다.

### 2. HOLD vs PARTIAL_THEN_HOLD 경계 refinement

대상 파일:

- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_dataset.py`

추가된 핵심 branch:

- `runner_secured + realized_pnl_state=LOCKED + low giveback`
  -> `HOLD`

새 reason:

- `runner_locked_hold_continue`
- `bootstrap_runner_locked_hold_continue`

의도:

- 이미 lock으로 runner가 확보된 뒤엔
  계속 `PARTIAL_THEN_HOLD`로 남기기보다
  `HOLD`로 읽는 게 더 자연스러운 row를 분리한다.

### 3. backfill source replay 일관성

대상 파일:

- `backend/services/path_checkpoint_action_resolver.py`
- `backend/services/path_checkpoint_dataset.py`
- `backend/services/path_checkpoint_position_side_observation.py`

내용:

- `open_trade_backfill`
- `closed_trade_hold_backfill`
- `closed_trade_runner_backfill`

는 stored label보다 최신 resolver replay를 우선 사용하게 맞춤

효과:

- snapshot / dataset / observation이 현재 rule tuning 결과를 더 일관되게 반영

## 테스트

실행 결과:

- `26 passed`
- `26 passed`
- observation/action/dataset 추가 확인 `23 passed`

총 `75 passed`

## 최신 결과

### checkpoint_dataset_resolved.csv

- `resolved_row_count = 83`
- `position_side_row_count = 80`
- `hindsight_label_counts`
  - `HOLD = 49`
  - `PARTIAL_THEN_HOLD = 13`
  - `WAIT = 12`
  - `PARTIAL_EXIT = 8`
  - `FULL_EXIT = 1`

### checkpoint_action_eval_latest.json

- `runtime_proxy_match_rate = 0.626506`
- `hold_precision = 0.888889`
- `partial_then_hold_quality = 0.325`

해석:

- `HOLD`를 넓히면서 `PARTIAL_THEN_HOLD`는 더 정밀한 family로 압축됐다.
- 지금은 `HOLD precision`은 올라갔고, 대신 `PARTIAL_THEN_HOLD`는 더 좁고 엄격한 label이 되었다.

### checkpoint_management_action_snapshot_latest.json

- `HOLD = 55`
- `PARTIAL_THEN_HOLD = 12`
- `PARTIAL_EXIT = 8`
- `WAIT = 7`
- `FULL_EXIT = 1`

### checkpoint_position_side_observation_latest.json

- `runner_secured_row_count = 47`
- `live_runner_source_row_count = 0`

해석:

- code path는 열렸지만,
- 실제 artifact 기준으로는 아직 새 live `exit_manage_runner` loop row가 더 쌓이지 않았다.
- 즉 다음엔 runtime loop를 조금 더 태워서 `live_runner_source_row_count`가 0에서 올라오는지 확인하는 게 중요하다.

## 다음 순서

1. 실제 live `exit_manage` loop를 더 돌려 `live_runner_source_row_count` 상승 확인
2. `runner_locked_hold_continue`가 실제 live row에서도 잡히는지 확인
3. 필요하면 `HOLD`를 다시 둘로 쪼개지 말고, `HOLD vs PARTIAL_THEN_HOLD` margin만 미세 조정
