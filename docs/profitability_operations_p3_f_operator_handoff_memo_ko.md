# Profitability / Operations P3-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p3_anomaly_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.json)
- [profitability_operations_p3_anomaly_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p3_anomaly_latest.md)

## 1. 현재 전체 상태

현재 P3 latest 기준 active alert는 62개다.

- `critical`: 1
- `high`: 25
- `medium`: 36

source 비중은 아래와 같다.

- lifecycle: 31
- expectancy: 21
- zero-pnl gap audit: 10

즉 지금은 단일 원인보다 `lifecycle pressure + expectancy drag + information gap`이 함께 보이는 상태다.

## 2. 지금 가장 먼저 볼 것

1. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
   - `critical`
   - `fast_adverse_close_alert`
   - 해석: 진입 직후 손실로 빠르게 꺾이는 패턴이 가장 강하다

2. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / UNKNOWN_REGIME`
   - `high`
   - `zero_pnl_information_gap_alert`
   - 해석: 경제성은 존재할 수 있지만 pnl field / attribution 공백 때문에 해석이 가려진다

3. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - `high`
   - `zero_pnl_information_gap_alert`
   - 해석: legacy sell bucket도 같은 정보 공백 성격이 강하다

4. `NAS100 / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - `high`
   - `zero_pnl_information_gap_alert`
   - 해석: NAS legacy sell도 운영 해석상 blind bucket이다

## 3. symbol별 운영 해석

### XAUUSD

- active alert 28개
- `critical 1 / high 16`
- 현재 가장 뜨거운 경보 중심이다
- `fast_adverse_close_alert`와 `zero_pnl_information_gap_alert`가 같이 보인다

### NAS100

- active alert 16개
- `high 8`
- zero-pnl information gap과 legacy bucket drag를 먼저 봐야 한다

### BTCUSD

- active alert 18개
- `high 1 / medium 17`
- 다른 심볼보다 catastrophic alert는 적지만 `blocked_pressure_alert`와 wait/consumer pressure 성격이 남아 있다

## 4. operator review 원칙

지금 review는 아래 순서가 맞다.

1. `critical fast adverse close`
2. `high zero-pnl information gap`
3. `high negative expectancy / legacy bucket blind`
4. `medium blocked / wait concentration`

즉 `실제 진입 품질 붕괴`를 먼저 보고,
그 다음 `경제성 해석 공백`을 정리하는 것이 맞다.

## 5. 다음 단계 handoff

P3 이후 가장 자연스러운 다음 단계는 `P4 time-series comparison`이다.

P4에서 바로 확인해야 할 질문은 아래다.

- 최근 창에서 XAUUSD critical fast adverse가 더 심해지고 있는가
- zero-pnl information gap bucket이 줄고 있는가, 늘고 있는가
- symbol별 alert 분포가 최근 배포/튜닝 이후 어떻게 이동했는가
