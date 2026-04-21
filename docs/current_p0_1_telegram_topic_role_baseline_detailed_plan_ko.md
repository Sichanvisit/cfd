# Current P0-1 Telegram Topic Role Baseline Detailed Plan

## 목적

이 문서는 `P0-1 topic 역할 고정`을 실제 코드/설정 기준으로 닫은 결과를 정리한다.

상위 기준:

- [current_p0_foundation_baseline_detailed_plan_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_p0_foundation_baseline_detailed_plan_ko.md)
- [current_detailed_reinforcement_master_roadmap_ko.md](/Users/bhs33/Desktop/project/cfd/docs/current_detailed_reinforcement_master_roadmap_ko.md)

---

## 한 줄 결론

`DM / 체크 topic / 보고서 topic / PnL forum` 역할을 중앙 정책 파일 하나로 고정했고, notifier가 그 정책만 보도록 묶었다.

즉 이제 라우팅 기준은 코드 안 여러 군데에 흩어져 있지 않고, 아래 파일에서 한 번에 읽을 수 있다.

- `backend/services/telegram_route_policy.py`

---

## 현재 고정된 역할

### 1. 실시간 DM

- route: `runtime`
- 역할: 실시간 진입 / 대기 / 청산 / 반전
- 승인 카드 금지

### 2. 체크 topic

- route: `check`
- 역할: 개선안 inbox / readiness 요약 / 상태 변경
- 장문 원문 보고서 금지

### 3. 보고서 topic

- route: `report`
- 역할: 원문 보고서 / review packet / apply packet
- 실시간 실행 메시지 금지

### 4. PnL forum

- route: `pnl`
- 역할: 15분 / 1시간 / 4시간 / 1일 / 1주 / 1달 손익 요약
- 교훈 코멘트 / readiness 요약 허용

---

## 구현 내용

### 1. 중앙 정책 파일 추가

- `backend/services/telegram_route_policy.py`

포함:

- route target dataclass
- route issue dataclass
- baseline builder
- validation rules
- destination resolver
- baseline snapshot writer

### 2. notifier 라우팅 중앙화

- `backend/integrations/notifier.py`

변경:

- `_resolve_destination()`가 직접 Config를 읽지 않고
- `telegram_route_policy.resolve_telegram_route_destination()`를 사용

효과:

- 이후 DM / check / report / pnl 분기가 다시 흔들리지 않음

### 3. baseline snapshot 산출물 추가

생성 파일:

- `data/analysis/shadow_auto/telegram_route_baseline_latest.json`
- `data/analysis/shadow_auto/telegram_route_baseline_latest.md`

역할:

- 현재 `.env` 기준 실제 route 구조를 한눈에 확인
- 충돌 / 누락 이슈가 있으면 issue 목록으로 확인

---

## 현재 설정 기준 결과

### runtime DM

- chat_id: `7210042241`
- 역할: 실시간 실행 DM

### improvement control forum

- chat_id: `-1003971710112`
- check topic id: `4`
- report topic id: `2`

### PnL forum

- chat_id: `-1003749911122`
- 15M topic id: `32`
- 1H topic id: `30`
- 4H topic id: `3`
- 1D topic id: `5`
- 1W topic id: `7`
- 1M topic id: `9`

현재 baseline validation issue:

- 없음

---

## 검증

테스트:

- `tests/unit/test_telegram_route_policy.py`
- `tests/unit/test_telegram_notifier.py`
- `tests/unit/test_telegram_notification_hub.py`

검증 포인트:

- 3갈래 route 역할 일치
- check/report topic 충돌 감지
- notifier가 중앙 정책 기준으로 destination resolve
- baseline snapshot 생성

---

## P0-1 완료 조건 판정

아래를 만족하므로 `P0-1`은 완료로 본다.

- DM / 체크 / 보고서 / PnL 역할이 코드에 고정됨
- notifier가 중앙 정책만 보게 됨
- 실제 `.env` 기준 baseline artifact 생성 완료
- validation issue 없음

---

## 다음 단계

`P0-2 상태 enum 고정`

즉 다음엔 route가 아니라 아래 언어를 잠그는 단계로 넘어가는 것이 맞다.

- `readiness_status`
- `proposal_stage`
- `approval_status`
