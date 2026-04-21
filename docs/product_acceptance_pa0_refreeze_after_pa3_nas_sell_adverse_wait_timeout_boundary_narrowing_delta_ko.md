# Product Acceptance PA0 Refreeze After PA3 NAS Sell Adverse-Wait Timeout Boundary Narrowing Delta

## 기준

- before: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T18:23:29`
- after: [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T19:03:02`

## 이번 refreeze 해석

이번 refreeze의 목적은 `PA3-1 first patch`가 closed-trade artifact에 바로 반영되는지 확인하는 것이었다.

핵심 결론:

- `must_hold 2`는 그대로 유지됐다
- 대표 family도 그대로 `NAS100 SELL + hard_guard=adverse + adverse_wait=timeout + bad_wait` 2건이다
- 따라서 이번 턴 기준 해석은 `코드/테스트/런타임 반영 완료`, `fresh closed trade 대기`가 맞다

## 대상 family 상태

대표 ticket:

- `91758855` -> `adverse_wait=timeout(349s)`
- `91765176` -> `adverse_wait=timeout(174s)`

즉 현재 baseline은 여전히 과도한 timeout bad-wait 사례를 보여주고 있고,
이번 patch는 이와 같은 새 close row가 다시 쌓일 때부터 의미 있게 비교된다.

## 부수 관찰

이번 refreeze에서는 exit queue 외에 runtime row turnover 영향도 같이 보였다.

- `must_show_missing_count`: `0 -> 2`
- `must_enter_candidate_count`: `0 -> 6`

이 변화는 `PA3-1` 구현 실패 신호가 아니라,
entry/chart recent window가 새 row로 다시 채워진 결과로 본다.

## 다음 확인 포인트

다음은 아래 순서가 자연스럽다.

1. fresh closed trade가 더 쌓이는지 확인
2. 동일 family가 새 close row에서도 `adverse_wait=timeout(...)`로 과도하게 남는지 확인
3. 그 뒤 PA0를 다시 얼려 `must_hold 2`가 줄었는지 본다
