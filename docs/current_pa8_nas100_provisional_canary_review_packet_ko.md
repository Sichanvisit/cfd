# Current PA8 NAS100 Provisional Canary Review Packet

## 목적

이 문서는 `NAS100 / continuation_hold_surface / RUNNER_CHECK / profit_hold_bias`
구간에서 만든 action-only preview를
실제 bounded canary 검토 대상으로 올릴 수 있는지 판단하는 packet 기준서다.

중요한 선은 유지한다.

- 이번 packet은 `action-only`다
- scene bias는 계속 `preview-only`다
- live resolver를 바로 바꾸지 않는다

## 입력

- [checkpoint_pa8_action_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_action_review_packet_latest.json)
- [checkpoint_pa8_action_review_nas100_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_action_review_nas100_latest.json)
- [checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_profit_hold_bias_preview_latest.json)

## 목표 상태

- `pa8_review_state = READY_FOR_ACTION_BASELINE_REVIEW`
- `nas100_review_result = narrow_hold_boundary_candidate_identified`
- `eligible_row_count >= 50`
- `preview_changed_row_count > 0`
- `worsened_row_count = 0`
- `preview_hold_precision >= 0.80`
- `preview_runtime_proxy_match_rate > baseline_runtime_proxy_match_rate`
- `preview_partial_then_hold_quality >= baseline_partial_then_hold_quality`

위 조건이 모두 맞으면:

- `canary_review_state = READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW`
- `recommended_next_action = prepare_nas100_action_only_provisional_canary_scope`

## candidate scope

- symbol: `NAS100`
- surface: `continuation_hold_surface`
- checkpoint_type: `RUNNER_CHECK`
- family: `profit_hold_bias`
- baseline_action: `HOLD`
- preview_action: `PARTIAL_THEN_HOLD`
- scene bias: 제외

## guardrails

- sample floor: `50`
- worsened rows ceiling: `0`
- hold precision floor: `0.80`
- runtime proxy match rate: baseline보다 개선되어야 함
- partial_then_hold_quality: baseline보다 나빠지면 안 됨

## 산출물

- JSON packet:
  - [checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json)
- Markdown review:
  - [checkpoint_pa8_nas100_provisional_canary_review_packet_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_provisional_canary_review_packet_latest.md)

## 구현 파일

- [path_checkpoint_pa8_action_canary_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_review_packet.py)
- [build_checkpoint_pa8_action_canary_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_pa8_action_canary_review_packet.py)
- [test_path_checkpoint_pa8_action_canary_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_path_checkpoint_pa8_action_canary_review_packet.py)
- [test_build_checkpoint_pa8_action_canary_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_build_checkpoint_pa8_action_canary_review_packet.py)

## 해석 원칙

이 packet이 `READY`가 되더라도 곧바로 live adoption으로 가지 않는다.
의미는 오직 이것이다.

`이 preview는 NAS100 단일 심볼의 action-only provisional canary review 대상으로 올릴 가치가 있다.`
