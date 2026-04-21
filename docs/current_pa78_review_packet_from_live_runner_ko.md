# Current PA7/PA8 Review Packet From Live Runner

## 목적

live `exit_manage_runner` source가 실제로 들어온 현재 상태에서
PA7 review와 PA8 bounded adoption review를 위해
바로 확인해야 하는 근거를 하나의 packet으로 묶는다.

이 문서는 새 로직을 적용하는 문서가 아니라,
이미 쌓인 산출물을 review-ready 형태로 정리하는 문서다.

## 입력 산출물

- `checkpoint_action_eval_latest.json`
- `checkpoint_position_side_observation_latest.json`
- `checkpoint_live_runner_watch_latest.json`
- `checkpoint_scene_disagreement_audit_latest.json`
- `checkpoint_trend_exhaustion_scene_bias_preview_latest.json`

## 핵심 판단 축

### PA7 review packet

다음을 만족하면 review-ready로 본다.

- resolved row가 충분히 많다
- live runner source가 실제로 들어왔다
- action eval이 안정적이다
  - runtime proxy match
  - hold precision
  - partial_then_hold quality
  - full_exit precision

### PA8 bounded adoption review

다음을 추가로 본다.

- scene disagreement가 아직 너무 높지 않은가
- trend_exhaustion preview가 baseline보다 나쁘지 않은가
- scene bias가 아직 preview-only인지, 실제 bounded adoption review로 넘길 수준인지

## 현재 운영 원칙

- `time_decay_risk`는 계속 log-only
- `trend_exhaustion`은 preview-only
- 따라서 PA8은 바로 live adoption이 아니라
  `bounded adoption review 가능 여부`만 판단한다

## 기대 출력

`checkpoint_pa78_review_packet_latest.json`

여기에는 아래가 들어간다.

- action/eval 축 요약
- live runner 축 요약
- scene disagreement 축 요약
- trend_exhaustion preview 축 요약
- `pa7_review_state`
- `pa8_review_state`
- blockers
- recommended_next_action

## 해석 원칙

- `READY_FOR_REVIEW`
  - packet을 사람 검토 단계로 넘겨도 되는 상태
- `HOLD_PREVIEW_ONLY_SCENE_BIAS`
  - action baseline은 충분히 좋아도 scene bias는 아직 preview-only라 PA8은 보류
- `HOLD_ACTION_SCENE_ALIGNMENT`
  - disagreement나 precision이 아직 높지 않아 review packet 보류
