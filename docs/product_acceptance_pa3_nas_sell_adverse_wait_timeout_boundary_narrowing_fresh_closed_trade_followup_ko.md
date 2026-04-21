# Product Acceptance PA3 NAS Sell Adverse-Wait Timeout Boundary Narrowing Fresh Closed-Trade Follow-Up

## 확인 시점

- baseline refreeze 기준: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
- `generated_at = 2026-04-01T19:32:10`

## 결론

이번 follow-up 기준으로는 `fresh closed trade`가 더 쌓였다고 보기 어렵다.

근거:

- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv) row count는 `139`
- 최근 tail close row도 여전히 `2026-03-02 20:20:38` 근방에 머문다
- 즉 `PA3-1` patch 이후 새 close artifact가 추가로 누적된 상태는 아니다

그래서 이번 refreeze에서도 target family는 그대로 유지됐다.

- `must_hold = 2`
- 대표 ticket:
  - `91758855`
  - `91765176`

## 해석

이번 확인의 의미는 아래와 같다.

1. `PA3-1` 코드/테스트/런타임 반영은 이미 끝났다
2. 하지만 closed-trade 기반 phase 특성상,
   새 close row가 없으면 `must_hold` 숫자는 그대로일 수밖에 없다
3. 따라서 현재 상태는 `fresh closed trade pending`이 맞다

## 부수 관찰

이번 refreeze에서는 closed-trade queue는 그대로였지만,
recent runtime turnover 때문에 entry/chart baseline은 다시 일부 흔들렸다.

- `must_show_missing = 6`
- `must_hide_leakage = 1`
- `must_block_candidate = 6`

이 변화는 `PA3-1` 실패가 아니라,
exit phase와 별개로 live entry/chart recent window가 다시 바뀐 결과로 본다.

## 다음

- fresh close row가 실제로 추가되면 다시 PA0 refreeze
- 그때 `must_hold 2 -> 0` 또는 `2 -> 감소` 여부를 재확인
- 동시에 `PA4 exit acceptance`는 병렬로 진행 가능
