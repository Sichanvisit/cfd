# Current PA8 Action-Only Review Packet Detailed Plan

## 목적

PA8은 이제 예전 의미의 `전체 bounded adoption`이 아니다.

현재 PA8의 목표는 아래 하나다.

> scene bias를 제외한 `checkpoint action baseline`만
> bounded review 대상으로 올릴 수 있는지 판단하는 review packet을 유지한다.

즉 이 문서는

- scene bias adoption을 여는 문서가 아니고
- action baseline review 기준을 안정적으로 고정하는 문서다.

## 범위

### 포함

- `checkpoint_action_eval_latest.json`
- `checkpoint_position_side_observation_latest.json`
- `checkpoint_live_runner_watch_latest.json`
- `checkpoint_pa7_review_processor_latest.json`
- `checkpoint_pa78_review_packet_latest.json`

### 제외

- `trend_exhaustion` scene bias live adoption
- `time_decay_risk` scene bias adoption
- SA8 bounded adoption decision 자체

scene은 이번 단계에서
`scene_bias_review_state`로만 관찰한다.

## 핵심 상태

### 1. PA7 review state

- `HOLD_REVIEW_PACKET`
- `READY_FOR_REVIEW`
- `REVIEW_PACKET_PROCESSED`

의미:

- PA7 queue가 아직 남아 있는지
- 아니면 processor 기준으로 이미 정리됐는지

### 2. PA8 review state

- `HOLD_ACTION_BASELINE_ALIGNMENT`
- `READY_FOR_ACTION_BASELINE_REVIEW`

의미:

- action baseline만 놓고 review/canary 후보가 되는지

### 3. scene bias review state

- `HOLD_SCENE_ALIGNMENT`
- `HOLD_PREVIEW_ONLY_SCENE_BIAS`
- `READY_FOR_SCENE_BOUNDED_ADOPTION_REVIEW`

의미:

- scene bias는 action baseline과 분리해서 계속 본다

## 입력 기준

### action axis

- `resolved_row_count`
- `runtime_proxy_match_rate`
- `hold_precision`
- `partial_then_hold_quality`
- `full_exit_precision`
- `manual_exception_count`

### live runner axis

- `live_runner_source_row_count`
- `recent_live_runner_source_row_count`

### PA7 queue axis

- `processed_group_count`
- `review_disposition_counts`
- `unresolved_review_group_count`
- `resolved_review_group_count`

### scene axis

- `high_conf_scene_disagreement_count`
- `scene_expected_action_alignment_rate`
- `trend_exhaustion_preview_positive`

## review gate

### PA7 data ready

- `resolved_row_count >= 4000`
- `live_runner_source_row_count >= 100`
- `hold_precision >= 0.84`
- `full_exit_precision >= 0.99`

### PA8 action baseline review ready

- `pa7_data_ready = true`
- `pa7_unresolved_review_group_count = 0`
- `runtime_proxy_match_rate >= 0.92`
- `hold_precision >= 0.84`
- `partial_then_hold_quality >= 0.95`
- `full_exit_precision >= 0.99`

### scene bias review ready

- `action_baseline_review_ready = true`
- `trend_exhaustion_preview_positive = true`
- `high_conf_scene_disagreement_count <= 500`
- `scene_expected_action_alignment_rate >= 0.95`

## 산출물

### summary

- `pa7_review_state`
- `pa8_review_state`
- `scene_bias_review_state`
- `action_baseline_review_ready`
- `scene_bias_review_ready`
- `pa7_unresolved_review_group_count`
- `blockers`
- `recommended_next_action`

### review_axes

- `action_eval`
- `pa7_review_processor`
- `position_side_observation`
- `scene_disagreement`
- `scene_bias_preview`

## 추천 next action 규칙

- PA7 data 자체가 부족하면:
  - `keep_collecting_checkpoint_rows_before_pa7_review`
- PA7 unresolved group이 남아 있으면:
  - `work_through_pa7_review_groups_before_pa8`
- action baseline review는 가능하지만 scene은 아직이면:
  - `prepare_pa8_action_baseline_review_and_keep_scene_bias_preview_only`
- action과 scene이 모두 review-ready면:
  - `prepare_pa8_action_and_scene_bounded_adoption_review`

## 구현 파일

- [path_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa78_review_packet.py)
- [build_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_pa78_review_packet.py)
- [test_path_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_path_checkpoint_pa78_review_packet.py)
- [test_build_checkpoint_pa78_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_build_checkpoint_pa78_review_packet.py)

## 완료 조건

- packet이 `PA7 processed`와 `PA8 action baseline ready`를 구분해서 표현한다
- scene bias는 별도 state로 남는다
- 최신 artifact가 현재 processor 현실과 모순되지 않는다
- 테스트가 모두 통과한다

## 현재 해석

현재 최신 기준으로는 아래처럼 읽는 것이 맞다.

```text
PA7 = REVIEW_PACKET_PROCESSED
PA8 = READY_FOR_ACTION_BASELINE_REVIEW
scene bias = HOLD_PREVIEW_ONLY_SCENE_BIAS
```

즉 다음 단계는
`PA8 action-only review packet을 실제 review packet처럼 더 쓰는 것`
이지,
아직 scene bias를 adoption으로 올리는 것이 아니다.
