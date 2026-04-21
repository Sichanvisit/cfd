# P5-2 PA8 Closeout Review/Apply 정밀화 상세

## 목표

`P5-1`의 집중 관찰 surface 위에 `PA8 closeout review/apply`를 한 단계 더 좁고 안전하게 올린다.

핵심은 아래 세 가지다.

- `closeout_decision`만으로 apply 하지 않는다.
- `closeout_review_packet -> closeout_apply_packet`을 다시 계산해 review/apply readiness를 확인한다.
- 실제 apply는 live window, sample floor, rollback trigger가 모두 안전할 때만 통과시킨다.

## 구현 범위

### 1. closeout packet 계층

- `checkpoint_improvement_pa8_closeout_review_packet.py`
  - 현재 canary refresh board를 읽어 closeout review 후보를 만든다.
  - `READY_FOR_MANUAL_PA8_CLOSEOUT_REVIEW`
  - `HOLD_PENDING_PA8_ROLLBACK`
  - `HOLD_PENDING_PA8_LIVE_WINDOW`
  - `HOLD_PENDING_PA8_SAMPLE_FLOOR`
  상태를 만든다.

- `checkpoint_improvement_pa8_closeout_apply_packet.py`
  - review packet을 읽어 apply 가능 여부를 만든다.
  - `READY_FOR_MANUAL_PA8_CLOSEOUT_APPLY_REVIEW`
  - `HOLD_PENDING_PA8_ROLLBACK`
  - `HOLD_PENDING_PA8_LIVE_WINDOW`
  - `HOLD_PENDING_PA8_SAMPLE_FLOOR`
  - `HOLD_PENDING_PA8_CLOSEOUT_REVIEW`
  상태를 만든다.

- `checkpoint_improvement_pa8_closeout_runtime.py`
  - review/apply packet을 한 번에 갱신하고 artifact를 남긴다.

### 2. apply guard 강화

`checkpoint_improvement_pa8_apply_handlers.py`의 `handle_closeout_review()`는 아래를 모두 다시 확인한다.

- `closeout_state == READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW`
- `live_observation_ready == true`
- `observed_window_row_count >= sample_floor`
- `active_trigger_count == 0`
- `review_packet.review_ready == true`
- `apply_packet.allow_apply == true`
- 해당 symbol이 `closeout_review_candidate == true`

위 조건 중 하나라도 안 맞으면 apply를 막고 handler error로 남긴다.

### 3. board / watch surface 보강

- governance summary에
  - `pa8_closeout_review_state`
  - `pa8_closeout_apply_state`
  를 같이 싣는다.

- master board에
  - `pa8_closeout_review_state`
  - `pa8_closeout_apply_state`
  를 summary/readiness/pa_state에 같이 surface한다.

## 산출물

- `checkpoint_improvement_pa8_closeout_review_packet_latest.json`
- `checkpoint_improvement_pa8_closeout_review_packet_latest.md`
- `checkpoint_improvement_pa8_closeout_apply_packet_latest.json`
- `checkpoint_improvement_pa8_closeout_apply_packet_latest.md`
- `checkpoint_improvement_pa8_closeout_runtime_latest.json`
- `checkpoint_improvement_pa8_closeout_runtime_latest.md`
- symbol별 `checkpoint_pa8_<symbol>_action_only_canary_closeout_apply_latest.json`

## 완료 조건

- closeout review/apply가 packet 기준으로 다시 계산된다.
- apply handler가 packet readiness를 다시 확인한다.
- board에서 `review/apply` 상태를 읽을 수 있다.
- false positive closeout apply가 guard로 차단된다.

## 다음 단계

이 단계가 닫히면 다음은 `P5-3 PA9 handoff 실제 승격축 정밀화`로 이어간다.
