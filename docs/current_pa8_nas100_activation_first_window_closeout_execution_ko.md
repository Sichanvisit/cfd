# PA8 NAS100 Activation / First Window / Closeout Execution

## 목표

- NAS100 action-only canary를 사람이 승인한 상태로 실제 apply한다.
- canary first window를 시작하고, post-activation live row가 없을 때는 preview seed를 기준 reference로 남긴다.
- closeout 판단은 낙관적으로 서두르지 않고, live row가 쌓이기 전에는 `HOLD_CLOSEOUT_PENDING_LIVE_WINDOW`로 둔다.

## 이번 단계에서 추가하는 것

- `activation apply`
  - review packet을 실제 승인 상태로 바꾸고 active state를 남긴다.
- `first window observation`
  - post-activation scoped row가 있으면 live 관찰값으로 누적한다.
  - 아직 없으면 preview 결과를 seed reference로 둔다.
- `closeout decision`
  - 활성 상태, trigger, sample floor, live row 존재 여부를 함께 보고 보수적으로 결정한다.

## 중요한 원칙

- 이번 단계는 `scene bias`를 여전히 건드리지 않는다.
- action-only NAS100 slice만 본다.
- preview seed는 live 결과를 대신하지 않는다.
- live row가 아직 없으면 closeout은 진행하지 않고 `보류`가 정답이다.

## 기대 산출물

- `checkpoint_pa8_nas100_action_only_canary_activation_apply_latest.json/md`
- `checkpoint_pa8_nas100_action_only_canary_active_state_latest.json`
- `checkpoint_pa8_nas100_action_only_canary_first_window_observation_latest.json/md`
- `checkpoint_pa8_nas100_action_only_canary_closeout_decision_latest.json/md`
