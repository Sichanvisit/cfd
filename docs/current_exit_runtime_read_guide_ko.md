# 현재 청산 Runtime 읽기 가이드

작성일: 2026-03-29 (KST)
대상: 새 스레드, 운영 점검, recent exit 흐름 빠른 해석

## 1. 먼저 어디를 보면 되나

가장 먼저 보는 순서는 이렇다.

1. `data/runtime_status.json`
2. `data/runtime_status.detail.json`
3. 필요하면 `data/trades/trade_history.csv`

핵심은 청산도 이제 `최근 몇 건에서 어떤 hold/exit/reverse 패턴이 많았는지`를
runtime surface에서 먼저 읽고, 정말 필요할 때만 trade history로 내려가면 된다는 점이다.


## 2. slim surface에서 먼저 볼 것

`runtime_status.json`에서 먼저 보는 핵심 필드는 아래다.

- `recent_exit_summary_window`
- `recent_exit_status_counts`
- `recent_exit_symbol_summary`
- `recent_exit_state_semantic_summary`
- `recent_exit_decision_summary`
- `recent_exit_state_decision_bridge_summary`


## 3. detail surface에서 먼저 볼 것

경로:

- `recent_exit_runtime_diagnostics.windows.last_200`

핵심 필드:

- `status_counts`
- `exit_state_semantic_summary`
- `exit_decision_summary`
- `exit_state_decision_bridge_summary`
- `symbol_summary.<SYMBOL>.*`

읽는 순서는 이게 가장 빠르다.

1. `status_counts`
2. `exit_state_semantic_summary`
3. `exit_decision_summary`
4. `exit_state_decision_bridge_summary`
5. `symbol_summary.<SYMBOL>` 상세


## 4. `exit_state_semantic_summary` 읽는 법

이 요약은 최근 청산 state가 어떤 계열로 많이 나타나는지 보여준다.

주로 봐야 할 건:

- `state_counts`
- `state_family_counts`
- `hold_class_counts`

이건
`최근 exit가 왜 바로 나가지 않고 머뭇거렸는가`
를 구조적으로 보는 용도다.


## 5. `exit_decision_summary` 읽는 법

이 요약은 최근 청산 decision이 어떤 결과로 귀결됐는지 보여준다.

주로 봐야 할 건:

- `winner_counts`
- `decision_family_counts`
- `decision_reason_counts`
- `wait_selected_rate`

이건
`최근 청산이 실제로 어디로 기울고 있나`
를 보는 용도다.


## 6. `exit_state_decision_bridge_summary` 읽는 법

이 요약은 state와 decision 사이 연결을 보여준다.

주로 봐야 할 건:

- `bridge_status_counts`
- `state_to_decision_counts`

중요한 건 state 요약만 보지 말고 bridge를 같이 봐야 한다는 점이다.


## 7. 심볼별로 읽는 가장 빠른 순서

경로:

- `recent_exit_runtime_diagnostics.windows.last_200.symbol_summary.<SYMBOL>`

권장 순서:

1. `status_counts`
2. `exit_state_semantic_summary`
3. `exit_decision_summary`
4. `exit_state_decision_bridge_summary`


## 8. 증상별 바로 해석

- `winner_counts`에서 `wait_exit`가 높다
  - 최근 청산이 즉시 종료보다 hold/recovery 쪽으로 많이 기울고 있다
- `decision_reason_counts`에서 recovery 계열이 높다
  - recovery policy나 overlay가 최근 주도 원인일 가능성이 높다
- `state_family_counts`는 recovery 쪽이 높은데 `winner_counts`는 `exit_now`가 높다
  - recovery state는 자주 생기지만 decision 단계에서 빨리 청산으로 풀린다
- `bridge_status_counts`에서 mismatch가 높다
  - state와 decision 사이 해석층에서 변환이 많이 일어난다


## 9. 언제 `trade_history.csv`까지 내려가나

아래 경우에만 내려가면 된다.

- 특정 심볼에서 이유 하나를 직접 row 단위로 확인하고 싶을 때
- runtime summary와 체감이 다를 때
- 특정 close reason / decision reason 조합을 직접 확인하고 싶을 때

그 외에는 recent runtime summary만으로도 운영 판단은 대부분 가능하다.
