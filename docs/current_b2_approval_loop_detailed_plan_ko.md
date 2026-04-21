# Current B2 ApprovalLoop Detailed Plan

## 목적

이 문서는 `B2. ApprovalLoop`를 실제 구현 가능한 수준으로 고정하는 상세 계획이다.

이번 단계의 목표는 `텔레그램 callback -> 승인 상태 전이 -> 이벤트 발행`까지를 닫는 것이다.
즉 아직 실제 bounded apply를 수행하는 단계는 아니고,
`승인 상태기계`를 먼저 안정적으로 만드는 단계다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_b1_telegram_state_store_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b1_telegram_state_store_detailed_plan_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)

---

## 이번 단계의 한 줄 목표

`pending / held` 상태의 review group에 대해,
허용된 사용자의 callback만 받아
`approved / held / rejected / expired`로 전이시키고
그 결과를 event로 올릴 수 있게 만든다.

---

## ApprovalLoop의 역할

ApprovalLoop는 아래만 책임진다.

- callback payload 해석
- allowed user 검증
- duplicate callback 멱등 처리
- deadline 만료 처리
- group status transition
- action history 기록
- `ApprovalReceived` event 발행

ApprovalLoop가 하지 않는 일:

- 텔레그램 메시지 전송
- 실제 canary activation / rollback / closeout apply
- 운영 상태 phase 변경

즉 ApprovalLoop는 `승인 기록반`이지 `집행반`이 아니다.

---

## v0 지원 상태

### 지원하는 입력 decision

- `approve`
- `hold`
- `reject`

### 상태 전이

- `pending -> approved`
- `pending -> held`
- `pending -> rejected`
- `pending -> expired`
- `held -> approved`
- `held -> held`
- `held -> rejected`
- `held -> expired`

### 아직 하지 않는 것

- `applied` 전이
  - 이건 `ApplyExecutor`가 맡는다.
- `reopen / refresh`
  - 추후 reconcile 또는 운영 보강 단계에서 다룬다.

---

## 지원하는 review type

v0에서는 아래 review type을 우선 지원한다.

- `CANARY_ACTIVATION_REVIEW`
- `CANARY_ROLLBACK_REVIEW`
- `CANARY_CLOSEOUT_REVIEW`

즉 지금 ApprovalLoop는 PA8 bounded canary governance 축에 먼저 맞춘다.

---

## 필수 운영 키

이번 단계에서 실제로 읽고/기록하는 운영 키는 아래다.

- `approval_id`
- `scope_key`
- `apply_job_key`
- `trace_id`
- `decision_deadline_ts`
- `supersedes_approval_id`

핵심 원칙:

- `approval_id`가 다르면 stale callback로 본다
- `callback_query_id`가 이미 처리된 이력이 있으면 duplicate로 본다
- `decision_deadline_ts`가 지났으면 먼저 `expired`로 전이한다

---

## TelegramStateStore와의 관계

ApprovalLoop는 아래 저장소를 사용한다.

- `check_groups`
- `check_actions`

필요 최소 store API:

- `get_check_group()`
- `get_check_action_by_callback_query_id()`
- `append_check_action()`
- `update_check_group()`
- `list_check_actions()`

중요:

- ApprovalLoop는 하위 저장소를 읽고 쓴다
- 하지만 상위 운영 phase는 직접 바꾸지 않는다
- 상위 phase는 여전히 `SystemStateManager`가 맡는다

---

## EventBus와의 관계

ApprovalLoop는 transition이 성공했을 때만 `ApprovalReceived` event를 발행한다.

event payload 최소 필드:

- `group_id`
- `group_key`
- `review_type`
- `scope_key`
- `approval_id`
- `apply_job_key`
- `decision`
- `previous_status`
- `next_status`
- `telegram_user_id`
- `telegram_username`

중요:

- `expired`는 callback 기반 승인 수신이 아니라 만료 정리이므로
  v0에서는 별도 event를 강제하지 않는다
- apply는 event를 받은 다음 단계에서 결정된다

---

## 필수 보호 규칙

### 1. allowed user 검증

- 허용 user set이 비어 있으면 모두 허용
- 비어 있지 않으면 whitelist에 있는 user만 처리
- 실패 시 group/status/action을 건드리지 않는다

### 2. duplicate callback 멱등 처리

- 동일 `callback_query_id`가 이미 기록되어 있으면
  두 번째 요청은 무시한다
- 기존 action record만 되돌려준다

### 3. stale approval 차단

- 현재 group의 `approval_id`와 callback의 `approval_id`가 다르면
  stale callback로 보고 무시한다

### 4. deadline expire 우선

- callback 시점에 `decision_deadline_ts`가 이미 지났으면
  decision을 적용하지 않고 먼저 `expired`로 전이한다

---

## 결과 payload 권장 shape

ApprovalLoop의 반환 payload는 아래 섹션을 가진다.

- `summary`
  - `trigger_state`
  - `recommended_next_action`
  - `group_id`
  - `group_key`
  - `decision`
  - `event_count`
- `group_before`
- `group_after`
- `action_record`
- `decision_result`

대표 trigger state:

- `APPROVAL_RECORDED`
- `UNAUTHORIZED_USER`
- `DUPLICATE_CALLBACK_IGNORED`
- `APPROVAL_ID_MISMATCH`
- `APPROVAL_EXPIRED`
- `GROUP_STATUS_NOT_ACTIONABLE`
- `GROUP_NOT_FOUND`

---

## 테스트 범위

이번 단계 테스트는 아래를 반드시 덮는다.

1. `pending -> approved` 성공 전이
2. unauthorized user 차단
3. duplicate callback idempotency
4. stale approval id 차단
5. overdue deadline -> expired
6. `held -> approved` 허용

즉 happy path보다 운영 꼬임 방지를 먼저 잠근다.

---

## 완료 조건

- ApprovalLoop가 callback을 받아 상태 전이를 처리한다
- duplicate callback이 멱등하게 무시된다
- approval_id mismatch가 stale callback로 차단된다
- deadline 만료가 `expired`로 반영된다
- `ApprovalReceived` event가 성공 전이에만 발행된다
- unit test가 통과한다

---

## 다음 단계 연결

B2가 닫히면 다음은 자연스럽게 `B3. ApplyExecutor`다.

즉 구조는 이렇게 이어진다.

`watch -> GovernanceActionNeeded -> Telegram approval -> ApprovalLoop -> ApprovalReceived -> ApplyExecutor`
