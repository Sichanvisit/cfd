# PA9 Handoff Review / Apply Scaffold

## 목표

`PA8 closeout` 이후 `PA9 action baseline handoff`가 바로 이어질 수 있도록,
기존 `handoff packet` 위에 `review packet`과 `apply packet`을 한 단계 더 올린다.

이번 단계의 목적은 `PA9`를 바로 live apply 하는 것이 아니라, 아래 흐름을 자동 갱신 상태로
만들어 두는 데 있다.

- `live window ready`
- `closeout review candidate 생성`
- `closeout apply`
- `PA9 handoff packet refresh`
- `PA9 handoff review/apply packet refresh`

## 추가된 산출물

- `checkpoint_improvement_pa9_action_baseline_handoff_packet_latest.json`
- `checkpoint_improvement_pa9_action_baseline_handoff_review_packet_latest.json`
- `checkpoint_improvement_pa9_action_baseline_handoff_apply_packet_latest.json`

## 서비스 구성

- `backend/services/checkpoint_improvement_pa9_handoff_packet.py`
  - symbol별 `activation_apply_state / closeout_state / live_observation_ready`를 읽어
    `handoff_state`를 요약한다.
- `backend/services/checkpoint_improvement_pa9_handoff_review_packet.py`
  - handoff packet을 읽어 `review_ready`와 `review_candidate_symbol_count`를 계산한다.
- `backend/services/checkpoint_improvement_pa9_handoff_apply_packet.py`
  - review packet을 읽어 `allow_apply`와 apply scaffold 상태를 요약한다.
- `backend/services/checkpoint_improvement_pa9_handoff_runtime.py`
  - handoff/review/apply 3개 packet을 한 번에 refresh하는 canonical runtime helper다.

## 자동 refresh 연결점

- `checkpoint_improvement_watch.py`
  - governance cycle이 돌 때 `PA8 canary refresh board`를 다시 읽고,
    이어서 `PA9 handoff runtime`도 함께 refresh한다.
- `checkpoint_improvement_pa8_apply_handlers.py`
  - activation / rollback / closeout apply 뒤에 `PA9 handoff runtime`을 함께 refresh한다.

즉 `PA8` 쪽 state가 바뀌면 `PA9` scaffold가 stale 상태로 오래 남지 않도록 묶여 있다.

## Master Board 반영

`checkpoint_improvement_master_board.py`는 이제 아래 상태를 함께 읽는다.

- `pa9_handoff_state`
- `pa9_review_state`
- `pa9_apply_state`
- `pa9_recommended_next_action`

특히 `prepared_symbol_count > 0`로 `PA9` review가 준비되면,
master board는 `pa8_live_window_pending`보다 `pa9_handoff_review_ready`를 우선 보여준다.

## 현재 해석

이번 단계로 가능한 것은 `PA9`의 review/apply scaffold 자동 갱신이다.
아직 남아 있는 것은 실제 `PA8 closeout`이 최소 1건 이상 나와야 `PA9` review/apply를
사람이 승인할 근거가 생긴다는 점이다.

즉 지금은:

- `배선`: 완료
- `review/apply scaffold`: 완료
- `최종 판단`: live row 이후
