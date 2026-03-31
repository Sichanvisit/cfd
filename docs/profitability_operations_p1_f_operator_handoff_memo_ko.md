# Profitability / Operations P1-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 리포트:
- [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)
- [profitability_operations_p1_lifecycle_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.md)

## 1. 한 줄 상태

현재 P1 lifecycle surface 기준으로 보면, `BTCUSD decision lifecycle은 in-scope coverage 안에서 읽히고 있고`, `XAUUSD/NAS100 쪽은 legacy closed trade bucket에서 fast adverse close가 강하게 보이는 상태`다.

## 2. 지금 바로 봐야 하는 concern

1. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY / BUY`
   - `fast_adverse_close_cluster`
   - 의미: 저유동성 구간에서 진입 후 빠른 손실 청산이 반복된다.

2. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / LOW_LIQUIDITY / SELL`
   - `fast_adverse_close_cluster`
   - 의미: BUY 쪽과 대칭적으로 SELL 쪽도 같은 패턴이 보인다.

3. `NAS100 / legacy_trade_without_setup_id::SELL::balanced / LOW_LIQUIDITY / SELL`
   - `fast_adverse_close_cluster`
   - 의미: NAS100 저유동성 SELL legacy bucket도 빠른 역행 종료가 누적된다.

## 3. 지금 읽히는 strength

1. `BTCUSD / lower_hold_buy / RANGE / BUY`
   - decision lifecycle이 대부분 in-scope coverage 안에서 읽힌다.

2. `BTCUSD / middle_sr_anchor_required_observe / RANGE / BUY`
   - wait-heavy이긴 하지만, 적어도 coverage 안에서 일관되게 관측된다.

3. `BTCUSD / outer_band_reversal_support_required_observe / RANGE / BUY`
   - blocked/wait family가 명시적으로 드러나고 있다.

## 4. operator 관점 해석

- 지금 P1은 `무엇이 수익을 만드는가`보다 `어디서 lifecycle 이상이 반복되는가`를 읽는 단계다.
- BTC는 decision surface가 살아 있어서 `blocked_pressure`, `wait_heavy`를 직접 해석할 수 있다.
- XAU/NAS는 closed trade는 많지만, 일부는 `legacy_trade_without_setup_id::*` bucket으로 남아 있어 P2에서 expectancy를 읽을 때 `explicit setup bucket`과 `legacy bucket`을 분리해서 봐야 한다.

## 5. 지금 바로 review queue에 올릴 것

1. XAUUSD low-liquidity fast-adverse-close family
2. NAS100 low-liquidity fast-adverse-close family
3. BTCUSD `lower_hold_buy` blocked pressure (`energy_soft_block`)
4. BTCUSD `middle_sr_anchor_required_observe` wait-heavy

## 6. 다음 단계 handoff

P1 operator memo 기준으로 다음 단계는 P2다.

P2에서 반드시 분리해서 봐야 하는 축은 아래다.

- `explicit setup expectancy` vs `legacy without setup expectancy`
- `decision_winner / decision_reason / exit_wait_state` attribution
- `symbol / setup / regime` 기준 기대값 차이

즉 P1은 lifecycle concern queue를 만들었고, P2는 그 concern들이 실제로 `돈을 잃게 만드는지`를 수치로 확인하는 단계다.
