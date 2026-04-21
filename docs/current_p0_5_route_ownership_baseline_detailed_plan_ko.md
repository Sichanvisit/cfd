# Current P0-5 Route Ownership Baseline Detailed Plan

## 목표

`P0-5`의 목표는 "누가 어떤 Telegram route로 보낼 수 있는지"를 코드와 문서에서 같은 기준으로 고정하는 것입니다.

`P0-1`이 목적지 자체를 고정했다면, `P0-5`는 그 목적지를 실제로 사용할 수 있는 owner를 고정하는 단계입니다.

---

## 왜 필요한가

route는 맞아도 ownership이 흔들리면 금방 다시 섞입니다.

- 실시간 DM에 proposal/report가 흘러들어올 수 있습니다.
- check topic에 실시간 entry/exit가 잘못 들어갈 수 있습니다.
- report topic에 inbox 성격의 backlog 알림이 쌓일 수 있습니다.
- PnL forum에 approval 성격 메시지가 섞일 수 있습니다.

그래서 `P0-5`는 route destination이 아니라 route ownership을 잠그는 단계입니다.

---

## 이번 단계에서 고정할 owner

### 1. `runtime_execution`

- layer: 실시간 자동매매 런타임
- allowed_routes: `runtime`
- message_kinds: `entry`, `wait`, `exit`, `reverse`

### 2. `improvement_check_inbox`

- layer: checkpoint improvement check inbox
- allowed_routes: `check`
- message_kinds: `proposal_inbox`, `readiness_summary`, `status_update`

### 3. `improvement_report_topic`

- layer: checkpoint improvement report topic
- allowed_routes: `report`
- message_kinds: `proposal_report`, `review_packet`, `apply_packet`

### 4. `pnl_digest`

- layer: PnL digest loop
- allowed_routes: `pnl`
- message_kinds: `pnl_digest`, `lesson_comment`, `readiness_summary`

### 5. `bootstrap_probe`

- layer: telegram bootstrap probe
- allowed_routes: `runtime`, `check`, `report`, `pnl`
- message_kinds: `bootstrap_probe`, `route_probe`

이 owner는 운영 배선 확인용 예외입니다.

### 6. `legacy_live_check_card`

- layer: legacy live check card
- allowed_routes: `check`
- message_kinds: `legacy_check_card`
- enabled_by_default: `False`

이 owner는 구형 live approval lane을 표시하기 위한 예외이며 기본 비활성입니다.

---

## 이번 단계에서 실제로 하는 일

### 1. ownership policy 파일 추가

파일:

- `backend/services/telegram_route_ownership_policy.py`

역할:

- owner별 allowed route 정의
- owner별 allowed message kind 정의
- ownership validation helper 제공
- baseline snapshot export

### 2. 실제 발송 지점에 ownership 검증 삽입

파일:

- `adapters/telegram_notifier_adapter.py`
- `backend/services/telegram_notification_hub.py`
- `backend/services/telegram_ops_service.py`

적용 위치:

- runtime DM 발송 전
- improvement check/report 발송 전
- PnL digest 발송 전
- bootstrap probe 발송 전
- legacy live check card 발송 전

### 3. baseline artifact와 테스트 고정

파일:

- `tests/unit/test_telegram_route_ownership_policy.py`

artifact:

- `data/analysis/shadow_auto/telegram_route_ownership_baseline_latest.json`
- `data/analysis/shadow_auto/telegram_route_ownership_baseline_latest.md`

---

## 완료 조건

- owner별 allowed route가 코드로 정의되어 있다
- 잘못된 owner-route 조합은 validation에서 바로 실패한다
- runtime / check / report / pnl의 실제 대표 발송 지점이 ownership validation을 지난다
- ownership baseline artifact가 생성된다

---

## 이번 단계에서 일부러 하지 않는 것

- route 자체 재설계
- 새 Telegram room 추가
- detector/apply 로직 변경
- legacy live check card 제거

즉 `P0-5`는 "누가 어디로 보낼 수 있는지"만 잠그는 단계이지, 발송되는 콘텐츠 자체를 바꾸는 단계는 아닙니다.

---

## 다음 단계 연결

`P0-5`가 닫히면 `P0-6 문서/코드 정합성 체크`가 쉬워집니다.

그 다음에는 바로 `P2 quick 설명력`과 `P1 readiness surface`로 넘어가도, Telegram routing/ownership 때문에 다시 흔들릴 가능성이 크게 줄어듭니다.
