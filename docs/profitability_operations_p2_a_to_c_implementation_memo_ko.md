# Profitability / Operations P2-A~P2-C Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 범위

이번 구현 범위는 아래 세 단계다.

- `P2-A`: closed trade scope and bucket split
- `P2-B`: expectancy summary shape
- `P2-C`: first canonical expectancy / attribution report script

## 2. 구현 산출물

- canonical script:
  - [profitability_operations_p2_expectancy_attribution_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p2_expectancy_attribution_report.py)
- latest outputs:
  - [profitability_operations_p2_expectancy_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.json)
  - [profitability_operations_p2_expectancy_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.csv)
  - [profitability_operations_p2_expectancy_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p2_expectancy_latest.md)
- tests:
  - [test_profitability_operations_p2_expectancy_attribution_report.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_profitability_operations_p2_expectancy_attribution_report.py)

## 3. 이번 구현에서 고정한 것

- closed trade는 `explicit_setup / legacy_without_setup / snapshot_restored_auto` bucket으로 먼저 분리한다.
- expectancy 계산은 `net_pnl_after_cost` 우선, 없으면 `profit` fallback이다.
- attribution은 `decision_winner / decision_reason / exit_wait_state / entry_stage / exit_policy_stage / exit_policy_profile` 기준으로 집계한다.
- first report는 `overall / readiness / bucket / symbol / setup / regime / symbol_setup / setup_regime / attribution summaries / negative clusters / quick read` shape로 고정한다.

## 4. 현재 해석에서 중요한 주의점

- 현재 latest data에서 `legacy_without_setup` closed trade 비중이 크다.
- explicit setup closed trade는 많지만, 일부 bucket은 `pnl=0` row가 많이 섞여 있어 경제적 readability를 주의해서 봐야 한다.
- 따라서 P2 latest report는 숫자를 보여주되, `explicit setup expectancy`와 `legacy bucket expectancy`를 섞지 않고 해석해야 한다.

## 5. 지금 latest에서 바로 읽을 수 있는 것

- 어떤 symbol/setup/regime bucket이 negative expectancy인지
- 어떤 exit attribution family가 손실 drag를 만들고 있는지
- `forced exit`, `reverse`, `recovery`가 각 bucket에서 어느 정도 비중인지
- attribution이 충분히 채워진 closed trade 비율이 어느 정도인지

## 6. 다음 자연스러운 단계

P2 관점에서 가장 자연스러운 다음 단계는 아래다.

1. `P2-D grouping expansion`
2. `P2-E negative expectancy / drag cluster refinement`
3. `P2-F operator memo / handoff`

즉 P2는 이제 첫 수치 surface가 열린 상태고, 다음부터는 grouping을 더 넓히고 drag cluster를 더 선명하게 만드는 단계로 가면 된다.
