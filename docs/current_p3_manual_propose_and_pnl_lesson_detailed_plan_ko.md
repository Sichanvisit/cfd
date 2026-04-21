# P3. `/propose` + PnL 교훈 상세 계획

## 목표

- 최근 마감 거래를 기준으로 문제 패턴을 사람이 읽을 수 있는 한국어 보고서로 surface한다.
- `1D PnL` 메시지에 숫자 외의 교훈 코멘트를 붙여, 다음 개선 제안의 입력으로 쓴다.
- 아직 detector 자동화로 가지 않고, 수동 명령과 일간 코멘트 수준에서 관찰 루프를 닫는다.

## 구현 범위

### 1. 수동 `/propose`

- 입력:
  - Telegram 명령 `/propose`
  - 선택 입력 `/propose 80` 같은 최근 거래 수 지정
- 처리:
  - 최근 마감 거래를 읽는다.
  - entry reason 기준으로 반복 손실 패턴을 묶는다.
  - `Level 1 / Level 2 / Level 3` 기준으로 문제를 분류한다.
  - 한국어 보고서를 `보고서 topic`에 보낸다.
  - 짧은 inbox 요약을 `체크 topic`에 보낸다.
- 출력:
  - `report_title_ko`
  - `report_lines_ko`
  - `inbox_summary_ko`
  - `proposal_envelope`

### 2. `1D PnL` 오늘의 교훈

- 입력:
  - 최근 일간 마감 거래
- 규칙:
  - MFE 대비 수익 포착률이 낮으면 경고
  - 같은 entry reason에서 최근 연속 손실이 있으면 경고
  - 특정 시간대 승률이 전체 대비 현저히 낮으면 경고
  - 없으면 `특이사항 없음`
- 출력:
  - `━━ 오늘의 교훈 ━━`
  - 1~3개의 코멘트

## 문제 판별 기준

### Level 1

- 같은 패턴에서 최근 3연속 손실
- 표본 5건 이상에서 승률 30% 미만
- 표본 5건 이상에서 평균 MFE 포착률 25% 미만

### Level 2

- 같은 패턴에서 최근 2연속 손실
- 표본 5건 이상에서 승률 45% 미만
- 표본 5건 이상에서 평균 MFE 포착률 40% 미만

### Level 3

- 표본 부족 또는 관찰 단계
- surface는 하지 않고 snapshot에는 남긴다

## 라우팅

- `runtime DM`
  - 사용하지 않음
- `check topic`
  - `[수동 제안 분석] ...` 요약
- `report topic`
  - 상세 보고서 원문
- `PnL forum 1D`
  - `오늘의 교훈` 섹션 추가

## 핵심 파일

- `backend/services/trade_feedback_runtime.py`
- `backend/services/telegram_ops_service.py`
- `tests/unit/test_trade_feedback_runtime.py`
- `tests/unit/test_telegram_ops_service_p3.py`

## 완료 조건

- `/propose` 명령으로 보고서 topic과 체크 topic에 한국어 surface가 생성된다.
- `1D PnL` 메시지에 `오늘의 교훈`이 붙는다.
- 둘 다 approval/apply 자동화 없이 관찰과 review 단계에만 머문다.
