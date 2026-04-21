# PA8 Action Review Checklist Detailed Plan

## Goal

`checkpoint_pa8_action_review_packet_latest.json`을 바로 사람 검토에 쓰기엔 아직 packet 성격이 강하므로,
NAS100 -> BTCUSD -> XAUUSD 순서의 실제 review checklist 문서로 한 번 더 푼다.

이번 단계는 scene bias를 건드리지 않고 action-only baseline review만 다룬다.

## Inputs

- `checkpoint_pa8_action_review_packet_latest.json`
- `checkpoint_pa78_review_packet_latest.json`
- `checkpoint_action_eval_latest.json`
- `checkpoint_management_action_snapshot_latest.json`
- `checkpoint_position_side_observation_latest.json`
- `checkpoint_live_runner_watch_latest.json`

## Outputs

- `checkpoint_pa8_action_review_checklist_latest.json`
- `checkpoint_pa8_action_review_checklist_latest.md`

## Checklist shape

각 symbol row는 아래 항목을 가진다.

- `goal`
- `current_metrics`
- `blockers`
- `pass_criteria`
- `check_items`
- `decision_options`
- `review_focuses`

## Review order

1. `NAS100`
   - hold boundary 중심 review
2. `BTCUSD`
   - runtime proxy / partial_then_hold boundary 중심 review
3. `XAUUSD`
   - support review only
   - row accumulation과 guard stability 확인

## Rules

- `PA8` checklist는 scene bias를 판단에 넣지 않는다.
- `scene_bias_review_state`는 summary에만 남기고, checklist decision에는 직접 반영하지 않는다.
- `PRIMARY_REVIEW` symbol은 patch/review task 또는 provisional canary 후보 둘 중 하나로 닫는다.
- `SUPPORT_REVIEW_ONLY` symbol은 sample accumulation 관찰 대상으로 둔다.

## Completion criteria

- JSON checklist와 Markdown checklist가 모두 생성된다.
- review order가 `NAS100 -> BTCUSD -> XAUUSD`로 유지된다.
- 각 symbol별 blocker와 pass criteria가 사람이 읽을 수 있는 checklist 문장으로 펼쳐진다.
