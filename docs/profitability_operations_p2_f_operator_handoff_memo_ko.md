# Profitability / Operations P2-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 리포트:
- [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)
- [profitability_operations_p2_expectancy_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.md)

## 1. 한 줄 상태

현재 P2 기준으로 보면, `closed trade는 충분히 많지만 nonzero pnl 비율이 낮아서 expectancy 해석 품질이 uneven`하고, 그중 일부 bucket은 실제 음수 expectancy이고 일부는 `zero-pnl information gap` 상태다.

## 2. 지금 먼저 봐야 하는 concern

1. `BTCUSD / range_upper_reversal_sell / NORMAL`
   - `zero_pnl_information_gap_cluster`
   - 의미: closed trade는 많은데 pnl이 전부 0이라 economic readability가 부족하다.

2. `NAS100 / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - `zero_pnl_information_gap_cluster`
   - 의미: legacy bucket + unknown regime 조합이라 해석 품질이 특히 낮다.

3. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / UNKNOWN_REGIME`
   - `zero_pnl_information_gap_cluster`
   - 의미: XAU legacy bucket도 같은 정보 공백이 남아 있다.

## 3. 실제 negative expectancy concern

1. `NAS100 / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
   - `negative_expectancy_cluster`
   - 의미: 저유동성 legacy BUY bucket이 실제 음수 기대값을 보인다.

2. 같은 bucket의 `legacy_bucket_blind_cluster`
   - 의미: 음수 기대값이 explicit setup이 아니라 legacy bucket 안에 숨어 있어서 해석/조정이 더 어렵다.

3. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / UNKNOWN`
   - `negative_expectancy_cluster`
   - 의미: regime 품질이 불안정한 구간에서 음수 기대값이 잡힌다.

## 4. strength

1. `BTCUSD / legacy_trade_without_setup_id::BUY::balanced / UNKNOWN`
   - positive expectancy가 관측된다.

2. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / LOW_LIQUIDITY`
   - positive expectancy bucket으로 남아 있다.

즉 P2 latest는 모든 legacy bucket이 다 나쁜 게 아니라, 일부는 positive expectancy를 유지하고 일부만 drag bucket이라는 점도 보여준다.

## 5. operator 관점 해석

- 지금 가장 먼저 결론 내리면 안 되는 것은 `zero-pnl information gap bucket`이다.
- 이런 bucket은 실제 음수라기보다, pnl 품질이 비어 있어서 경제적 해석을 보류해야 하는 대상이다.
- 반대로 `negative_expectancy_cluster`가 잡힌 bucket은 실제 손실 기대값으로 읽어야 한다.
- 따라서 operator review는 `정보 공백 버킷`과 `실제 음수 expectancy 버킷`을 분리해서 다뤄야 한다.

## 6. 지금 review queue에 올릴 것

1. zero-pnl information gap이 큰 explicit setup bucket
2. NAS100 low-liquidity legacy BUY negative expectancy bucket
3. XAUUSD legacy BUY negative expectancy bucket
4. explicit setup closed-trade에서 왜 pnl=0 row가 많이 남는지 quality audit

## 7. 다음 단계 handoff

P2 이후 가장 자연스러운 다음 단계는 P3다.

P3에서 바로 연결할 수 있는 항목은 아래다.

- zero-pnl information gap anomaly
- negative expectancy cluster anomaly
- forced-exit drag concentration anomaly

즉 P2는 이제 “무엇이 기대값을 깎는가”를 읽는 단계까지 왔고, 다음은 그 이상을 자동으로 감지하는 단계다.
