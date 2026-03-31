# Profitability / Operations P4 Time-Series Comparison Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `P4 time-series comparison`이 무엇인지, 왜 필요한지, 어떤 비교 기준으로 구현해야 하는지 고정하기 위한 상세 기준 문서다.

P4의 핵심 질문은 하나다.

`지금 보이는 P1/P2/P3 concern이 직전 창과 비교해서 실제로 악화되고 있는가, 완화되고 있는가?`

## 2. 왜 P4가 필요한가

P1은 lifecycle concern을 보여준다.
P2는 expectancy와 attribution drag를 보여준다.
P3는 그 concern을 운영 경보로 승격한다.

하지만 P3까지 가도 아직 모르는 것이 있다.

- 이 alert는 원래부터 크던 것인가
- 최근 들어 갑자기 커진 것인가
- 특정 symbol이 최근에만 악화된 것인가
- 이전 창보다 지금이 더 나빠진 것인지, 단지 절대값이 큰 것인지

P4는 이 질문에 답하는 단계다.

## 3. P4가 아닌 것

P4는 아직 최적화나 자동 조정이 아니다.

- tuning parameter를 바꾸지 않는다
- operator action을 자동 적용하지 않는다
- blacklist를 자동으로 업데이트하지 않는다

즉 P4는 `비교 해석` 단계다.

## 4. P4 첫 버전의 비교 기준

첫 버전은 `recent row window vs immediately previous row window` 비교로 간다.

즉 아래 두 창을 비교한다.

- `current window`
- `previous window`

각 창은 raw source의 tail row를 동일한 window size로 자른다.

### 첫 버전에서 이렇게 하는 이유

- 기존 P1/P2/P3 script를 재사용할 수 있다
- immediate worsening / improving trend를 빠르게 읽을 수 있다
- deploy marker가 아직 없는 상태에서도 비교가 가능하다

## 5. 입력 source

### raw source

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [entry_decisions.detail.jsonl](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.detail.jsonl)
- [trade_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_history.csv)
- [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv)

### reused build surface

P4는 raw source를 직접 집계하기보다, 각 window에 대해 아래 canonical build를 다시 수행한 뒤 비교한다.

- P1 lifecycle
- P2 expectancy
- P2 zero-pnl gap audit
- P3 anomaly / alerting

## 6. 첫 버전 canonical 출력 shape

### latest json

필수 section:

- `compare_scope`
- `window_source_summary`
- `overall_delta_summary`
- `p1_cluster_type_deltas`
- `p2_cluster_type_deltas`
- `p3_alert_type_deltas`
- `symbol_alert_deltas`
- `worsening_signal_summary`
- `improving_signal_summary`
- `quick_read_summary`

### latest csv

symbol / alert delta flat row export.

### latest md

operator가 바로 읽는 compare memo.

## 7. P4에서 반드시 분리해야 하는 것

1. `absolute large concern`과 `recent worsening`
2. `information gap 악화`와 `negative expectancy 악화`
3. `symbol worsening`과 `alert type worsening`

즉 단순히 지금 큰 것만 보여주면 안 되고,
직전 창 대비 `delta`가 무엇인지 같이 보여야 한다.

## 8. 첫 버전 완료 기준

P4 첫 버전이 완료됐다고 보려면 아래가 가능해야 한다.

1. current / previous 두 창이 canonical build surface로 재생성된다.
2. P3 active alert count와 severity가 창간 delta로 읽힌다.
3. symbol별 alert 집중도가 delta로 읽힌다.
4. worsening / improving signal 요약이 나온다.
5. operator가 latest markdown만 보고 "무엇이 최근 더 나빠졌는지"를 말할 수 있다.

## 9. 결론

P4는 `P1/P2/P3 observability를 최근 변화량 해석으로 승격하는 단계`다.
첫 버전은 row-window compare로 가고, 이후에 deploy before/after compare는 확장 사항으로 붙인다.
