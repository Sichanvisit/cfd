# Current B1 TelegramStateStore Detailed Plan

## 목적

이 문서는 `B1. TelegramStateStore`를 실제 구현 가능한 수준으로 좁혀서 정리한 상세 계획이다.

이번 단계의 핵심은 approval loop를 완성하는 것이 아니라,
그 전에 필요한 `하위 영속 저장소`를 먼저 닫는 것이다.

즉 B1은 아래를 담당한다.

- check group 기록
- event 기록
- action 기록
- telegram message 매핑
- poller offset 저장

상위 운영 상태는 여전히 [system_state_manager.py](/Users/bhs33/Desktop/project/cfd/backend/services/system_state_manager.py)가 맡고,
이번 저장소는 approval/message/offset의 하위 저장소 역할만 한다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_pre_orchestration_build_inventory_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_build_inventory_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_telegram_notification_hub_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_notification_hub_design_ko.md)

---

## 이번 단계의 목표

아래 5개 테이블을 가진 최소 SQLite store를 만든다.

- `check_groups`
- `check_events`
- `check_actions`
- `telegram_messages`
- `poller_offsets`

그리고 B2/B3에서 바로 사용할 수 있도록 아래 최소 API를 제공한다.

- `upsert_check_group()`
- `get_check_group()`
- `list_check_groups()`
- `append_check_event()`
- `append_check_action()`
- `upsert_telegram_message()`
- `get_telegram_message()`
- `set_poller_offset()`
- `get_poller_offset()`

---

## SystemStateManager와의 관계

이 경계는 이번 단계에서 꼭 고정한다.

- `SystemStateManager`
  - 상위 운영 상태의 진실 소스
  - phase / watch run / canary symbol state 담당
- `TelegramStateStore`
  - approval / message / offset 하위 저장소
  - callback 이력과 메시지 매핑 담당

즉 Telegram DB에 뭐가 저장되어 있어도 그게 곧 시스템 전체 상태를 대신하면 안 된다.

---

## 핵심 키 규약

이번 단계에서 컬럼으로 먼저 고정하는 운영 키는 아래다.

- `approval_id`
- `scope_key`
- `apply_job_key`
- `trace_id`
- `decision_deadline_ts`
- `supersedes_approval_id`

이 단계에서는 모든 키의 생성 규칙을 강제하지는 않지만,
store 레벨에서 저장할 자리를 먼저 만든다.

---

## 권장 DB 경로

- `data/runtime/telegram_hub.db`

이 파일은 approval/message/offset의 운영 기록장이다.

---

## 테이블별 목적

### 1. `check_groups`

비슷한 체크 요청을 묶는 대표 그룹.

핵심 컬럼:

- `group_id`
- `group_key`
- `status`
- `priority`
- `symbol`
- `side`
- `strategy_key`
- `check_kind`
- `action_target`
- `reason_fingerprint`
- `reason_summary`
- `review_type`
- `scope_key`
- `trace_id`
- `scope_note`
- `decision_deadline_ts`
- `apply_job_key`
- `supersedes_approval_id`
- `first_event_ts`
- `last_event_ts`
- `pending_count`
- `approved_by / approved_at`
- `rejected_by / rejected_at`
- `held_by / held_at`
- `expires_at`
- `created_at / updated_at`

### 2. `check_events`

그룹 아래에 들어가는 원본 이벤트 기록.

핵심 컬럼:

- `event_id`
- `group_id`
- `source_type`
- `source_ref`
- `symbol`
- `side`
- `payload_json`
- `event_ts`
- `trace_id`
- `created_at`

### 3. `check_actions`

텔레그램 callback 이력.

핵심 컬럼:

- `action_id`
- `group_id`
- `telegram_user_id`
- `telegram_username`
- `action`
- `note`
- `callback_query_id`
- `approval_id`
- `trace_id`
- `created_at`

### 4. `telegram_messages`

entity와 telegram message 매핑.

핵심 컬럼:

- `message_row_id`
- `entity_type`
- `entity_id`
- `route_key`
- `chat_id`
- `topic_id`
- `telegram_message_id`
- `message_kind`
- `content_hash`
- `is_editable`
- `created_at / updated_at`

### 5. `poller_offsets`

update poller offset 저장.

핵심 컬럼:

- `stream_key`
- `last_update_id`
- `updated_at`

---

## 이번 단계의 최소 동작 규칙

### 1. group은 `group_key` 기준 upsert

같은 `group_key`가 다시 들어오면 새 row를 늘리지 않고 기존 group을 갱신한다.

### 2. event는 append

event는 원본 이력이므로 append-only로 간다.
필요하면 `pending_count`와 `last_event_ts`를 같이 올린다.

### 3. action도 append

버튼 이력은 수정하지 않고 append-only로 남긴다.

### 4. telegram message는 entity 기준 upsert

같은 entity/route/message_kind 조합은 같은 row를 재사용하고 최신 telegram message id만 반영한다.

### 5. offset은 stream 기준 upsert

같은 stream은 한 줄만 유지한다.

---

## 이번 단계에서 아직 하지 않는 것

- approval transition 검증
- allowed user 검증
- callback idempotency full flow
- apply dispatch
- stale/expired cleanup

즉 B1은 저장소만 닫고, 상태기계는 B2에서 붙인다.

---

## 테스트 범위

이번 단계 테스트는 아래 정도면 충분하다.

1. 테이블 bootstrap
2. `check_group` insert + update
3. `check_event` append + pending count 반영
4. `check_action` append
5. `telegram_message` upsert
6. `poller_offset` upsert

---

## 완료 조건

- SQLite 파일이 자동 생성된다
- 핵심 테이블 5개가 존재한다
- B2/B3에서 바로 사용할 최소 CRUD가 있다
- unit test가 통과한다

---

## 다음 단계 연결

B1이 닫히면 다음 순서는 아래가 가장 자연스럽다.

1. `B2. ApprovalLoop`
2. `B3. ApplyExecutor`

즉 B1은 approval loop가 의존할 `기록장과 메시지 매핑 저장소`를 먼저 만드는 단계다.
