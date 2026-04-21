# Current C2 Checkpoint Improvement Reconcile Placeholder Detailed Plan

## 목적

`C2 reconcile placeholder`는 아직 자동 복구기가 아니다.

이번 단계의 목적은 아래 두 가지다.

- 무엇이 `reconcile backlog`인지 canonical하게 식별한다
- 이후 `OrchestratorLoop`가 읽을 health/backlog 축을 `C1 Master Board` 기준으로 고정한다

즉 `C2`는 실제로 DB를 고치는 단계가 아니라, `무엇이 꼬였는지 먼저 보이게 만드는 단계`다.

## 범위

### 이번 C2에서 하는 것

- `checkpoint_improvement_reconcile.py` 추가
- `checkpoint_improvement_reconcile_latest.json`
- `checkpoint_improvement_reconcile_latest.md`
- `SystemStateManager`에 `reconcile_last_run` 추가
- `C1 Master Board`에 `orchestrator_contract` 축 고정

### 이번 C2에서 하지 않는 것

- approval 자동 만료 실행
- stale group 자동 재오픈
- message mapping 자동 복구
- late callback 자동 무효화

이런 규칙은 이후 운영 로그를 보면서 순차적으로 추가한다.

## reconcile placeholder가 읽는 기준

### 1. C1 Master Board

여기서 아래 축을 canonical하게 읽는다.

- `blocking_reason`
- `next_required_action`
- `approval_backlog_count`
- `apply_backlog_count`
- `reconcile_backlog_count`
- `degraded_components`

### 2. TelegramStateStore

placeholder가 직접 세는 실제 그룹:

- `pending / held` 중 deadline이 지난 actionable group
- `approved` 상태인데 아직 `applied`가 아닌 group

## orchestrator_contract

`C1 Master Board`는 이제 사람이 보기 위한 보드일 뿐 아니라, 이후 `OrchestratorLoop`가 읽는 canonical contract도 같이 제공한다.

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

한 줄로 말하면:

`C1 summary`는 사람용, `orchestrator_contract`는 기계용이다.

## reconcile placeholder 출력

### summary

- `trigger_state`
- `recommended_next_action`
- `approval_backlog_count`
- `apply_backlog_count`
- `reconcile_signal`

### reconcile_summary

- `stale_actionable_count`
- `approved_not_applied_count`
- `same_scope_conflict_count`
- `late_callback_invalidation_count`
- `recommended_next_action`

### 세부 목록

- `stale_actionable_groups`
- `approved_not_applied_groups`

## recommended_next_action 규칙

우선순위:

1. `approved_not_applied_count > 0`
   - `inspect_apply_backlog_and_drain_executor_before_new_reviews`
2. `stale_actionable_count > 0`
   - `expire_or_reopen_stale_governance_approvals_before_new_reviews`
3. 그 외
   - board의 `next_required_action` fallback

## 테스트 기준

### 1. no signal

- backlog 없음
- reconcile signal 없음
- `SKIP_WATCH_DECISION`

### 2. backlog 있음

- stale held group 존재
- approved-not-applied group 존재
- `RECONCILE_PLACEHOLDER_REFRESHED`
- `reconcile_last_run` 갱신

### 3. board builder 오류

- `WATCH_ERROR`
- `SystemStateManager -> DEGRADED`
- `WatchError` 발행

## 완료 기준

`C2` 완료는 아래를 의미한다.

- reconcile cycle이 canonical backlog를 읽고 placeholder report를 만든다
- `C1 Master Board`가 사람용 보드이면서 오케스트레이터 입력 계약도 같이 제공한다
- 이후 `OrchestratorLoop`는 새 health/backlog 축을 그대로 읽어도 된다

한 줄로 정리하면,

`C2`는 아직 자동 수리 단계가 아니라, 자동 수리가 필요해질 backlog를 정확하게 식별하고 오케스트레이터가 읽을 공통 계약을 먼저 고정하는 단계다.
