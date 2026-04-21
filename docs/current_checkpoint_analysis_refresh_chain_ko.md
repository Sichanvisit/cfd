# Checkpoint Analysis Refresh Chain

## 왜 필요한가

- `checkpoint_rows.csv`는 계속 쌓이는데
- `scene log-only bridge`, `scene disagreement audit`, `trend_exhaustion preview`, `PA8 board`
  같은 요약 artifact는 수동으로 다시 빌드해야 했다.

그래서 실제 상태는 바뀌었는데
우리가 보는 report는 어제 시각에 멈춰 있는 문제가 생길 수 있었다.

## 해결 방식

row가 기본 runtime 경로로 append될 때
`throttled refresh chain`을 같이 건다.

원칙:

- row마다 무조건 전체 재빌드하지 않는다
- 기본값은 `5분` 또는 `25 row` 이상 쌓였을 때만 재빌드한다
- non-default test/tmp 경로에서는 자동 refresh를 돌리지 않는다
- refresh 실패가 trading path를 막으면 안 된다

## refresh 대상

1. `checkpoint_dataset.csv`
2. `checkpoint_dataset_resolved.csv`
3. `checkpoint_action_eval_latest.json`
4. `checkpoint_position_side_observation_latest.json`
5. `checkpoint_live_runner_watch_latest.json`
6. `checkpoint_management_action_snapshot_latest.json`
7. `checkpoint_scene_dataset.csv`
8. `checkpoint_scene_eval_latest.json`
9. `checkpoint_scene_log_only_bridge_latest.json`
10. `checkpoint_scene_disagreement_audit_latest.json`
11. `checkpoint_trend_exhaustion_scene_bias_preview_latest.json`
12. `checkpoint_pa7_review_processor_latest.json`
13. `checkpoint_pa78_review_packet_latest.json`
14. `checkpoint_pa8_canary_refresh_board_latest.json`
15. `checkpoint_pa8_historical_replay_board_latest.json`

## 자동 연결 위치

- `record_checkpoint_context()`

이 함수는 entry / exit / backfill 모두가 공통으로 지나가는 지점이라
여기에 throttled refresh를 붙이면 원천 row가 들어오는 모든 경로를 한 번에 커버할 수 있다.

## 수동 실행

필요하면 아래 스크립트로 강제 refresh도 가능하다.

- [build_checkpoint_analysis_refresh_chain.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_analysis_refresh_chain.py)

예:

```powershell
python scripts/build_checkpoint_analysis_refresh_chain.py --force
```

## 주의

- 이 chain은 `scene bias live adoption`을 여는 체인이 아니다
- stale artifact를 fresh row 기준으로 다시 맞추는 체인이다
- `PA8`의 live closeout은 여전히 실제 post-activation live row가 필요하다
- `historical replay board`는 supporting evidence일 뿐, live first-window를 대체하지 않는다
