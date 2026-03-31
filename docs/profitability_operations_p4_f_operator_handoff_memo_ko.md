# Profitability / Operations P4-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p4_compare_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.json)
- [profitability_operations_p4_compare_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p4_compare_latest.md)

## 1. 현재 compare 요약

현재 P4 latest 기준 비교는 `recent row window vs immediately previous row window`다.

핵심 delta는 아래와 같다.

- `active_alert_delta`: 11
- `critical_delta`: 0
- `high_delta`: 0
- `avg_pnl_delta`: 0.0
- `zero_pnl_row_delta`: 0

즉 이번 compare에서 가장 크게 보이는 변화는 절대 수익률 변화보다 `운영 alert 분포 변화`다.

## 2. 최근 악화 top signal

1. `BTCUSD`
   - `active_alert_delta = +4`
   - 최근 창에서 blocked / skip 계열 pressure가 커졌다

2. `NAS100`
   - `active_alert_delta = +4`
   - 최근 창에서 skip / blocked / legacy drag가 같이 보인다

3. `XAUUSD`
   - `active_alert_delta = +3`
   - zero-pnl information gap과 legacy drag 쪽이 계속 두드러진다

4. `blocked_pressure_alert`
   - `delta = +5`

5. `skip_heavy_alert`
   - `delta = +4`

6. `zero_pnl_information_gap_alert`
   - `delta = +4`

## 3. 최근 완화 signal

- `cut_now_concentration_alert`
  - `delta = -3`

즉 최근 창에서는 cut_now 집중은 완화됐지만,
그 대신 blocked / skip / information-gap 성격이 더 커졌다.

## 4. 운영 해석

이번 compare에서 중요한 건 아래다.

- 지금 악화는 `즉시 catastrophic severity 상승`보다 `운영 pressure 구조 변화`에 가깝다
- 최근 창에서 blocked / skip / information gap이 더 많이 보인다
- 따라서 P5로 넘어갈 때는 `cut_now 완화`를 긍정 신호로 보되,
  `blocked/skip/information gap 증가`를 casebook review 우선순위로 올리는 것이 맞다

## 5. 다음 단계 handoff

P4 이후 가장 자연스러운 다음 단계는 `P5 optimization loop / casebook strengthening`이다.

P5에서 우선 review할 후보는 아래다.

1. `BTCUSD / blocked_pressure_alert`
2. `BTCUSD / skip_heavy_alert`
3. `NAS100 / legacy bucket pressure`
4. `XAUUSD / zero_pnl information gap`
