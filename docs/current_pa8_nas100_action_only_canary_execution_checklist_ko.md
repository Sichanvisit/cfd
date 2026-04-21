# Current PA8 NAS100 Action-Only Canary Execution Checklist

## 목적

이 문서는
[checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json)
기준으로,
`NAS100 action-only provisional canary`를 실제 bounded execution 전 점검표로 풀어쓴다.

핵심 원칙은 단순하다.

- NAS100만 본다
- action-only만 본다
- scene bias는 계속 제외한다
- scope를 넓히지 않는다

## 입력

- [checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_provisional_canary_review_packet_latest.json)

## 목표 상태

- `canary_review_state = READY_FOR_PROVISIONAL_ACTION_ONLY_CANARY_REVIEW`
- `execution_state = READY_FOR_BOUNDED_ACTION_ONLY_CANARY_EXECUTION`
- `blockers = []`

## 실행 범위

- symbol: `NAS100`
- surface: `continuation_hold_surface`
- checkpoint_type: `RUNNER_CHECK`
- family: `profit_hold_bias`
- baseline action: `HOLD`
- candidate action: `PARTIAL_THEN_HOLD`
- scene bias: 제외

## guardrails

- sample floor: `50`
- worsened row ceiling: `0`
- hold precision floor: `0.80`
- runtime proxy match rate: baseline보다 높아야 함
- partial_then_hold_quality: baseline보다 나빠지면 안 됨

## 산출물

- JSON:
  - [checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.json)
- Markdown:
  - [checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\checkpoint_pa8_nas100_action_only_canary_execution_checklist_latest.md)

## 구현 파일

- [path_checkpoint_pa8_action_canary_execution_checklist.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\path_checkpoint_pa8_action_canary_execution_checklist.py)
- [build_checkpoint_pa8_action_canary_execution_checklist.py](C:\Users\bhs33\Desktop\project\cfd\scripts\build_checkpoint_pa8_action_canary_execution_checklist.py)
- [test_path_checkpoint_pa8_action_canary_execution_checklist.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_path_checkpoint_pa8_action_canary_execution_checklist.py)
- [test_build_checkpoint_pa8_action_canary_execution_checklist.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_build_checkpoint_pa8_action_canary_execution_checklist.py)

## 해석

이 체크리스트는 live rollout 승인이 아니다.

의미는 딱 이것이다.

`이제 NAS100 action-only bounded canary를 켜기 전에 무엇을 확인해야 하는지, 어떤 신호가 나오면 즉시 멈춰야 하는지를 실행 언어로 고정했다.`
