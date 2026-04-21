# P5-3 PA9 Handoff Precision And PA7 Backlog Narrowing

## 목표

- `PA9 handoff`를 packet 수준이 아니라 `review -> approval -> apply -> applied artifact`까지 닫는다.
- `PA7 backlog`는 전체 기준을 완화하지 않고, 실제로 의미가 약한 경계군만 좁게 줄인다.

## 이번에 반영한 것

### 1. PA9 handoff 승격축 정밀화

- `PA9_ACTION_BASELINE_HANDOFF_REVIEW` review type을 추가했다.
- governance cycle이 `PA9 handoff review ready`일 때 check/report에 review 후보를 올릴 수 있게 했다.
- approval 후에는 `checkpoint_improvement_pa9_apply_handlers.py`가 실제 apply를 집행한다.
- apply 시:
  - symbol review/apply candidate 검증
  - `PA9_HANDOFF_PREPARED_ACTION_ONLY_CANARY -> PA9_ACTION_BASELINE_HANDOFF_APPLIED`
  - symbol별 handoff apply artifact 기록
  - PA9 runtime 재계산
  - PA8 canary refresh board 재생성

### 2. PA9 runtime/applied state surface

- handoff packet이 symbol별 `handoff_apply_state`를 읽는다.
- review/apply packet도 `already applied` 상태를 이해한다.
- runtime 최신 artifact를 별도로 남긴다.

### 3. PA7 backlog 좁은 자동 정리

- `protective_exit_surface / LATE_TREND_CHECK / WAIT hindsight`
- `PARTIAL_EXIT baseline/policy`
- `avg_abs_current_profit <= 0.10`
- `avg_giveback_ratio >= 0.95`

위 조건은 실제로는 `near-flat wait boundary`에 가까워서,
전체 정책 mismatch가 아니라 이미 안전하게 de-risked 된 경계군으로 본다.

즉:
- rule 완화 아님
- closeout 기준 완화 아님
- 매우 좁은 `safe partial de-risk`만 backlog에서 제외

## 산출물

- `checkpoint_improvement_pa9_action_baseline_handoff_runtime_latest.json`
- `checkpoint_pa9_<symbol>_action_baseline_handoff_apply_latest.json`
- refreshed `checkpoint_pa7_review_processor_latest.json`
- refreshed `checkpoint_pa78_review_packet_latest.json`

## 현재 확인 결과

- `PA9 handoff`는 여전히 `HOLD_PENDING_PA8_LIVE_WINDOW`
- 즉 승격 경로는 닫혔지만 live evidence가 아직 부족하다
- `PA7 unresolved review group count`는 `3 -> 2`로 감소했다

## 해석

- 이번 단계는 `승격축`을 더 안전하게 만들었다
- 동시에 `PA7 backlog`를 억지로 지우지 않고, 실제로 의미가 약한 한 덩어리만 줄였다
- 남은 backlog는 이제 더 실질적인 `WAIT/HOLD 경계`이므로 함부로 자동 정리하지 않는 편이 맞다

## 다음 단계

- `P5-4 actual first symbol closeout/handoff run`
- 또는 남은 `mixed_wait_boundary_review / mixed_review`를 별도 narrow review lane으로 surface
