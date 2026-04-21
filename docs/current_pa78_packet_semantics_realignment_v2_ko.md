# Current PA7/PA8 Packet Semantics Realignment v2

## 목적

기존 `checkpoint_pa78_review_packet`은 너무 오래된 의미를 유지하고 있었다.

- `PA7`을 아직도 raw KPI floor 중심으로만 판단
- `PA8`에 scene bias blocker를 그대로 섞음
- `PA7 processor`가 이미 queue를 거의 소화한 현실을 packet이 반영하지 못함

이번 realignment의 목적은 아래 세 축을 분리하는 것이다.

1. `PA7`
   - review queue를 실제로 아직 소화해야 하는가
2. `PA8`
   - scene bias를 제외한 action baseline review로는 올라갈 수 있는가
3. `SA`
   - scene bias는 여전히 preview-only인가

## 새 의미

### PA7 review state

- `HOLD_REVIEW_PACKET`
  - 아직 review packet으로 보기엔 데이터가 부족함
- `READY_FOR_REVIEW`
  - 데이터는 충분하지만 processor unresolved group이 남아 있음
- `REVIEW_PACKET_PROCESSED`
  - processor 기준 unresolved group이 사라졌고,
    남은 건 `resolved_by_current_policy` 또는 hydration-confirmed 성격임

즉 이제 `PA7`은 더 이상 raw KPI floor만으로 보지 않고,
`checkpoint_pa7_review_processor_latest.json`의 disposition을 같이 본다.

### PA8 review state

- `HOLD_ACTION_BASELINE_ALIGNMENT`
  - action baseline review로 올리기엔 아직 score/KPI/PA7 processor 상태가 부족함
- `READY_FOR_ACTION_BASELINE_REVIEW`
  - scene bias를 빼고 보면 action baseline은 bounded review로 올릴 수 있음

핵심은 `PA8`을 이제 scene adoption 단계가 아니라
`action-only review`로 읽는다는 점이다.

### Scene bias review state

- `HOLD_SCENE_ALIGNMENT`
  - scene disagreement/alignment가 아직 부족함
- `HOLD_PREVIEW_ONLY_SCENE_BIAS`
  - action baseline review는 가능하지만 scene bias는 preview-only 유지
- `READY_FOR_SCENE_BOUNDED_ADOPTION_REVIEW`
  - scene도 bounded adoption review로 올릴 수 있음

즉 `PA8`과 `scene bias`를 같은 state로 묶지 않는다.

## 새 gating 기준

### PA7 data ready

- `resolved_row_count >= 4000`
- `live_runner_source_row_count >= 100`
- `hold_precision >= 0.84`
- `full_exit_precision >= 0.99`

### PA7 unresolved review group count

아래 disposition은 unresolved로 본다.

- `policy_mismatch_review`
- `baseline_hydration_gap`
- `mixed_backfill_value_scale_review`
- `mixed_wait_boundary_review`
- `mixed_review`

아래 disposition은 processed/resolved로 본다.

- `resolved_by_current_policy`
- `hydration_gap_resolved_by_current_policy`
- `hydration_gap_confirmed_cluster`
- `confidence_only_confirmed`

### Action baseline review ready

- `pa7_data_ready = true`
- `pa7_unresolved_review_group_count = 0`
- `runtime_proxy_match_rate >= 0.92`
- `hold_precision >= 0.84`
- `partial_then_hold_quality >= 0.95`
- `full_exit_precision >= 0.99`

### Scene bias review ready

- `action_baseline_review_ready = true`
- `trend_exhaustion_preview_positive = true`
- `high_conf_scene_disagreement_count <= 500`
- `scene_expected_action_alignment_rate >= 0.95`

## 기대 효과

이제 latest packet은 아래처럼 읽는다.

- `PA7 review_state`
  - queue를 실제로 더 소화해야 하는지
- `PA8 review_state`
  - action baseline review는 열 수 있는지
- `scene_bias_review_state`
  - scene bias는 여전히 preview-only인지

즉 다음처럼 해석할 수 있다.

```text
PA7 = 이미 processor로 거의 정리됨
PA8 = action baseline review 가능
SA = scene bias는 아직 preview-only
```

## 관련 파일

- [path_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa78_review_packet.py)
- [build_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_pa78_review_packet.py)
- [checkpoint_pa7_review_processor_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa7_review_processor_latest.json)
- [checkpoint_pa78_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa78_review_packet_latest.json)
