# Current C1 Checkpoint Improvement Master Board Detailed Plan

## 목적

`C1 Master Board`는 새 판단 엔진이 아니라, 이미 있는 신호를 한 장으로 묶는 `canonical operations snapshot`이다.

이번 단계의 목표는 아래 5개 축을 하나의 보드로 합치는 것이다.

- `SystemStateManager`
- `checkpoint_improvement_watch` latest report
- `PA8 canary refresh board`
- `PA78 review packet`
- `TelegramStateStore` approval/apply backlog

즉 `C1`은 오케스트레이터 이전에 사람이 지금 상태를 빠르게 읽고, 이후 `checkpoint_improvement_watch`와 `OrchestratorLoop`가 공통으로 참고할 수 있는 기준 보드를 만드는 단계다.

## 범위

### 이번 C1에서 하는 것

- `checkpoint_improvement_master_board.py` 추가
- `checkpoint_improvement_master_board_latest.json`
- `checkpoint_improvement_master_board_latest.md`
- 보드용 최소 필드 고정
- backlog / degrade / next action 계산

### 이번 C1에서 하지 않는 것

- 새로운 PA/SA 판단 로직 추가
- reconcile 실행기 구현
- 오케스트레이터 통합
- Telegram 실제 API 전송

## 입력 소스

### 1. system state

- `phase`
- `last_row_ts`
- `row_count_since_boot`
- `light_last_run`
- `heavy_last_run`
- `governance_last_run`
- `pa8_symbols`
- `telegram_healthy`
- `last_error`

### 2. watch report

- `cycle_name`
- `trigger_state`
- `recommended_next_action`
- `generated_at`

### 3. PA8 canary board

- `active_symbol_count`
- `live_observation_ready_count`
- `recommended_next_action`

### 4. PA78 review packet

- `pa7_unresolved_review_group_count`
- `pa7_review_state`
- `pa8_review_state`
- `scene_bias_review_state`
- `recommended_next_action`

### 5. Telegram approval/apply 상태

- group status counts
- pending / held backlog
- approved apply backlog
- oldest pending age
- last successful apply timestamp

## 출력 계약

### summary

필수 필드:

- `contract_version`
- `generated_at`
- `trigger_state`
- `recommended_next_action`
- `phase`
- `blocking_reason`
- `next_required_action`
- `active_pa8_symbol_count`
- `live_window_ready_count`
- `pending_approval_count`
- `held_approval_count`
- `approved_apply_backlog_count`
- `oldest_pending_approval_age_sec`
- `last_successful_apply_ts`
- `degraded_components`
- `reconcile_backlog_count`

### 세부 섹션

- `system_state`
- `watch_state`
- `pa_state`
- `approval_state`
- `health_state`
- `orchestrator_contract`
- `artifacts`

### orchestrator_contract

이 섹션은 이후 `OrchestratorLoop`가 그대로 읽는 기계용 contract다.

필드:

- `phase`
- `phase_allows_progress`
- `reconcile_signal`
- `approval_backlog_count`
- `apply_backlog_count`
- `reconcile_backlog_count`
- `blocking_reason`
- `next_required_action`
- `degraded_components`
- `telegram_healthy`
- `watch_cycle_name`
- `watch_trigger_state`
- `active_pa8_symbol_count`
- `live_window_ready_count`

## blocking_reason 우선순위

보드는 한 번에 여러 문제가 있어도 가장 먼저 볼 이유를 하나로 압축해야 한다.

우선순위는 아래 순서로 고정한다.

1. `system_phase_emergency`
2. `system_phase_degraded`
3. `approved_apply_backlog`
4. `approval_backlog_pending`
5. `pa7_review_backlog`
6. `pa8_live_window_pending`
7. `none`

## next_required_action 규칙

### emergency / degraded

- `inspect_degraded_components_and_restore_dependencies`

### approved apply backlog

- `drain_approved_apply_backlog_before_new_governance_reviews`

### approval backlog

- `process_pending_or_held_governance_reviews_in_telegram`

### PA7 backlog

- `PA78 review packet`의 `recommended_next_action` 우선 사용

### PA8 live window pending

- `PA8 canary board`의 `recommended_next_action` 우선 사용

### blocker 없음

- `watch -> PA78 -> PA8` 순서로 `recommended_next_action`을 fallback 사용

## degraded_components 규칙

최소 v0에서는 아래만 본다.

- `system_phase:degraded`
- `system_phase:emergency`
- `telegram`
- `watch:<cycle_name>`

즉 보드는 아직 health monitor 전체가 아니라, 지금 복구 판단에 직접 쓰는 신호만 보여준다.

## reconcile_backlog_count 규칙

`C1`은 reconcile executor를 아직 만들지 않았으므로, backlog만 보수적으로 계산한다.

v0 구성:

- `approved_apply_backlog_count`
- `stale_actionable_count`

즉:

`reconcile_backlog_count = approved_apply_backlog_count + stale_actionable_count`

## 구현 단위

### 새 파일

- `backend/services/checkpoint_improvement_master_board.py`
- `tests/unit/test_checkpoint_improvement_master_board.py`

### 산출물

- `data/analysis/shadow_auto/checkpoint_improvement_master_board_latest.json`
- `data/analysis/shadow_auto/checkpoint_improvement_master_board_latest.md`

## 테스트 기준

### 1. 운영 요약 생성

- state / watch / pa8 / pa78 / approval store를 합쳐 board를 만든다
- pending backlog / last apply ts / next action이 맞게 계산된다

### 2. degraded 우선순위

- system phase degraded + telegram unhealthy + watch error일 때
- `blocking_reason = system_phase_degraded`
- degraded components가 모두 잡힌다

### 3. reconcile backlog 계산

- approved apply backlog
- stale held approval
- 둘이 합쳐 `reconcile_backlog_count`가 계산된다

## 완료 기준

`C1` 완료는 아래를 의미한다.

- board 서비스가 실제 JSON/MD를 만든다
- 현재 phase / backlog / PA 상태 / next action이 한 장에 보인다
- `checkpoint_improvement_watch` 이후 단계가 board를 canonical snapshot으로 사용할 수 있다

한 줄로 정리하면,

`C1 Master Board`는 오케스트레이션 전 단계에서 “지금 어디가 막혔고 다음에 뭘 해야 하는지”를 한 장으로 보여주는 운영 기준판이다.
