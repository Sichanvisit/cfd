# BC8 State25 Weight Bounded Live 상세 계획

## 목표

state-first context bridge가 만든 `weight` 조정 후보를 더 이상 trace/log-only에만 두지 않고,
`state25` 실행 본체가 아주 좁은 범위에서 실제로 읽을 수 있는 bounded live 계약으로 연결한다.

이번 단계의 핵심은 새 엔진을 만드는 것이 아니라, 기존 state25 실행 경로가 이미 갖고 있는
`teacher_weight_overrides`를 `bounded_live` 모드에서만 실제 소비하도록 경계를 분명히 하는 것이다.

## 현재 상태

- BC2까지: bridge가 `weight_adjustments_requested/effective/suppressed`를 계산한다.
- BC3~BC4까지: runtime trace와 `/detect -> /propose` review 후보가 올라온다.
- BC5 overlap guard refinement까지: 같은 runtime hint 중복 때문에 weight review가 blanket suppression되던 문제를 줄였다.
- 아직 부족했던 점:
  - active candidate state에 `bounded_live` weight를 써도 실제 runtime hint로 흘러가는 경로가 분명하지 않았다.
  - apply handler가 `bounded_live`를 쓰더라도 contract/trace가 충분히 정리되지 않았다.

## 이번 단계에서 닫는 것

1. active candidate state contract에 `state25_weight_bounded_live_enabled`를 포함한다.
2. `state25_weight_patch_apply_handlers.py`가 `log_only`와 `bounded_live`를 모두 처리한다.
3. `forecast_state25_runtime_bridge.py`는 `log_only_teacher_weight_overrides`가 아니라
   `live_teacher_weight_overrides`만 실제 runtime hint 입력으로 사용한다.
4. review packet builder는 `state25_execution_bind_mode=bounded_live`를 표현할 수 있다.

## 실제 소비 규칙

- `log_only`
  - review/backlog/trace에는 보인다.
  - live runtime hint에는 직접 반영하지 않는다.
- `bounded_live`
  - symbol scope, entry stage scope를 만족하는 경우에만 live runtime hint 입력으로 전달한다.
  - 기존 state25 방향 결정을 강제로 뒤집지 않고, teacher pattern 해석 비중만 미세 조정한다.

## 구현 파일

- `backend/services/teacher_pattern_active_candidate_runtime.py`
- `backend/services/state25_weight_patch_apply_handlers.py`
- `backend/services/state25_weight_patch_review.py`
- `backend/services/forecast_state25_runtime_bridge.py`
- `backend/services/checkpoint_improvement_telegram_runtime.py`

## 운영 메모

- 이번 단계는 bounded live **소비 경로**와 **apply contract**를 닫는 단계다.
- 아직 자동으로 bounded live review를 무조건 승격시키지는 않는다.
- 즉 지금은
  - `review payload가 bounded_live를 명시하면 apply 가능`
  - `apply 후에는 실제 runtime hint에 bounded_live weight가 반영`
  상태까지 닫힌 것으로 본다.

## 검증 포인트

- active candidate state가 `bounded_live`일 때 `live_teacher_weight_overrides`가 비지 않아야 한다.
- `forecast_state25_runtime_bridge_v1`가 log-only override를 live 입력으로 쓰지 않아야 한다.
- weight bounded live apply 이후 `current_binding_mode = bounded_live`와
  `current_rollout_phase = bounded_live`가 기록돼야 한다.
