# Profitability / Operations P2 Zero PnL Gap Audit Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p2_zero_pnl_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.json)
- [profitability_operations_p2_zero_pnl_gap_audit_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.csv)
- [profitability_operations_p2_zero_pnl_gap_audit_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_zero_pnl_gap_audit_latest.md)
- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)

## 1. 목적

이 메모는 P2 expectancy 해석 중 `zero_pnl_information_gap_cluster`가 실제로 무엇을 의미하는지 빠르게 고정하기 위한 얇은 보조 audit 기록이다.

핵심 질문은 하나다.

`pnl=0 으로 보이는 row가 실제로 경제적 0 종료인가, 아니면 pnl field 기록 방식 때문에 expectancy 해석이 가려진 것인가?`

## 2. 이번 audit에서 확인한 사실

최근 5000개 closed trade 기준으로 zero-pnl row는 4292개였다.

패턴 분포는 아래와 같았다.

- `net_zero_overrides_nonzero_profit`: 4281
- `all_pnl_fields_zero_or_missing`: 11

즉, 현재 zero-pnl concern의 대부분은 "진짜 0원 종료가 많다"가 아니라,
`profit` 값은 살아 있는데 `gross_pnl` / `net_pnl_after_cost`가 0으로 남아서 expectancy surface에서 경제적 의미가 가려지는 현상에 더 가깝다.

## 3. metadata gap 해석

zero-pnl row 안에서 같이 많이 비는 항목은 아래와 같다.

- `missing_decision_winner`: 2324
- `missing_decision_reason`: 2324
- `missing_setup`: 2292
- `missing_regime`: 881

이 숫자는 zero-pnl concern이 단순 pnl field 문제만이 아니라,
`legacy / low-attribution bucket`과 강하게 겹쳐 있다는 뜻이다.

즉 아래 두 문제가 함께 있다.

1. pnl field 경제성 해석 공백
2. setup / regime / decision attribution 공백

## 4. 현재 top concern bucket

이번 audit에서 바로 review queue에 올린 bucket은 아래 세 개다.

1. `BTCUSD / range_upper_reversal_sell / NORMAL`
   - pattern: `net_zero_overrides_nonzero_profit`
   - rows: 387
   - avg_abs_profit: 0.5733

2. `NAS100 / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - pattern: `net_zero_overrides_nonzero_profit`
   - rows: 267
   - avg_abs_profit: 5.7211

3. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - pattern: `net_zero_overrides_nonzero_profit`
   - rows: 255
   - avg_abs_profit: 12.2031

해석은 아래처럼 나누는 것이 맞다.

- BTC explicit setup bucket:
  - setup / regime / decision attribution은 살아 있으나 pnl field 표기가 net-zero로 덮이는지 점검 필요
- NAS/XAU legacy bucket:
  - pnl field 공백과 attribution 공백이 같이 겹친다

## 5. 이번 audit의 의미

이 보조 audit는 새 phase를 여는 것이 아니다.
P2에서 보이기 시작한 `zero_pnl_information_gap_cluster`를 과해석하지 않도록 막는 safety surface다.

즉 이 audit가 말해주는 것은 아래와 같다.

- `zero_pnl_information_gap_cluster`를 곧바로 "실제 기대값 0인 전략"으로 읽으면 안 된다.
- 먼저 `profit` 대비 `net/gross` 기록 방식과 bucket attribution quality를 함께 봐야 한다.
- 따라서 P2 quick read에서는 이 cluster를 `negative expectancy`와 별도 concern으로 분리해서 다루는 것이 맞다.

## 6. 운영상 다음 사용 방법

이 audit는 독립 트랙으로 키우지 않는다.
대신 아래 두 용도로만 사용한다.

1. P2 operator review 보조
   - zero-pnl concern이 실제 경제적 0인지, field mismatch인지 빠르게 구분

2. P3 anomaly seed
   - zero-pnl 정보 공백이 특정 symbol/setup/regime에 다시 몰리는지 경보 후보로 사용

## 7. 결론

현재 zero-pnl concern의 본질은 `진짜 0 pnl 종료의 다발`보다 `pnl field mismatch + attribution gap`에 더 가깝다.

따라서 지금 수준에서는 이 얇은 audit만 유지하고,
주요 본선은 계속 `P3 anomaly / alerting`으로 넘어가는 것이 맞다.
