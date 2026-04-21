# Current PA8 NAS100 Canary Review Monitoring Rollback Packets

## 목적

이 문서는 PA8에서 아직 남아 있던 세 갈래를 같이 정리한다.

- activation packet 사람 검토
- bounded action-only canary monitoring packet
- rollback review packet

핵심 원칙은 그대로 유지한다.

- NAS100만 본다
- action-only만 본다
- scene bias는 계속 제외한다

## 1. activation human review

산출물:

- [checkpoint_pa8_nas100_action_only_canary_activation_review_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_activation_review_latest.json)
- [checkpoint_pa8_nas100_action_only_canary_activation_review_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_activation_review_latest.md)

의미:

- activation packet을 사람이 approve / hold / reject 중 무엇으로 볼지 정리한다

## 2. monitoring packet

산출물:

- [checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.json)
- [checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_monitoring_packet_latest.md)

의미:

- canary를 켠 뒤 어떤 metric을 계속 볼지 고정한다
- 첫 window 전에는 `AWAIT_FIRST_CANARY_WINDOW_RESULTS`로 둔다

추적 대상:

- `hold_precision`
- `runtime_proxy_match_rate`
- `partial_then_hold_quality`
- `new_worsened_rows`

## 3. rollback review packet

산출물:

- [checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.json)
- [checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_rollback_review_packet_latest.md)

의미:

- 어떤 조건이면 즉시 중단할지 미리 고정한다

rollback 기준:

- hold precision drop below baseline
- runtime proxy match rate drop below baseline
- partial_then_hold_quality regression
- new worsened rows detected

## 4. first canary window 관찰 결과

이번 단계에서는 실제 canary를 아직 켜지 않았기 때문에
결과 누적은 시작하지 않고,
그 대신 monitoring packet을 `first window 대기` 상태로 만든다.

즉 지금 상태는:

- `monitoring_state = READY_TO_START_FIRST_CANARY_WINDOW`
- `first_window_status = AWAIT_FIRST_CANARY_WINDOW_RESULTS`

## 구현 파일

- [path_checkpoint_pa8_action_canary_activation_review.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_activation_review.py)
- [path_checkpoint_pa8_action_canary_monitoring_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_monitoring_packet.py)
- [path_checkpoint_pa8_action_canary_rollback_review_packet.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_rollback_review_packet.py)

## 해석

이제 PA8에서 남은 것은 “문서가 없어서 못 움직이는 상태”가 아니다.

지금은

- activation review
- monitoring
- rollback

셋 다 packet으로 준비됐고,
다음부터는 진짜로 first canary window를 관찰해서 결과를 누적하는 단계다.
