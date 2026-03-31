# Profitability / Operations P2-D~P2-F Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 범위

이번 구현 범위는 아래 세 단계다.

- `P2-D`: grouping expansion
- `P2-E`: drag cluster refinement
- `P2-F`: operator memo / handoff

## 2. 이번에 확장한 grouping

P2 latest report는 이제 아래 grouping을 함께 제공한다.

- `direction_expectancy_summary`
- `symbol_regime_expectancy_summary`
- `bucket_regime_expectancy_summary`
- 기존 `symbol_setup_expectancy_summary`
- 기존 `setup_regime_expectancy_summary`
- 기존 `symbol_setup_regime_expectancy_summary`

즉 이제 setup과 regime뿐 아니라 direction과 setup bucket 관점에서도 expectancy를 읽을 수 있다.

## 3. 이번에 보강한 drag cluster

이제 negative cluster는 단순 음수 expectancy만 보는 것이 아니라 아래를 함께 읽는다.

- `zero_pnl_information_gap_cluster`
- `negative_expectancy_cluster`
- `forced_exit_drag_cluster`
- `reverse_drag_cluster`
- `legacy_bucket_blind_cluster`

또한 `negative_expectancy_cluster_type_summary`를 추가해서 어떤 drag 유형이 전체적으로 많이 나타나는지 한 번에 볼 수 있게 했다.

## 4. operator 관점 의미

현재 P2 latest는 두 가지를 동시에 보여준다.

1. 실제로 평균 pnl이 음수인 bucket
2. closed trade는 많지만 pnl이 0이라 경제적 expectancy 해석이 아직 불가능한 bucket

즉 operator는 이제 `이 bucket이 손실인가?`와 함께 `이 bucket은 아직 pnl quality가 부족해서 판단을 미뤄야 하는가?`도 동시에 읽을 수 있다.

## 5. handoff 의미

P2-F memo는 단순 top-N 요약이 아니라 아래를 분리해서 읽게 만든다.

- 경제적으로 실제 손실을 만드는 bucket
- zero-pnl 때문에 아직 해석 품질이 부족한 bucket
- positive expectancy를 보이는 strength bucket

## 6. 다음 자연스러운 단계

P2는 이제 첫 expectancy/attribution surface와 drag cluster까지 열린 상태다.

다음은 두 갈래다.

1. `P3 alerting / anomaly detection`
2. 또는 P2를 조금 더 밀어서 operator memo를 주기적/자동 surface로 다듬기

즉 지금부터는 P2를 “보는 도구”에서 “운영 판단 트리거”로 승격시키는 단계로 넘어가면 된다.
