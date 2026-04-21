# Product Acceptance PA3/PA4 Closed Trade Wait Label And Release Seed Alignment Detailed Reference

## 목적

이 문서는 runtime actual closed history 기준으로
`PA3 must_hold`와 `PA4 must_release / bad_exit`를 다시 읽었을 때 드러난
두 가지 왜곡을 함께 교정하기 위한 상세 기준 문서다.

## 실제 문제

### 1. PA3 wait label 왜곡

대표 row:

- `BTCUSD`
- `ticket=96743677`
- `Adverse Stop ... hard_guard=adverse | adverse_wait=timeout(18s)`
- `exit_delay_ticks=3`
- `peak_profit_at_exit=-0.47`

이 row는 runtime 의미상 `긴 hold 실패`보다는
`짧은 defensive deferral 이후 timeout`에 가까운데,
closed-trade label은 무조건 `bad_wait`로 기록되고 있었다.

즉 `timeout`이라는 문자열만 보고 bad_wait로 떨어져,
PA3 `must_hold`에서 과하게 남는 문제가 있었다.

### 2. PA4 release/bad-exit seed 과대 포착

대표 row:

- `XAUUSD ticket=99802294`
- `NAS100 ticket=99774778`
- `NAS100 ticket=98726456`

이 row들은 `peak_profit_at_exit`가 실제로 의미 있는 green room을 형성했고,
`giveback_usd`도 1달러 이상이라 release 문제로 보는 게 맞다.

반대로 아래 family는 tiny peak 혹은 no-green defensive loss인데도
raw `giveback_usd` 또는 negative pnl만으로 `must_release / bad_exit`에 같이 잡히고 있었다.

- `BTCUSD ticket=96740516`
- `BTCUSD ticket=96743677`
- `NAS100 ticket=98754873`

즉 PA4 seed는
`실제로 release-too-late인 close`
와
`green room이 거의 없던 defensive adverse close`
를 충분히 분리하지 못하고 있었다.

## 수정 기준

### PA3 쪽

- `adverse_wait=timeout(...)`라도
- timeout이 짧고
- actual delay tick도 짧고
- meaningful green room이 없고
- post-exit MFE도 작으면

이를 `bad_wait`가 아니라 `unnecessary_wait`로 본다.

핵심 해석:

`짧은 timeout defensive deferral`은
`조금 더 들고 갔어야 했던 hold failure`가 아니라
`크게 의미 없었던 짧은 defer`에 가깝다.

### PA4 쪽

release / bad-exit seed는 이제
`meaningful peak`가 있었는지 먼저 본다.

- peak가 충분히 있었고 giveback이 컸다 -> release/bad-exit seed 유지
- peak가 거의 없었다 -> raw giveback을 release failure 근거로 과하게 쓰지 않음

핵심 해석:

`green room이 거의 없던 defensive loss`는
`release를 너무 늦게 했다`기보다
`애초에 adverse close였다`에 더 가깝다.

## owner

- closed-trade label owner:
  - [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- current artifact rewrite owner:
  - [cleanup_trade_closed_history.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/cleanup_trade_closed_history.py)
- PA0 seed owner:
  - [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)

## 기대 결과

- `must_hold 1 -> 0`
- `must_release / bad_exit`는 즉시 0이 아니라
  `실제 release-too-late family` 위주로 더 좁아진다
- 다음 PA4 메인축이 더 분명해진다
