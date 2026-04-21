# PF7 Live Runner Watch Loop

## 목적

- `exit_manage_runner` live source가 실제 runtime loop에서 생성되기 시작했는지 확인한다.
- 이전 스냅샷 대비 증가량(`delta`)까지 같이 본다.

## 추가된 파일

- `backend/services/path_checkpoint_live_runner_watch.py`
- `scripts/build_checkpoint_live_runner_watch.py`

## 보는 값

- `live_runner_source_row_count`
- `recent_live_runner_source_row_count`
- `live_runner_hold_row_count`
- `previous_live_runner_source_row_count`
- `live_runner_source_delta`
- `symbols_with_live_runner_source`

## 실행 예시

한 번만 확인:

```powershell
python scripts/build_checkpoint_live_runner_watch.py --iterations 1 --recent-minutes 60
```

반복 확인:

```powershell
python scripts/build_checkpoint_live_runner_watch.py --iterations 12 --sleep-seconds 10 --recent-minutes 60
```

## 최신 확인 결과

- `live_runner_source_row_count = 0`
- `recent_live_runner_source_row_count = 0`
- `live_runner_source_delta = 0`
- `recommended_next_action = keep_runtime_running_until_exit_manage_runner_rows_appear`

즉 코드 경로는 열렸지만,
아직 실제 runtime loop에서 `exit_manage_runner` live row가 새로 찍히지는 않았다.

## 다음 해석 기준

### 좋은 신호

- `live_runner_source_row_count > 0`
- `live_runner_source_delta > 0`
- 특정 symbol row에 `recommended_focus = inspect_<symbol>_live_runner_hold_boundary`

### 아직 대기 상태

- count가 계속 `0`
- delta도 `0`

이 경우엔 runtime이 아직 runner-secured hold 구간을 지나지 않았거나,
해당 분기까지 live row가 충분히 안 들어온 상태로 보면 된다.
