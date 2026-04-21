# Current B3 ApplyExecutor Detailed Plan

## 목적

이 문서는 `B3. ApplyExecutor`를 실제 구현 가능한 수준으로 고정하는 상세 계획이다.

이번 단계의 목표는 `ApprovalLoop`가 승인 완료한 review를
실제 bounded apply handler로 안전하게 넘기고,
중복 집행 없이 `applied` 상태까지 기록하는 것이다.

즉 아직 `오케스트레이터 전체 완성` 단계는 아니고,
`승인 상태기계 -> 집행기` 연결을 먼저 닫는 단계다.

이 문서는 아래 문서를 함께 기준으로 본다.

- [current_b1_telegram_state_store_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b1_telegram_state_store_detailed_plan_ko.md)
- [current_b2_approval_loop_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_b2_approval_loop_detailed_plan_ko.md)
- [current_pre_orchestration_foundation_execution_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_pre_orchestration_foundation_execution_roadmap_ko.md)
- [current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_checkpoint_improvement_watch_orchestration_detailed_design_ko.md)
- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)

---

## 이번 단계의 한 줄 목표

`ApprovalReceived` 또는 그와 동등한 approval payload를 받아
`approved` 상태인 group만 실제 apply handler로 넘기고,
성공 시 `applied`로 마감할 수 있게 만든다.

---

## ApplyExecutor의 역할

ApplyExecutor는 아래만 책임진다.

- approval payload 검증
- group이 실제로 `approved` 상태인지 확인
- review type별 handler dispatch
- duplicate apply 방지
- apply action history 기록
- group status를 `applied`로 전이

ApplyExecutor가 하지 않는 일:

- approval 결정 자체
- 텔레그램 callback 처리
- 텔레그램 메시지 전송
- watch candidate 생성
- 상위 phase 변경

즉 ApplyExecutor는 `집행반`이지 `승인반`도 `반장`도 아니다.

---

## v0 지원 review type

- `CANARY_ACTIVATION_REVIEW`
- `CANARY_ROLLBACK_REVIEW`
- `CANARY_CLOSEOUT_REVIEW`

이 세 가지가 현재 PA8 bounded canary governance 축의 핵심이다.

---

## handler dispatch 원칙

이번 단계에서 ApplyExecutor는 review type별 handler를 직접 내장하지 않는다.
대신 아래 구조로 간다.

- executor는 `review_type -> handler` 맵을 받는다
- handler는 실제 symbol/scope별 bounded apply 의미를 구현한다
- executor는 그 결과를 받아 상태만 정리한다

즉 executor는 `무엇을 집행할지`를 몰라도 되고,
`집행 조건과 기록을 관리하는 책임`만 진다.

이렇게 해야 이후
- NAS 전용 activation apply
- BTC/XAU symbol bundle apply
- closeout/handoff apply
를 같은 집행기 위에 얹을 수 있다.

---

## 필수 보호 규칙

### 1. approved 상태가 아니면 집행 금지

- group status가 `approved`가 아니면 집행하지 않는다
- `held / rejected / expired / pending` 모두 거부

### 2. approve decision이 아니면 집행 금지

- decision이 `approve`가 아닌 payload는 집행하지 않는다
- hold/reject는 상태만 유지하고 apply하지 않는다

### 3. review type handler가 없으면 집행 금지

- handler가 등록되지 않은 review type은 `NO_APPLY_HANDLER`

### 4. duplicate apply 방지

- 이미 같은 `approval_id`로 `apply` action이 기록돼 있으면 무시
- 또는 group status가 이미 `applied`면 무시

### 5. handler 실패 시 상태 오염 금지

- handler가 예외를 던지면
  - group status는 그대로 `approved`
  - apply action은 기록하지 않는다

---

## 입력 payload 최소 필드

executor가 읽는 최소 approval payload:

- `group_id`
- `review_type`
- `decision`
- `approval_id`
- `apply_job_key`
- `trace_id`

이 중 `group_id`와 `review_type`, `decision`은 사실상 필수다.

---

## 결과 payload 권장 shape

ApplyExecutor 반환 payload는 아래를 가진다.

- `summary`
  - `trigger_state`
  - `recommended_next_action`
  - `group_id`
  - `group_key`
  - `review_type`
  - `decision`
- `group_before`
- `group_after`
- `approval_event`
- `apply_record`
- `apply_result`
- `decision_result`

대표 trigger state:

- `APPLY_EXECUTED`
- `GROUP_NOT_FOUND`
- `GROUP_NOT_APPROVED`
- `DECISION_NOT_APPLICABLE`
- `UNSUPPORTED_REVIEW_TYPE`
- `NO_APPLY_HANDLER`
- `DUPLICATE_APPLY_IGNORED`
- `HANDLER_ERROR`

---

## TelegramStateStore와의 관계

ApplyExecutor는 아래 store API를 사용한다.

- `get_check_group()`
- `list_check_actions()`
- `append_check_action()`
- `update_check_group()`

핵심은:

- executor는 action history를 append-only로 남긴다
- success 시에만 `apply` action을 기록한다
- 성공 후 group status는 `applied`로 닫는다

---

## B2와의 연결

흐름은 아래처럼 이어진다.

`ApprovalLoop -> ApprovalReceived -> ApplyExecutor`

즉 B2가 `approved`를 만들고,
B3가 그 approved를 실제 집행으로 옮긴다.

---

## v0에서 아직 하지 않는 것

- multi-symbol 동시 apply orchestration
- retry queue
- apply failure auto-recovery
- handler 결과를 상위 state manager에 반영
- apply result event 추가 발행

이건 이후 watch/orchestrator 단계에서 붙인다.

---

## 테스트 범위

이번 단계 테스트는 아래를 반드시 덮는다.

1. approved group 집행 성공 -> `applied`
2. non-approved group 집행 거부
3. non-approve decision 집행 거부
4. handler 미등록 거부
5. duplicate apply 무시
6. handler error 시 상태 오염 방지

즉 초반엔 집행 성공보다 `잘못된 집행 방지`를 먼저 잠근다.

---

## 완료 조건

- approved group만 apply 가능하다
- apply 성공 시 `apply` action이 기록된다
- group status가 `applied`로 닫힌다
- duplicate apply가 무시된다
- handler error가 상태를 더럽히지 않는다
- unit test가 통과한다

---

## 다음 단계 연결

B3가 닫히면 다음은 자연스럽게 `B4. Telegram approval bridge`다.

즉 구조는 이렇게 연결된다.

`watch -> GovernanceActionNeeded -> Telegram review card -> ApprovalLoop -> ApplyExecutor`
