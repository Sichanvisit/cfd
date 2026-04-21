# Current B4 Telegram Approval Bridge Detailed Plan

## 목적

`B4`의 목적은 `checkpoint_improvement_watch`가 만든 `GovernanceActionNeeded` 후보를
즉시 Telegram control plane으로 넘길 수 있는 `dispatch-ready bridge`를 만드는 것이다.

이번 단계의 핵심은 Telegram API 완성본이 아니라,

- `GovernanceActionNeeded`
- `pending check_group`
- `ApprovalLoop`
- `ApplyExecutor`

를 하나의 얇은 흐름으로 닫는 것이다.

즉 이번 단계는 `watch -> approval candidate -> approve callback -> bounded apply`까지를
내부 코드와 테스트 기준으로 먼저 연결하는 단계다.

---

## 범위

이번 `v0`에서 다루는 범위는 아래와 같다.

1. `GovernanceActionNeeded` event 구독
2. 동일 `scope_key` 기준 review request 생성 또는 갱신
3. `check_groups` / `check_events`에 approval request 기록
4. Telegram 발송용 `dispatch_envelope` 생성
5. callback을 `ApprovalLoop`로 전달
6. `ApprovalReceived` approve 결과를 `ApplyExecutor`로 전달

이번 단계에서 아직 하지 않는 것은 아래와 같다.

- 실제 Telegram API 전송
- message edit / resend 정책 고도화
- duplicate merge 정교화
- reconcile rule 본체

---

## 새 서비스

- [telegram_approval_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_approval_bridge.py)

이 서비스는 아래 4개를 묶는다.

- [event_bus.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/event_bus.py)
- [telegram_state_store.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/telegram_state_store.py)
- [approval_loop.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/approval_loop.py)
- [apply_executor.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/apply_executor.py)

---

## 책임

### 1. governance event -> review request

bridge는 `GovernanceActionNeeded`를 받으면:

- `scope_key`를 `group_key`로 사용
- 기존 actionable group이 있으면 같은 `approval_id` 유지
- terminal group만 있으면 새 `approval_id`로 reopen
- `check_event`를 append
- Telegram 발송용 `dispatch_envelope`를 기록

### 2. callback -> approval loop

bridge는 callback 입력을 직접 처리하지 않고,
항상 [approval_loop.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/approval_loop.py)로 위임한다.

즉 bridge는 승인 상태기계가 아니라,
승인 상태기계를 `event_bus`와 이어주는 연결층이다.

### 3. approval -> apply executor

bridge는 `ApprovalReceived` event 중 `decision=approve`인 경우만
[apply_executor.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/apply_executor.py)로 전달한다.

`hold`나 `reject`는 apply로 보내지 않는다.

---

## 운영 키 규약

이번 단계에서 bridge가 기대하는 최소 키는 아래와 같다.

- `approval_id`
- `scope_key`
- `apply_job_key`
- `trace_id`
- `decision_deadline_ts`
- `supersedes_approval_id`

이 키들은 `TelegramStateStore`에 저장되고,
callback과 apply가 동일 scope를 추적하는 최소 연결 고리로 쓰인다.

---

## deadline 규칙 v0

초기 `v0` deadline은 review type에 따라 보수적으로 잡는다.

- `CANARY_ROLLBACK_REVIEW`: `+5분`
- `CANARY_ACTIVATION_REVIEW`: `+10분`
- `CANARY_CLOSEOUT_REVIEW`: `+15분`

이 값은 hard contract freeze 전까지는 조정 가능하다.

---

## 테스트 포인트

이번 단계 테스트는 아래 4개를 닫아야 한다.

1. governance event가 pending review request와 dispatch record를 만든다
2. 같은 scope의 반복 governance event는 같은 actionable group을 refresh한다
3. approve callback은 `ApprovalLoop -> ApplyExecutor`로 이어져 group을 `applied`로 만든다
4. hold callback은 apply를 실행하지 않는다

테스트 파일:

- [test_telegram_approval_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_telegram_approval_bridge.py)

---

## 완료 조건

`B4`는 아래가 만족되면 닫힌다.

- `watch`가 만든 governance candidate가 review request로 저장된다
- Telegram 발송에 필요한 envelope가 생성된다
- approve callback이 apply까지 닫힌다
- hold/reject는 apply 없이 상태만 전이된다

이 단계가 닫히면 다음은 `C1 Master Board` 또는 `A6 heavy_cycle`로 넘어갈 수 있다.
