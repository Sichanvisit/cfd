# Current Telegram Notification Hub Design

## 목적

이 문서는 현재 CFD 프로젝트에 `봇 1개 + 텔레그램 방 3개` 운영 구조를 붙이기 위한 설계 고정안이다.

구현 직전 세부 자료는 아래 문서를 함께 본다.

- [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)
- [current_telegram_ops_mvp_templates_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_templates_ko.md)
- [current_telegram_ops_mvp_refinements_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_ops_mvp_refinements_ko.md)
- [current_telegram_setup_quickstart_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_setup_quickstart_ko.md)

목표는 아래 3가지를 동시에 만족하는 것이다.

1. 체크 요청이 수익/진입/청산 보고에 묻히지 않게 분리한다.
2. 체크 요청이 누적될 때는 개별 메시지를 무한정 쌓지 않고, 비슷한 요청을 묶어서 처리한다.
3. 누적 수익은 별도 포럼방의 기간별 토픽에서 `1H / 4H / 1D / 1W / 1M` 단위로 본다.

현재 코드베이스에는 이미 아래 기반이 있다.

- 텔레그램 발송 어댑터: [adapters/telegram_notifier_adapter.py](/Users/bhs33/Desktop/project/cfd/adapters/telegram_notifier_adapter.py)
- 단일 채팅 전송기: [backend/integrations/notifier.py](/Users/bhs33/Desktop/project/cfd/backend/integrations/notifier.py)
- FastAPI 런타임 진입점: [backend/fastapi/app.py](/Users/bhs33/Desktop/project/cfd/backend/fastapi/app.py)
- 거래 SQLite 미러: [backend/services/trade_sqlite_store.py](/Users/bhs33/Desktop/project/cfd/backend/services/trade_sqlite_store.py)
- 단일 텔레그램 설정: [backend/core/config.py](/Users/bhs33/Desktop/project/cfd/backend/core/config.py)

따라서 본 설계는 새 봇을 추가로 만들지 않고, 기존 발송기를 `텔레그램 허브`로 승격하는 방향을 기본값으로 한다.

---

## 목표 운영 구조

### 텔레그램 구조

- 방 1: `체크 전용`
- 방 2: `수익/진입/청산 보고 전용`
- 방 3: `누적수익 포럼 전용`

방 3은 포럼 그룹으로 만들고 토픽을 아래처럼 고정한다.

- `1H`
- `4H`
- `1D`
- `1W`
- `1M`

### 운영 원칙

- 체크방에는 `행동이 필요한 것`만 보낸다.
- 보고방에는 `정보성 메시지`만 보낸다.
- 누적수익 포럼은 `기간별 요약 카드`를 유지한다.
- 체크는 새 메시지 남발보다 `미처리 묶음 카드`를 우선한다.
- 포럼 토픽은 가능하면 `요약 메시지 1개를 edit`하는 방식으로 유지한다.

---

## 권장 아키텍처

### 핵심 판단

현재 환경은 Windows 데스크톱에서 MT5와 함께 돌아가는 형태라서, 첫 구현은 `Webhook`보다 `getUpdates polling`이 현실적이다.

이 판단은 로컬 런타임에 공인 HTTPS 엔드포인트를 붙이지 않아도 되고, 기존 실행 흐름에 영향이 적기 때문이다.

단, 나중에 외부 서버나 고정 도메인을 붙이면 webhook으로 바꿀 수 있게 인터페이스는 분리한다.

### 상위 구성

1. `TelegramClient`
   - Telegram Bot API 호출 담당
   - `sendMessage`, `editMessageText`, `editMessageReplyMarkup`, `answerCallbackQuery`, `getUpdates` 캡슐화
2. `TelegramNotificationHub`
   - 이벤트 타입에 따라 목적지 라우팅
   - 체크방, 보고방, 포럼 토픽방 분기
3. `TelegramUpdatePoller`
   - 버튼 클릭 callback update 수신
   - offset 저장, 재시도, 중복 방지 담당
4. `CheckQueueService`
   - 체크 생성, 병합, 재알림, 승인/거부/보류 상태 전이 담당
5. `PnlDigestService`
   - `1H / 4H / 1D / 1W / 1M` 누적 손익 집계 담당
6. `TelegramStateStore`
   - 체크 상태, 메시지 매핑, callback 처리 이력 저장

### 레이어 연결

- 기존 진입/청산 로직은 바로 텔레그램에 문자열을 보내지 않는다.
- 먼저 `허브 이벤트`를 만든다.
- 허브가 이벤트를 보고 목적지와 표현 방식을 결정한다.

즉, 기존의 `send("문자열")` 구조를 아래처럼 확장한다.

```text
Trading / Exit / Report logic
  -> Notification event
  -> TelegramNotificationHub
  -> Check room / Report room / PnL topic
```

---

## 추천 파일 배치

기존 파일을 최대한 유지하면서 아래 파일을 추가하는 구성을 권장한다.

- [backend/integrations/telegram_client.py](/Users/bhs33/Desktop/project/cfd/backend/integrations/telegram_client.py)
  - 저수준 Telegram Bot API 클라이언트
- [backend/services/telegram_notification_hub.py](/Users/bhs33/Desktop/project/cfd/backend/services/telegram_notification_hub.py)
  - 이벤트 라우팅 허브
- [backend/services/telegram_state_store.py](/Users/bhs33/Desktop/project/cfd/backend/services/telegram_state_store.py)
  - 체크/메시지/offset 저장소
- [backend/services/check_queue_service.py](/Users/bhs33/Desktop/project/cfd/backend/services/check_queue_service.py)
  - 체크 병합, 승인/거부/보류, 재알림
- [backend/services/pnl_digest_service.py](/Users/bhs33/Desktop/project/cfd/backend/services/pnl_digest_service.py)
  - 기간별 PnL 계산
- [backend/services/telegram_update_poller.py](/Users/bhs33/Desktop/project/cfd/backend/services/telegram_update_poller.py)
  - getUpdates 기반 수신 루프
- [backend/fastapi/routers_telegram.py](/Users/bhs33/Desktop/project/cfd/backend/fastapi/routers_telegram.py)
  - 선택 사항
  - 운영 조회용 `/ops/check-queue`, `/ops/telegram/status` 같은 내부 API

기존 [backend/integrations/notifier.py](/Users/bhs33/Desktop/project/cfd/backend/integrations/notifier.py)는 바로 지우지 말고 아래 순서로 축소한다.

1. 보고방 전송을 우선 이관
2. 체크방 전송을 허브로 분리
3. 포럼 토픽 집계 전송 추가
4. 최종적으로 notifier는 hub 또는 client thin wrapper로 정리

---

## 설정 확장안

현재는 `TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`만 있다.

아래 키로 확장하는 것을 권장한다.

### 필수 키

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHECK_CHAT_ID`
- `TELEGRAM_REPORT_CHAT_ID`
- `TELEGRAM_PNL_FORUM_CHAT_ID`

### 포럼 토픽 키

- `TELEGRAM_PNL_TOPIC_1H_ID`
- `TELEGRAM_PNL_TOPIC_4H_ID`
- `TELEGRAM_PNL_TOPIC_1D_ID`
- `TELEGRAM_PNL_TOPIC_1W_ID`
- `TELEGRAM_PNL_TOPIC_1M_ID`

### 체크 운영 키

- `TELEGRAM_ALLOWED_USER_IDS`
- `TELEGRAM_CHECK_MERGE_WINDOW_MINUTES`
- `TELEGRAM_CHECK_RENOTIFY_MINUTES`
- `TELEGRAM_CHECK_EXPIRE_MINUTES`
- `TELEGRAM_POLL_INTERVAL_SEC`
- `TELEGRAM_LONG_POLL_TIMEOUT_SEC`

### 선택 키

- `TELEGRAM_WEBHOOK_ENABLED`
- `TELEGRAM_WEBHOOK_SECRET`
- `TELEGRAM_CHECK_TOPIC_ID`
- `TELEGRAM_REPORT_TOPIC_ID`

`체크방`, `보고방`도 일반 그룹이 아니라 포럼의 토픽으로 운영하고 싶으면 뒤의 topic id를 쓰면 된다.

---

## 저장소 분리 전략

### 권장안

체크/메시지/상호작용 상태는 거래 미러 DB와 분리해서 새 SQLite 파일에 저장한다.

권장 경로:

- `data/ops/telegram_hub.db`

### 이유

- 거래 미러는 읽기 성능 중심 구조이고, 교체(sync) 주기가 있다.
- 체크 상태는 상호작용과 재시도가 많고, 운영 이력이 오래 남아야 한다.
- 두 책임을 분리하면 기존 거래 조회 코드에 영향이 적다.

즉:

- 거래 데이터 읽기: 기존 `trade_history.csv`, `closed_trade_history.csv`, `trades.db`
- 텔레그램 운영 상태 쓰기: 신규 `telegram_hub.db`

---

## 데이터 모델

### 1. `check_groups`

비슷한 체크 요청을 묶는 대표 테이블.

권장 컬럼:

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
- `first_event_ts`
- `last_event_ts`
- `pending_count`
- `last_prompt_message_id`
- `last_prompt_chat_id`
- `last_prompt_topic_id`
- `approved_by`
- `approved_at`
- `rejected_by`
- `rejected_at`
- `held_by`
- `held_at`
- `expires_at`
- `created_at`
- `updated_at`

`status` 값은 아래를 권장한다.

- `pending`
- `approved`
- `rejected`
- `held`
- `expired`
- `applied`
- `cancelled`

### 2. `check_events`

묶음에 포함된 개별 원본 이벤트 기록.

권장 컬럼:

- `event_id`
- `group_id`
- `source_type`
- `source_ref`
- `symbol`
- `side`
- `payload_json`
- `event_ts`
- `created_at`

### 3. `check_actions`

버튼 클릭 이력.

권장 컬럼:

- `action_id`
- `group_id`
- `telegram_user_id`
- `telegram_username`
- `action`
- `note`
- `callback_query_id`
- `created_at`

`action` 값:

- `approve`
- `reject`
- `hold`
- `apply`
- `refresh`
- `reopen`

### 4. `telegram_messages`

텔레그램 메시지와 내부 엔터티 매핑.

권장 컬럼:

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
- `created_at`
- `updated_at`

`message_kind` 예:

- `check_prompt`
- `check_audit`
- `report_entry`
- `report_exit`
- `pnl_summary`

### 5. `telegram_update_offsets`

polling offset 저장.

권장 컬럼:

- `stream_key`
- `last_update_id`
- `updated_at`

### 6. `pnl_snapshots`

기간별 집계 캐시와 히스토리.

권장 컬럼:

- `snapshot_id`
- `window_code`
- `window_start_ts`
- `window_end_ts`
- `realized_pnl`
- `open_pnl`
- `trade_count`
- `win_rate`
- `gross_pnl`
- `cost_total`
- `best_trade_pnl`
- `worst_trade_pnl`
- `summary_json`
- `created_at`

---

## 체크 병합 규칙

### 핵심 원칙

체크는 원본 이벤트 하나당 메시지 하나가 아니라, `미해결 그룹 하나당 대표 메시지 하나`를 만든다.

### 기본 그룹 키

아래 조합을 추천한다.

- `symbol`
- `side`
- `strategy_key`
- `check_kind`
- `action_target`
- `time_bucket`

예:

```text
BTCUSD|BUY|strategy_a|entry_review|apply|2026-04-10T21:00+09:00/15m
```

### 시간 버킷

기본값은 `15분`을 권장한다.

이유:

- 너무 짧으면 병합 효과가 약하다.
- 너무 길면 서로 다른 상황이 지나치게 합쳐진다.

### reason fingerprint

가능하면 단순 텍스트 전체가 아니라 아래 값으로 fingerprint를 만든다.

- 주요 rule family
- stage
- symbol
- side
- strategy
- 정규화된 이유 코드 상위 N개

텍스트 similarity보다 구조화된 코드 기반 병합이 더 안정적이다.

### 병합 조건

기존 `pending` 그룹이 있고 아래 조건을 만족하면 새 이벤트를 합친다.

1. `group_key` 일치
2. `reason_fingerprint` 일치 또는 similarity 임계치 이상
3. 아직 `approved/rejected/applied/expired`로 닫히지 않음

### 재알림 규칙

- `pending_count` 증가 시 기존 메시지를 edit
- 마지막 알림 후 `RENOTIFY_MINUTES` 경과 시 메시지 재상단화
- `EXPIRE_MINUTES` 초과 시 `expired` 처리

---

## 체크 메시지 표현

### 대표 카드 예시

```text
[체크 요청]
상태: PENDING
종목: BTCUSD
방향: BUY
전략: strategy_a
요청: 적용 허가
미처리 누적: 7건
최근 발생: 2026-04-10 21:40 KST

진입 근거 요약
- lower_rebound_confirm
- bb20 support reclaim
- short-term momentum recovery

청산/리스크 메모
- initial stop preserved
- follow-through weak if volume fades

담당 메모
- 최근 15분 동일 성격 요청 누적
```

### 버튼 예시

- `승인`
- `거부`
- `보류`
- `상세`
- `새로고침`

체크박스 느낌은 실제 checkbox가 아니라 메시지 edit로 표현한다.

예:

- `☐ 적용 허가`
- `☑ 적용 허가`

### 버튼 처리 후 예시

```text
[체크 요청]
상태: APPROVED
종목: BTCUSD
방향: BUY
전략: strategy_a
요청: 적용 허가
누적 처리: 7건
승인자: myid
승인시각: 2026-04-10 21:43 KST
```

버튼 클릭 후에는 반드시 아래 3개를 수행한다.

1. DB 상태 저장
2. 원본 메시지 edit
3. `answerCallbackQuery` 호출

---

## callback data 규약

짧고 버전 가능한 형태를 권장한다.

예:

```text
chk:12345:approve:v1
chk:12345:reject:v1
chk:12345:hold:v1
chk:12345:refresh:v1
```

파싱 후에는 반드시 아래를 검증한다.

- 허용 사용자 여부
- group 상태가 아직 처리 가능 상태인지
- 동일 callback 재처리 여부

중복 클릭이 들어와도 DB 트랜잭션에서 멱등하게 처리해야 한다.

---

## 보고방 설계

### 역할

보고방은 현재 단일 notifier가 보내는 텍스트성 알림을 수용하는 공간이다.

여기에는 아래 이벤트를 보낸다.

- 진입 시그널
- 청산 결과
- 손익 결과
- 전략 메모
- 주간/일간 보고

### 보고방 원칙

- 정보는 쌓아도 된다.
- 버튼은 최소화한다.
- 체크가 필요한 이벤트는 보고방에 보내지 말고 체크 이벤트로 승격한다.

### 보고 이벤트 타입 예시

- `entry_signal`
- `exit_result`
- `runtime_alert`
- `shock_weekly_report`
- `daily_report`

---

## 누적수익 포럼 설계

### 토픽 의미

기간 정의는 아래 기본값을 권장한다.

- `1H`: 최근 1시간 rolling
- `4H`: 최근 4시간 rolling
- `1D`: KST 당일 00:00 이후 누적
- `1W`: KST 주간 누적, 월요일 00:00 기준
- `1M`: KST 월간 누적, 매월 1일 00:00 기준

이렇게 하면 짧은 구간은 최근 흐름을 보고, 긴 구간은 운영 기준 기간 누적을 볼 수 있다.

### 집계 항목

각 토픽의 대표 요약 메시지에는 아래 항목을 권장한다.

- 기간명
- 기준 시각
- 실현 손익
- 현재 미실현 손익
- 총 거래 수
- 승률
- 평균 손익
- 최고 수익 거래
- 최악 손실 거래
- 주요 진입 사유 TOP 3
- 주요 청산 사유 TOP 3

### 토픽별 대표 메시지 예시

```text
[1D 누적수익]
기준: 2026-04-10 21:45 KST

실현 손익: +132.40 USD
미실현 손익: -8.10 USD
총 거래: 11
승률: 63.6%
평균 손익: +12.03 USD
최고 거래: +44.20 USD
최악 거래: -18.50 USD

주요 진입 근거 TOP3
- lower_rebound_confirm: 4
- upper_reject_mixed_confirm: 3
- range_reclaim_follow: 2

주요 청산 근거 TOP3
- target_hit: 5
- adverse_exit: 3
- managed_reduce: 2
```

### 업데이트 전략

토픽마다 `요약 메시지 1개`를 유지하고 edit한다.

추가로 아래 이벤트가 발생할 때만 히스토리 메시지를 남긴다.

- 일간 마감
- 주간 마감
- 월간 마감
- 수익 급변 임계치 초과

즉, 토픽 자체는 조용하지만 핵심 변곡만 남기는 구조가 좋다.

---

## PnL 계산 기준

### 추천 기준

기간별 누적수익의 기본 기준은 `실현 손익`으로 한다.

이유:

- 닫히지 않은 포지션의 손익은 계속 바뀐다.
- 실현 손익은 기간 합계가 안정적이다.
- 운영 복기와 비교가 쉽다.

### 미실현 손익 처리

미실현 손익은 보조 항목으로만 함께 보여준다.

즉:

- 메인 숫자: `실현 손익`
- 서브 숫자: `현재 미실현 손익`

### 데이터 원천

아래 조합을 권장한다.

- closed trades: 기존 미러 또는 `TradeReadService`
- open trades: 기존 미러 또는 `TradeReadService`
- 사유 통계: closed/open row의 reason 관련 컬럼

즉, 신규 시스템은 거래 로직을 건드리지 않고 읽기만 한다.

---

## 서비스별 책임 분리

### `TelegramClient`

- 텔레그램 API 호출
- 재시도
- rate limiting
- HTTP 오류 로깅

### `TelegramNotificationHub`

- 이벤트 타입 -> 목적지 라우팅
- 메시지 신규 생성 vs edit 선택
- 체크/보고/포럼 분기

### `CheckQueueService`

- 그룹 생성
- 병합
- 상태 전이
- 버튼 처리
- 만료 처리
- 재알림

### `PnlDigestService`

- 기간 정의
- 손익 계산
- 토픽별 summary payload 생성
- 마감 스냅샷 기록

### `TelegramStateStore`

- SQLite 트랜잭션
- idempotency
- 메시지 매핑 조회
- offset 저장

---

## FastAPI 및 런타임 연결 방식

### 추천 1차 구현

FastAPI `lifespan`에서 아래 두 백그라운드 작업을 시작한다.

1. `TelegramUpdatePoller`
2. `PnlDigestRefreshLoop`

이 방식은 현재 [backend/fastapi/app.py](/Users/bhs33/Desktop/project/cfd/backend/fastapi/app.py)의 생명주기 구조와 맞다.

### 운영 조회 API

내부용으로 아래 API를 두면 운영이 편하다.

- `GET /ops/telegram/status`
- `GET /ops/check-queue`
- `GET /ops/check-queue/pending`
- `GET /ops/pnl-digest`

프론트엔드 확장은 나중에 해도 되지만, API는 초기에 넣는 것이 디버깅에 도움이 된다.

---

## 이벤트 계약 권장안

현재의 `문자열 바로 전송` 대신 typed event를 권장한다.

예:

```json
{
  "event_type": "check_request",
  "route_key": "check",
  "symbol": "BTCUSD",
  "side": "BUY",
  "strategy_key": "strategy_a",
  "check_kind": "entry_review",
  "action_target": "apply",
  "priority": "high",
  "reason_codes": ["lower_rebound_confirm", "bb20_reclaim"],
  "reason_summary": "Lower rebound confirm with BB20 reclaim and recovering momentum.",
  "payload": {
    "entry_price": 83210.5,
    "score": 381,
    "position_count": 1
  }
}
```

보고 이벤트 예:

```json
{
  "event_type": "exit_result",
  "route_key": "report",
  "symbol": "XAUUSD",
  "profit": 24.8,
  "points": 61,
  "entry_price": 3187.24,
  "exit_price": 3189.68,
  "reason_summary": "Managed reduce after follow-through fade."
}
```

이 구조로 바꾸면 나중에 텔레그램 외 채널이 필요해져도 재사용 가능하다.

---

## 단계별 구현 순서

실제 구현 스레드에서는 아래 phase만 보지 말고, [current_telegram_control_plane_and_improvement_loop_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)의 `권장 구현 순서`와 승인 경계를 함께 본다.

### Phase 1. 채팅 분리

- config에 3개 chat id와 5개 topic id 추가
- 기존 notifier를 보고방 라우팅용으로 확장
- 보고방 알림이 정상 이동하는지 먼저 확인

### Phase 2. 체크 큐 도입

- `telegram_hub.db` 추가
- `check_groups`, `check_events`, `check_actions`, `telegram_messages` 구현
- 체크 메시지를 새 메시지 대신 그룹 카드로 생성
- 버튼 승인/거부/보류 처리 추가

### Phase 3. 포럼 누적수익

- `pnl_snapshots` 구현
- `1H / 4H / 1D / 1W / 1M` 토픽별 대표 메시지 생성
- edit 기반 갱신 적용

### Phase 4. 재알림과 운영 API

- pending aging 재알림
- expired 처리
- `/ops/check-queue` 조회 API 추가

### Phase 5. 선택 확장

- 프론트엔드 관리 화면
- 텔레그램 Mini App
- webhook 전환

---

## 구현 시 주의점

### 1. privacy mode

버튼 callback만 쓸 경우 봇 privacy mode를 당장 끌 필요는 없다.

### 2. 권한 제어

아무 사용자나 승인/거부하지 않도록 `TELEGRAM_ALLOWED_USER_IDS` 검증이 필요하다.

### 3. 메시지 수정 실패

메시지가 너무 오래되었거나 삭제되었을 수 있으므로, edit 실패 시 새 메시지를 생성하고 매핑을 갱신해야 한다.

### 4. 중복 클릭

callback은 네트워크 재시도로 중복 수신될 수 있으니 DB 레벨 멱등 처리가 필요하다.

### 5. 기간 정의

특히 `1D`, `1W`, `1M`은 `Asia/Seoul` 기준으로 고정해야 한다.

### 6. 실현/미실현 혼합

누적수익 메인 숫자에 미실현을 섞지 않는 것이 운영 판단에 더 안정적이다.

---

## 권장 초기값

- 체크 병합 윈도우: `15분`
- 체크 재알림: `20분`
- 체크 만료: `180분`
- PnL 요약 갱신 주기: `60초`
- polling interval: `2초`
- long poll timeout: `25초`

---

## 최종 권장안

현재 프로젝트에는 아래 방식이 가장 안전하다.

1. `봇 1개 + 방 3개` 유지
2. `체크방`, `보고방`, `누적수익 포럼방`으로 역할 분리
3. 체크는 `큐 + 병합 + 버튼 승인/거부/보류`
4. 누적수익은 `포럼 토픽별 대표 메시지 edit`
5. 상태 저장은 거래 DB와 분리된 `telegram_hub.db`
6. 1차 수신 방식은 `getUpdates polling`

이 구성이면 체크가 묻히지 않고, 보고는 계속 흐르게 두면서, 기간별 손익은 챕터처럼 토픽으로 나눠 볼 수 있다.
