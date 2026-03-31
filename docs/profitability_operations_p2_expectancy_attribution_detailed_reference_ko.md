# Profitability / Operations P2 Expectancy / Attribution Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P2 expectancy / attribution observability`가 무엇인지, 왜 필요한지, 어떤 입력과 출력으로 구현해야 하는지를 고정하기 위한 상세 기준 문서다.

P2의 핵심 질문은 하나다.

`어떤 symbol / setup / regime / exit family가 실제로 기대값을 만들고, 어떤 축이 기대값을 깎고 있는가?`

## 2. 왜 P2가 필요한가

P1은 lifecycle을 읽는다.

- 어디서 wait가 몰리는가
- 어디서 blocked pressure가 몰리는가
- 어디서 fast adverse close가 반복되는가

하지만 P1만으로는 아직 부족하다.

- wait-heavy가 실제로 수익 보호인지, 기회 손실인지
- cut_now 집중이 손실 최소화인지, 과도한 조기 청산인지
- reverse_now가 비용인지, 구조적 방어인지
- 어떤 setup이 실제로 돈을 버는지

를 숫자로 답하지 못한다.

P2는 바로 그 부분을 담당한다.

## 3. P2가 아닌 것

P2는 아직 자동 최적화가 아니다.

- threshold를 바로 바꾸지 않는다
- blacklist를 자동으로 적용하지 않는다
- anomaly alert를 쏘지 않는다
- 시계열 before/after compare를 본격적으로 하지 않는다

즉 P2는 `수익 기여를 수치화하는 관측 단계`이지, `자동 의사결정 단계`가 아니다.

## 4. P2 입력 소스

### closed trade source

- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv)

핵심 필드:

- `symbol`
- `direction`
- `entry_setup_id`
- `regime_at_entry`
- `entry_stage`
- `exit_policy_stage`
- `exit_policy_profile`
- `decision_winner`
- `decision_reason`
- `exit_wait_state`
- `profit`
- `net_pnl_after_cost`
- `open_time`
- `close_time`

### 보조 기준 소스

- [profitability_operations_p1_lifecycle_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p1_lifecycle_latest.json)
- [profitability_operations_p1_f_operator_handoff_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_f_operator_handoff_memo_ko.md)

P2는 closed-trade 중심이지만, P1에서 만든 concern queue를 해석 우선순위로 참고한다.

## 5. P2 핵심 해석 단위

### 5-1. expectancy

최소한 아래를 각 그룹별로 읽어야 한다.

- `closed_trade_count`
- `net_pnl_sum`
- `avg_pnl`
- `win_rate`
- `avg_win`
- `avg_loss`
- `profit_factor`
- `avg_hold_seconds`

### 5-2. attribution

기대값을 깎거나 만드는 원인을 아래 축으로 읽어야 한다.

- `decision_winner`
- `decision_reason`
- `exit_wait_state`
- `entry_stage`
- `exit_policy_stage`
- `exit_policy_profile`

### 5-3. explicit vs legacy separation

P2에서 가장 중요한 분리 규칙은 이것이다.

- `explicit setup bucket`
- `legacy without setup bucket`
- `snapshot_restored_auto bucket`

특히 현재 데이터에서는 closed trade에 `entry_setup_id`가 비어 있는 legacy row가 많기 때문에, explicit setup과 legacy bucket을 섞으면 잘못된 결론이 나온다.

## 6. P2 출력 형태

### 6-1. latest json

기계적으로 다시 읽을 수 있는 canonical report.

필수 section:

- overall expectancy summary
- coverage / attribution readiness summary
- symbol expectancy summary
- setup expectancy summary
- regime expectancy summary
- symbol-setup expectancy summary
- decision_winner attribution summary
- decision_reason attribution summary
- exit_wait_state attribution summary
- stage attribution summary
- negative expectancy cluster summary
- operator quick read

### 6-2. latest csv

setup/symbol/regime 기준 flat row.

### 6-3. latest md

운영자가 바로 읽는 quick memo.

## 7. P2에서 반드시 분리해야 하는 것

1. `explicit setup`과 `legacy without setup`
2. `gross profit`과 `net after cost`
3. `count가 큰 그룹`과 `expectancy가 음수인 그룹`
4. `forced exit family`와 `reverse/recovery family`

## 8. P2가 답해야 하는 질문

- 어떤 setup이 실제로 plus expectancy인가
- 어떤 regime에서 expectancy가 급격히 나빠지는가
- cut_now / exit_now / reverse_now 중 무엇이 실제 손실 기여가 큰가
- wait_be / recovery 계열이 실제로 기대값을 회복시키는가
- explicit setup 기준과 legacy bucket 기준 결론이 얼마나 다른가

## 9. 완료 기준

P2가 완료되었다고 보려면 최소한 아래가 가능해야 한다.

1. setup/symbol/regime 기준 expectancy를 숫자로 읽을 수 있다.
2. decision_winner / decision_reason / exit_wait_state attribution을 따로 읽을 수 있다.
3. explicit setup과 legacy bucket을 섞지 않은 해석이 가능하다.
4. operator가 latest md만 읽고도 `무엇이 실제로 기대값을 깎는가`를 말할 수 있다.

## 10. 한 줄 결론

P2는 `P1에서 만든 lifecycle concern을, 실제 수익 기대값과 attribution 숫자로 번역하는 단계`다. P1이 “어디가 이상한가”를 읽었다면, P2는 “그 이상이 실제로 돈을 잃게 만드는가”를 읽는다.
