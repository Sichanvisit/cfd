# Product Acceptance PA3 Wait / Hold Casebook Mini Set

## 목적

이 문서는 `PA3 Step 2 casebook capture`를 위해
현재 closed-trade artifact에서 바로 비교 가능한
`bad_wait` anchor와 `no_wait` control을 작은 묶음으로 고정한 미니 케이스북이다.

핵심 목적은 아래 둘이다.

- `must_hold 2`를 채우는 `bad_wait timeout` family를 대표 row로 고정
- `good_wait` label이 아직 없으므로, 우선 `no_wait control`과 비교해 경계 조정 기준을 만든다

## 현재 label 분포

[trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv) 전체 기준으로
현재 `wait_quality_label` 분포는 아래다.

- `no_wait = 137`
- `bad_wait = 2`
- `good_wait = 0`
- `unnecessary_wait = 0`

즉 현재 PA3 casebook mini set은
`good_wait vs bad_wait` 구조가 아니라
`bad_wait vs no_wait control` 구조로 먼저 시작하는 것이 맞다.

## A. bad_wait anchor

### case A1. NAS SELL adverse timeout / flow bullish

- `symbol = NAS100`
- `ticket = 91758855`
- `direction = SELL`
- `wait_quality_label = bad_wait`
- `profit = -2.08`
- `exit_reason = Adverse Stop ... hard_guard=adverse | adverse_wait=timeout(349s)`

해석:

- SELL 포지션인데 `BB 20/2 mid 돌파지지`와 `TopDown 1M bullish`가 붙어 있다
- 즉 adverse 구간에서 반대 방향 회복 근거가 이미 있었는데도
  `349s` 동안 기다리다가 timeout으로 닫혔다
- 이번 `PA3-1 tf_confirm + weak peak cap`이 가장 직접적으로 겨냥하는 대표 케이스다

### case A2. NAS SELL adverse timeout / RSI oversold

- `symbol = NAS100`
- `ticket = 91765176`
- `direction = SELL`
- `wait_quality_label = bad_wait`
- `profit = -1.64`
- `exit_reason = Adverse Stop ... hard_guard=adverse | adverse_wait=timeout(174s)`

해석:

- `RSI oversold`와 `TopDown 1M bullish`가 붙은 SELL adverse timeout 사례다
- A1보다 짧지만 `174s`도 여전히 길다고 보는 대표 케이스다
- 즉 이번 경계 조정은 `349s` 같은 extreme case만이 아니라
  `174s`급 bad-wait도 줄이는 방향으로 읽는다

## B. no_wait control

### case B1. NAS SELL adverse protect / no_wait

- `symbol = NAS100`
- `ticket = 91754280`
- `direction = SELL`
- `wait_quality_label = no_wait`
- `profit = -2.02`
- `exit_reason = Protect Exit ... hard_guard=adverse`

해석:

- A1과 같은 `NAS SELL + conservative + adverse` 결이지만
  이 케이스는 timeout wait 없이 바로 protect exit로 닫혔다
- 따라서 `bad_wait timeout` 문제와 `너무 빨리 접은 protect` 문제를
  분리해서 봐야 한다는 control row로 쓴다

### case B2. NAS SELL adverse protect / RSI oversold / no_wait

- `symbol = NAS100`
- `ticket = 91770037`
- `direction = SELL`
- `wait_quality_label = no_wait`
- `profit = -2.08`
- `exit_reason = Protect Exit ... hard_guard=adverse`

해석:

- A2와 비슷한 `RSI oversold` 계열인데 timeout wait 없이 닫힌 control이다
- 즉 같은 context군 안에서도
  `over-hold timeout`과 `immediate protect exit`는 따로 다뤄야 한다

### case B3. XAU BUY protect / no_wait / plus-to-minus

- `symbol = XAUUSD`
- `ticket = 91741342`
- `direction = BUY`
- `wait_quality_label = no_wait`
- `profit = 0.09`
- `exit_reason = Protect Exit ... hard_guard=plus_to_minus`

해석:

- checklist에서 잡아둔 `XAU BUY protect exit no_wait` 비교군이다
- 이 row는 adverse timeout이 아니라 `plus_to_minus` protect 계열이라
  PA3-1 timeout 경계와는 직접 축이 다르다
- 대신 `hold patience`보다 `protect exit quality` 쪽에 더 가까운 control로 둔다

## mini set에서 바로 얻는 판단

1. `must_hold 2`의 핵심 문제는 `SELL adverse timeout bad_wait`다
2. 같은 adverse 계열이어도 `timeout으로 오래 버틴 문제`와 `protect로 바로 닫은 문제`는 다르다
3. 즉 PA3-1 first patch는 `bad_wait timeout`만 먼저 줄이는 방향이 맞다
4. `good_wait / unnecessary_wait` label은 아직 closed-trade surface에 없으므로
   후속 phase에서는 label 자체의 부재도 같이 봐야 한다

## 다음 연결

- [product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md)
