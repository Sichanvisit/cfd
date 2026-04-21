# PA8 Canary Refresh Board

## 목적

- NAS100 / BTCUSD / XAUUSD의 active PA8 canary를 한 번에 다시 계산한다.
- 장이 닫힌 동안에는 seed reference 상태를 유지한다.
- 장이 다시 열리면 post-activation live row 기준으로
  first window observation과 closeout decision을 즉시 새로 만든다.

## refresh가 하는 일

1. NAS100 first window observation 재계산
2. NAS100 closeout decision 재계산
3. BTCUSD first window observation 재계산
4. BTCUSD closeout decision 재계산
5. XAUUSD first window observation 재계산
6. XAUUSD closeout decision 재계산
7. 세 심볼 상태를 하나의 board로 요약

## 기대 상태

- 장 닫힘:
  - `FIRST_WINDOW_SEEDED_PENDING_LIVE_ROWS`
  - `HOLD_CLOSEOUT_PENDING_LIVE_WINDOW`
- 장 열림 후 live row 축적:
  - `FIRST_WINDOW_LIVE_OBSERVATION_ACTIVE`
  - sample floor 충족 전까지 `HOLD_CLOSEOUT_PENDING_SAMPLE_FLOOR`
  - 충분한 row와 trigger 없음:
    - `READY_FOR_PA9_ACTION_BASELINE_HANDOFF_REVIEW`

## 핵심 원칙

- scene bias는 계속 preview-only다.
- PA8은 action-only canary만 본다.
- closeout은 live row 없이 강제로 닫지 않는다.
- board는 상태판이고, activation scope 자체를 넓히지 않는다.
