# PA7 Round 2: Protective Reclaim Wait Expansion

## 목적

`PA7 review processor` 기준 최상위 mismatch group은 여전히 아래 family에 집중되어 있었다.

- `protective_exit_surface`
- `RECLAIM_CHECK`
- `active_open_loss` 또는 `open_loss_protective`
- baseline `PARTIAL_EXIT`
- hindsight `WAIT`

Round 1 패치 이후에도 같은 family가 남았지만, 남은 row를 다시 보면 대부분이 동일한 패턴을 보였다.

- `FULL_EXIT` score leader였지만 gate 미통과
- `current_profit < 0`
- `giveback_ratio ~= 0.99`
- `continuation > reversal`
- `hold_quality`가 `partial_exit_ev`와 비슷하거나 더 높음
- source는 거의 전부 `exit_manage_hold`

즉 이 구간은 “즉시 trim”보다 “reclaim retest wait”로 보는 편이 현재 hindsight에 더 잘 맞는다.

## Round 2 규칙

`path_checkpoint_action_resolver.py`

`top_label == FULL_EXIT and not full_exit_allowed` fallback 안에서:

- `surface_name == protective_exit_surface`
- `checkpoint_type == RECLAIM_CHECK`
- `row_family in {active_open_loss, open_loss_protective}`
- `current_profit < 0`
- `continuation >= reversal + 0.08`
- `hold_score >= max(partial_score - 0.02, 0.33)`

를 만족하면:

- `WAIT`
- reason: `protective_reclaim_open_loss_wait_retest`

으로 보정한다.

## 의도

이 패치는 `active_open_loss/open_loss_protective`의 모든 open-loss row를 바꾸는 것이 아니다.

오직 아래 조건에만 적용한다.

- protective surface
- reclaim check
- `FULL_EXIT` gate는 이미 실패함
- continuation 쪽이 아직 우세함

즉 “위험하니 full exit는 보고 있었지만, gate를 못 넘었고, 그렇다고 trim도 hindsight상 과했던 reclaim-loss retest 구간”만 더 좁게 WAIT로 눌러주는 패치다.

## 기대 효과

- `NAS100/BTCUSD/XAUUSD` 공통의 top mismatch group 감소
- `PA7 review processor`의 1순위 group 축소
- 다음 review 대상이 `runner-secured trim mismatch`나 `backfill HOLD/WAIT` 계열로 자연스럽게 올라오도록 정리

## 검증

- resolver unit test
- dataset runtime-proxy unit test
- `build_checkpoint_dataset.py`
- `build_checkpoint_eval.py`
- `build_checkpoint_pa7_review_queue_packet.py`
- `build_checkpoint_pa7_review_processor.py`
