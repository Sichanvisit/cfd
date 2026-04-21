# P5-1 PA8 Closeout Concentrated Observation 상세 계획

## 목표

PA8 closeout을 억지로 당기지 않으면서도, 지금 어떤 심볼을 가장 먼저 집중 관찰해야 하는지 board와 readiness surface에서 계속 보이게 만든다.

## 핵심 원칙

- closeout 기준 자체는 낮추지 않는다.
- rollback 기준도 완화하지 않는다.
- 승격축은 계속 보수적으로 유지한다.
- 대신 `closeout focus`를 별도 축으로 surface해서 운영자가 지금 어디를 먼저 봐야 하는지 명확히 만든다.

## 이번 단계에서 만드는 것

### 1. PA8 closeout focus surface

`readiness_status`와 별도로 `focus_status`를 둔다.

- `NOT_APPLICABLE`
- `PENDING_EVIDENCE`
- `WATCHLIST`
- `CONCENTRATED`
- `READY_FOR_REVIEW`
- `BLOCKED`

### 2. focus 판정 규칙

- `READY_FOR_REVIEW`
  - live window ready
  - 또는 closeout state가 review-ready
- `CONCENTRATED`
  - sample floor 80% 이상
  - 또는 rollback 성격 closeout 후보
- `WATCHLIST`
  - sample floor 50% 이상
  - 또는 active trigger가 존재
- `PENDING_EVIDENCE`
  - 아직 집중 관찰로 끌어올릴 근거 부족
- `BLOCKED`
  - system phase degraded/emergency

## surface 필드

### summary

- `pa8_closeout_focus_status`
- `pa8_focus_symbol_count`
- `pa8_primary_focus_symbol`

### readiness_state

- `pa8_closeout_focus_status`
- `pa8_closeout_focus_reason`
- `pa8_closeout_focus_next_required_action`
- `pa8_primary_focus_symbol`
- `pa8_focus_symbol_count`
- `pa8_focus_watchlist_symbol_count`
- `pa8_closeout_focus_surface`

### pa8_closeout_focus_surface

- `focus_status`
- `blocking_reason`
- `focus_symbol_count`
- `ready_for_review_symbol_count`
- `concentrated_symbol_count`
- `watchlist_symbol_count`
- `pending_symbol_count`
- `blocked_symbol_count`
- `primary_focus_symbol`
- `primary_focus_reason_ko`
- `primary_focus_progress_ratio`
- `recommended_next_action`
- `symbols[]`

## board 연동

- master board는 `PA8 live window pending` 상태일 때도
  `CONCENTRATED` 또는 `READY_FOR_REVIEW`가 있으면
  일반적인 waiting action 대신
  `pa8_closeout_focus_next_required_action`을 summary의 `next_required_action`으로 올린다.

즉 시스템이 아직 closeout-ready는 아니더라도,
운영자에게는 `지금 BTCUSD closeout 집중 관찰` 같은 더 구체적인 액션이 보이게 된다.

## PnL readiness 요약 연동

일간 PnL readiness 요약에는 아래 줄이 추가된다.

- `PA8 focus: CONCENTRATED (집중 1 / watchlist 1 / primary BTCUSD)`

## 이번 단계에서 하지 않는 것

- closeout 자동 승인
- closeout 기준 완화
- multi-symbol 동시 촉진
- PA9 handoff 조건 완화

## 완료 조건

- readiness surface에 `PA8 closeout focus`가 보인다.
- master board summary에 `pa8_closeout_focus_status`, `pa8_primary_focus_symbol`이 보인다.
- `pa8_live_window_pending`일 때도 집중 관찰 심볼이 있으면 `next_required_action`이 더 구체적으로 바뀐다.
- PnL readiness 요약에 `PA8 focus` 한 줄이 들어간다.
