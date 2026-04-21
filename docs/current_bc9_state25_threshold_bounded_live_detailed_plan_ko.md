# BC9 State25 Threshold Bounded Live 상세 계획

## 목표

threshold bridge가 계산한 `HARDEN` delta를 log-only trace에서 끝내지 않고,
state25 entry threshold에 bounded live로 실제 반영할 수 있는 signed contract를 닫는다.

핵심은 `threshold live contract -> apply handler -> entry_try_open_entry 실제 소비`
이 세 고리를 모두 연결하는 것이다.

## 현재 상태

- BC6: threshold log-only translator가 requested/effective/suppressed를 계산한다.
- BC7: threshold review lane이 `/detect -> /propose`에 surface된다.
- 아직 부족했던 점:
  - threshold 승인 후 active candidate state에 bounded live patch를 쓰는 apply handler가 없었다.
  - entry path가 bounded live threshold를 실제 `dynamic_threshold`에 반영하는 계약이 명확하지 않았다.

## 이번 단계에서 닫는 것

1. active candidate state contract에
   - `state25_threshold_bounded_live_enabled`
   - `state25_threshold_bounded_live_delta_points`
   - `state25_threshold_bounded_live_direction`
   - `state25_threshold_bounded_live_reason_keys`
   를 정리한다.
2. `state25_threshold_patch_apply_handlers.py`를 추가한다.
3. `entry_try_open_entry.py`가 bounded live threshold delta를 실제 `dynamic_threshold`에 반영한다.
4. runtime row에
   - before/after threshold
   - delta
   - direction
   을 남긴다.

## 실제 소비 규칙

- v1은 `HARDEN only`
- bounded live가 켜져 있어도
  - symbol scope hit
  - entry stage scope hit
  를 만족해야만 실제 적용된다.
- semantic live guard보다 먼저 state25 bounded live threshold를 반영하고,
  그 뒤 semantic live guard가 추가 threshold를 더할 수 있다.

## 구현 파일

- `backend/services/teacher_pattern_active_candidate_runtime.py`
- `backend/services/state25_threshold_patch_apply_handlers.py`
- `backend/services/state25_threshold_patch_review.py`
- `backend/services/entry_try_open_entry.py`
- `backend/services/checkpoint_improvement_telegram_runtime.py`

## 운영 메모

- 이번 단계는 bounded live threshold **실행 계약**을 닫는 단계다.
- review lane은 여전히 log-only 중심으로 유지할 수 있지만,
  apply payload가 `bounded_live`를 명시하면 실제 threshold harden이 entry path에 반영된다.
- 즉 지금은
  - `review/log-only`
  - `bounded live apply`
  를 둘 다 표현할 수 있는 상태가 된다.

## 검증 포인트

- threshold bounded live apply 이후 active candidate state가 `bounded_live`로 전환된다.
- entry path runtime row에 `state25_candidate_live_threshold_before/after/delta/direction`이 찍힌다.
- symbol/stage scope가 맞지 않으면 bounded live threshold는 적용되지 않는다.
