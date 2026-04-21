# Current P2 Quick Runtime Explanation Detailed Plan

## 목표

`P2-quick`의 목표는 실시간 DM에서 사용자가 가장 먼저 궁금해하는 `"왜 지금 이렇게 판단했는가"`를 짧고 표준화된 2~3줄로 바로 보이게 만드는 것입니다.

이 단계는 detector나 readiness를 바꾸는 단계가 아니라, 이미 돌아가고 있는 런타임 판단을 사람 언어로 드러내는 단계입니다.

---

## 이번 단계에서 붙이는 설명 포맷

### 1. 진입

- `주도축:`
- `핵심리스크:`
- `강도:`

### 2. 대기

- `대기이유:`
- `해제조건:`

기존 `베리어 / 빌리프 / 포리캐스트`는 그대로 유지하되, 그 위에 사람이 먼저 읽는 두 줄을 얹습니다.

### 3. 청산

- `청산사유:`
- `복기힌트:`

단, 복기 힌트는 의미 있는 규칙이 있을 때만 붙이고, 억지 힌트는 만들지 않습니다.

### 4. 반전

- `상태:`
- `주도축:`
- `핵심리스크:`
- `강도:`

---

## 생성 규칙

### 진입 / 반전의 주도축

- raw reason을 정규화한다
- stage/wait 이유를 제외한 상위 reason 2개를 고른다
- `A + B` 형태로 연결한다
- primary reason이 없으면 stage reason을 fallback으로 쓴다

### 진입 / 반전의 핵심리스크

- 현재 방향의 반대쪽 위험을 짧게 적는다
- `BUY`면 상단 저항/하방 신호 재확인 쪽
- `SELL`면 하단 반등/지지 재확인 쪽
- raw reason에 `upper/lower/rebound/divergence/touch`가 있으면 조금 더 구체적으로 적는다

### 진입 / 반전의 강도

- score와 reason 개수를 함께 본다
- `HIGH / MEDIUM / LOW`만 surface한다
- raw score 숫자는 DM에 다시 노출하지 않는다

### 대기의 해제조건

- forecast confirm side가 있으면 그 방향 확인 시 재검토
- barrier hint가 강하면 해당 barrier 완화 시 재검토
- 둘 다 없으면 방향 확인 신호 추가 시 재검토

### 청산의 복기힌트

- `protective loss / stop`: 반대 힘 급변 여부와 진입 시점 재검토
- `protective profit / runner`: MFE 대비 이익 포착 효율 복기
- `target / full exit`: 목표가 전량 청산이 최선이었는지 복기
- `timeout`: time decay 여부 복기
- 큰 역행폭: 변동성 구간과 허용 역행폭 복기

---

## 이번 단계에서 실제로 건드리는 파일

- `backend/integrations/notifier.py`
- `tests/unit/test_telegram_notifier.py`

필요 시 회귀 확인:

- `tests/unit/test_telegram_notifier_adapter.py`
- `tests/unit/test_trading_application_wait_alerts.py`
- `tests/unit/test_trading_application_reverse.py`
- `tests/unit/test_trade_logger_manual_reason_tags.py`
- `tests/unit/test_trade_logger_lifecycle.py`

---

## 완료 조건

- 실시간 진입 DM에 `주도축 / 핵심리스크 / 강도`가 보인다
- 대기 DM에 `대기이유 / 해제조건`이 보인다
- 청산 DM에 `청산사유 / 복기힌트`가 보인다
- 반전 DM에 `상태 / 주도축 / 핵심리스크 / 강도`가 보인다
- raw `Score:`나 `Why now` 같은 구버전 잔말이 다시 나타나지 않는다

---

## 이번 단계에서 일부러 하지 않는 것

- scene axis 본격 노출
- detector proposal 생성
- readiness surface 연결
- weight patch 반영

즉 `P2-quick`은 설명력을 먼저 체감시키는 얇은 단계이고, 이후 `P1 readiness`와 `P2 full`의 발판 역할을 합니다.
