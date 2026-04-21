# Current Telegram Setup Quickstart

## 목적

이 문서는 지금 운영 중인 텔레그램 구조를 기준으로, `체크방`, `보고서방`, `PnL 포럼`을 빠르게 연결하는 실전용 빠른 시작 가이드다.

핵심 목표는 아래 4가지다.

1. 방 구조를 헷갈리지 않게 만든다.
2. `chat_id`와 `topic_id`를 정확히 찾는다.
3. `.env`를 현재 운영 구조에 맞게 채운다.
4. 첫 테스트 전송까지 확인한다.

운영 제어 구조는 [current_telegram_control_plane_and_improvement_loop_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_telegram_control_plane_and_improvement_loop_ko.md)를, 체크 인박스 UX는 [current_telegram_dual_room_inbox_pattern_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_telegram_dual_room_inbox_pattern_ko.md)를 같이 보면 된다.

## 권장 구조

지금 기준 권장 구조는 아래다.

1. `런타임 DM`
2. `체크방`
3. `보고서방`
4. `PnL 포럼`

역할은 이렇게 나눈다.

- `런타임 DM`
  - 초단기 runtime 알림
- `체크방`
  - 개선안 체크 인박스
  - 누적 목록과 상태 확인
- `보고서방`
  - 원문 보고서 1회 발송
  - 승인/보류/거부가 붙는 상세 보고서
- `PnL 포럼`
  - 주기 손익 보고 전용
  - `15M / 1H / 4H / 1D / 1W / 1M` topic 사용

중요한 점:

- `체크방`과 `보고서방`이 각각 독립 방이면 `topic_id`가 없어도 된다.
- `PnL`만 forum topic을 쓰는 구조가 가장 단순하다.

## 준비물

아래 3가지만 있으면 된다.

1. 봇 토큰
2. 텔레그램 앱
3. 봇이 들어가 있는 기존 방 또는 새로 만든 방

봇 토큰은 보통 [.env](/C:/Users/bhs33/Desktop/project/cfd/.env)의 `TELEGRAM_BOT_TOKEN`에 있다.

주의:

- 토큰은 절대 다른 사람에게 보내지 않는다.
- 공용 브라우저와 공용 PC에서는 가능한 한 직접 입력하지 않는다.

## Step 1. 방 만들기

### 1-1. 체크방

새 그룹 또는 슈퍼그룹 1개를 만든다.

추천 이름:

- `CFD 체크방`

이 방은 체크 인박스와 승인 대상 보고서 링크를 모아보는 곳이다.

### 1-2. 보고서방

새 그룹 또는 슈퍼그룹 1개를 만든다.

추천 이름:

- `CFD 보고서방`

이 방은 원문 보고서가 한 번씩 올라오는 곳이다.

### 1-3. PnL 포럼

새 그룹 또는 슈퍼그룹 1개를 만들고 `Topics` 또는 `포럼`을 켠다.

추천 이름:

- `CFD PnL`

topic은 아래 6개를 만든다.

- `15M`
- `1H`
- `4H`
- `1D`
- `1W`
- `1M`

## Step 2. 봇 추가와 권한

각 방에 같은 봇을 모두 추가한다.

권장 권한:

- 메시지 보내기
- 링크/버튼 메시지 보내기
- 메시지 수정

가능하면 `관리자(Admin)`로 두는 편이 편하다.

## Step 3. update를 일부러 만들기

`chat_id`와 `topic_id`를 찾으려면, 봇 기준으로 새 update가 적어도 1개는 생겨야 한다.

아래처럼 한 번씩 보내면 된다.

- 체크방: `/start@봇아이디`
- 보고서방: `/start@봇아이디`
- PnL 포럼 각 topic: `/start@봇아이디`

중요:

- 아무 응답이 없어도 괜찮다.
- 핵심은 `getUpdates`에 새 항목이 남는 것이다.

## Step 4. `getUpdates`로 ID 찾기

가장 쉬운 방법은 API를 직접 보는 것이다.

브라우저 대신 PowerShell을 권장한다.

```powershell
$token = "YOUR_BOT_TOKEN"
Invoke-RestMethod "https://api.telegram.org/bot$token/getUpdates" | ConvertTo-Json -Depth 8
```

브라우저를 써야 한다면 아래를 열 수는 있다.

```text
https://api.telegram.org/bot<YOUR_BOT_TOKEN>/getUpdates
```

주의:

- 공용 브라우저에서는 하지 않는다.
- 브라우저 히스토리와 자동완성에 토큰이 남을 수 있다.
- 테스트 후 URL 기록을 지우는 편이 안전하다.

만약 `result: []`로 비어 있으면 아직 update가 안 쌓인 것이다. 그때는 Step 3을 다시 한 번 한다.

## Step 5. `chat_id` 찾는 법

일반 방 update에서는 아래 부분을 찾는다.

```json
"chat": {
  "id": -1001234567890,
  "title": "CFD 체크방",
  "type": "supergroup"
}
```

여기서 `id`가 그 방의 `chat_id`다.

예:

- `CFD 체크방 chat_id = -1001234567890`
- `CFD 보고서방 chat_id = -1001234567999`

## Step 6. `topic_id` 찾는 법

포럼 topic 메시지에는 아래처럼 `message_thread_id`가 함께 나온다.

```json
"message": {
  "message_id": 55,
  "message_thread_id": 88,
  "chat": {
    "id": -1002222333344,
    "title": "CFD PnL",
    "type": "supergroup"
  }
}
```

여기서:

- `chat.id` = `PnL 포럼 chat_id`
- `message_thread_id` = 해당 topic의 `topic_id`

예:

- `CFD PnL chat_id = -1002222333344`
- `15M topic_id = 32`
- `1H topic_id = 30`

topic마다 각각 다르므로 `15M / 1H / 4H / 1D / 1W / 1M`를 각각 확인해야 한다.

## Step 7. `.env` 채우기

현재 구조에 맞는 핵심 키는 아래다.

```env
TELEGRAM_BOT_TOKEN=
TELEGRAM_CHAT_ID=

TELEGRAM_CHECK_CHAT_ID=
TELEGRAM_CHECK_TOPIC_ID=

TELEGRAM_REPORT_CHAT_ID=
TELEGRAM_REPORT_TOPIC_ID=

TELEGRAM_PNL_FORUM_CHAT_ID=
TELEGRAM_PNL_TOPIC_15M_ID=
TELEGRAM_PNL_TOPIC_1H_ID=
TELEGRAM_PNL_TOPIC_4H_ID=
TELEGRAM_PNL_TOPIC_1D_ID=
TELEGRAM_PNL_TOPIC_1W_ID=
TELEGRAM_PNL_TOPIC_1M_ID=

TELEGRAM_ALLOWED_USER_IDS=
TELEGRAM_OPS_ENABLED=true
TELEGRAM_OPS_LIVE_CHECK_APPROVALS_ENABLED=false
```

채우는 규칙:

- `체크방`이 일반 방이면 `TELEGRAM_CHECK_TOPIC_ID`는 비워둔다.
- `보고서방`이 일반 방이면 `TELEGRAM_REPORT_TOPIC_ID`는 비워둔다.
- `PnL 포럼`은 `chat_id` 1개 + `topic_id` 6개를 채운다.
- `TELEGRAM_ALLOWED_USER_IDS`에는 승인 버튼을 누를 사람의 telegram user id를 쉼표로 넣는다.

## Step 8. 전송 테스트

### 일반 방 테스트

PowerShell 예시:

```powershell
$token = "YOUR_BOT_TOKEN"
$chatId = "-1001234567890"
Invoke-RestMethod "https://api.telegram.org/bot$token/sendMessage" -Method Post -Body @{
  chat_id = $chatId
  text = "check room test"
}
```

### forum topic 테스트

```powershell
$token = "YOUR_BOT_TOKEN"
$chatId = "-1002222333344"
$topicId = "32"
Invoke-RestMethod "https://api.telegram.org/bot$token/sendMessage" -Method Post -Body @{
  chat_id = $chatId
  message_thread_id = $topicId
  text = "15M topic test"
}
```

메시지가 해당 방 또는 topic에 오면 성공이다.

## Step 9. forum topic id가 안 잡힐 때

현재 프로젝트는 runtime 쪽에서 callback 중심 polling을 쓰기 때문에, forum topic id를 잡을 때는 one-off capture helper를 쓰는 편이 가장 빠르다.

스크립트:

- [capture_telegram_forum_topics.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/capture_telegram_forum_topics.py)

예시:

```powershell
python scripts/capture_telegram_forum_topics.py --chat-id -1003971710112 --timeout-sec 25 --rounds 4
```

그 상태에서 각 topic에 아래처럼 한 번씩 보낸다.

```text
/start@sichan_trading_bot check-topic
/start@sichan_trading_bot report-topic
```

스크립트 출력의 `message_thread_id`가 곧 topic id다.

## 흔한 실수

- 체크방과 보고서방을 새로 만들었는데 `.env`는 예전 forum chat_id를 그대로 두는 경우
- `result: []`인데도 `chat_id`를 못 찾는다고 생각하는 경우
- 일반 방인데 `topic_id`를 억지로 채워 넣는 경우
- `TELEGRAM_ALLOWED_USER_IDS`를 비워둬서 승인 버튼이 안 먹는 경우
- `TELEGRAM_OPS_LIVE_CHECK_APPROVALS_ENABLED=true`로 켜서 실시간 진입/청산 승인 구조로 되돌리는 경우

## 지금 운영 기준 추천

현재 운영 목표는 아래다.

- 진입 / 기다림 / 청산은 자동
- 텔레그램 승인은 학습 결과 반영과 bounded canary, closeout, handoff에만 사용

즉 텔레그램은 `매매 리모컨`이 아니라 `개선안 승인 콘솔`로 쓰는 게 맞다.

## 현재 프로젝트에 맞춘 실제 배치 예시

현재 프로젝트에선 아래 3개 목적지로 보는 게 가장 자연스럽다.

1. `Trading_Bot` 1:1 방
2. `CFD PnL` forum
3. `CFD 체크방` forum

여기서 `CFD 체크방`이 forum이면 아래처럼 잡는다.

```env
TELEGRAM_CHECK_CHAT_ID=-100...
TELEGRAM_REPORT_CHAT_ID=-100...
TELEGRAM_CHECK_TOPIC_ID=<체크 topic id>
TELEGRAM_REPORT_TOPIC_ID=<보고서 topic id>
```

즉 `chat_id`는 같고 `topic_id`만 다르게 쓰는 구조다.
