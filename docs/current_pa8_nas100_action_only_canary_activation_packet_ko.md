# Current PA8 NAS100 Action-Only Canary Activation Packet

## 목적

이 문서는
[checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.json)
과
[checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json)
를 바탕으로,
`NAS100 bounded action-only canary`를 사람이 최종 승인할 수 있는 activation packet으로 묶는다.

중요한 원칙:

- symbol은 `NAS100` 하나만
- action-only만
- `HOLD -> PARTIAL_THEN_HOLD`만
- scene bias는 계속 제외
- size 변경과 새 entry logic은 허용하지 않음

## 목표 상태

- `activation_state = READY_FOR_MANUAL_BOUNDED_ACTION_ONLY_CANARY_ACTIVATION_REVIEW`
- `allow_activation = true`
- `manual_activation_required = true`
- `blockers = []`

## activation scope

- symbol: `NAS100`
- surface: `continuation_hold_surface`
- checkpoint_type: `RUNNER_CHECK`
- family: `profit_hold_bias`
- baseline action: `HOLD`
- candidate action: `PARTIAL_THEN_HOLD`
- size change: 불가
- new entry logic: 불가
- scene bias: 제외

## activation guardrails

- sample floor: `50`
- worsened row ceiling: `0`
- hold precision floor: `0.80`
- runtime proxy match rate: baseline보다 좋아야 함
- partial_then_hold_quality: baseline보다 나빠지면 안 됨
- rollback:
  - hold precision drop below baseline
  - partial_then_hold_quality regression
  - new worsened rows detected

## 산출물

- JSON:
  - [checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.json)
- Markdown:
  - [checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_activation_packet_latest.md)

## 구현 파일

- [path_checkpoint_pa8_action_canary_activation_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_activation_packet.py)
- [build_checkpoint_pa8_action_canary_activation_packet.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_pa8_action_canary_activation_packet.py)
- [test_path_checkpoint_pa8_action_canary_activation_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_path_checkpoint_pa8_action_canary_activation_packet.py)
- [test_build_checkpoint_pa8_action_canary_activation_packet.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_build_checkpoint_pa8_action_canary_activation_packet.py)

## 해석

이 packet은 아직 live apply가 아니다.

의미는 이것이다.

`이제 NAS100 bounded action-only canary를 사람이 승인할 수 있을 정도로, scope / monitoring / rollback 계약이 정리됐다.`
