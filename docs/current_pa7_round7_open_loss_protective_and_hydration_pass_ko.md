# PA7 Round-7 Open-Loss Protective Narrowing And Hydration Pass

## 목적

PA7 review queue의 다음 두 병목을 같이 정리한다.

1. `open_loss_protective` 잔여 mismatch
2. `runner_secured_continuation | WAIT` hydration giant group

## 관찰

### 1) open_loss_protective 잔여 그룹

남은 주요 그룹은 두 갈래였다.

- `BTCUSD / follow_through_surface / INITIAL_PUSH / open_loss_protective`
  - live row 성격
  - `PARTIAL_EXIT -> hindsight WAIT`
  - `full_exit_gate_not_met_trim_fallback`가 너무 쉽게 trim으로 내려감

- `NAS100/XAUUSD / continuation_hold_surface / RUNNER_CHECK / open_loss_protective`
  - backfill synthetic row 성격
  - `FULL_EXIT/PARTIAL_EXIT -> hindsight WAIT`
  - moderate protective pressure인데 full-exit gate 쪽이 과하게 열림

### 2) hydration giant group

`BTCUSD / continuation_hold_surface / RUNNER_CHECK / runner_secured_continuation / WAIT`
대형 그룹은 실제 정책 mismatch보다
`management_action_label blank + score blank`가 많은 hydration backlog였다.

중요한 점:

- blank 비율이 매우 높고
- `policy_replay_action_label == hindsight_best_management_action_label`
  인 row가 대다수다.

즉 이 그룹은 “정책 재검토 대상”보다
“기록 수화 상태를 따로 보고 지나갈 그룹”에 가깝다.

## 이번 패치

### A. Resolver patch

`path_checkpoint_action_resolver.py`에 두 좁은 예외를 추가한다.

1. `follow_through_surface + INITIAL_PUSH + open_loss_protective`
   - continuation 우세
   - hold가 trim보다 낫고
   - full-exit gate는 안 열렸을 때
   - `WAIT`로 되돌림

2. `backfill + continuation_hold_surface + RUNNER_CHECK + open_loss_protective`
   - giveback이 높지만
   - full_exit score는 극단까진 아니고
   - continuation/reversal이 거의 균형일 때
   - `WAIT`로 되돌림

### B. Processor hydration pass

`path_checkpoint_pa7_review_processor.py`에서
아래 조건이면 기존 `baseline_hydration_gap` 대신
별도 disposition으로 낮춘다.

- `blank_baseline_share >= 0.60`
- `missing_score_share >= 0.60`
- `policy_replay_match_rate >= 0.85`
- `policy_replay_action_label == hindsight_best_management_action_label`

새 disposition:

- `hydration_gap_resolved_by_current_policy`

의미:

- baseline row는 비어 있지만
- current policy replay는 이미 hindsight와 맞음
- 그래서 high-priority review 대상이 아니라
  hydration 정리 대상으로 본다

## 기대 효과

- PA7 top queue에서 synthetic/backfill protective mismatch 축소
- hydration giant group이 실제 정책 mismatch와 분리됨
- review queue가 더 실제 경계 패치 쪽으로 정렬됨

## 검증

- `tests/unit/test_path_checkpoint_action_resolver.py`
- `tests/unit/test_path_checkpoint_dataset.py`
- `tests/unit/test_path_checkpoint_pa7_review_processor.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_exit_service.py`
