# Profitability / Operations P1-D~P1-E Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 범위

이번 구현 범위는 아래 두 단계다.

- `P1-D`: grouping expansion
- `P1-E`: suspicious lifecycle cluster refinement

기준 script는 [profitability_operations_p1_lifecycle_correlation_report.py](C:\Users\bhs33\Desktop\project\cfd\scripts\profitability_operations_p1_lifecycle_correlation_report.py) 이다.

## 2. 이번에 확장한 grouping

기존 `symbol / setup / regime` 중심 summary를 아래까지 확장했다.

- `side_summary`
- `symbol_setup_summary`
- `symbol_regime_summary`
- `lifecycle_family_summary`를 `symbol / setup / regime / side` 기준으로 재정의

즉 이제 lifecycle family는 단순 setup family가 아니라 `같은 setup이라도 BUY/SELL side가 다르면 분리해서` 읽는다.

## 3. 이번에 보강한 side 해석

decision row 쪽 side가 비어 있는 경우를 위해 아래 순서로 보강했다.

1. `setup_side`
2. `consumer_check_side`
3. `observe_side`
4. `action`
5. `consumer_effective_action`
6. 없으면 `setup/archetype/observe_reason` 문자열의 `buy/sell` suffix에서 추론

그래서 `range_upper_reversal_sell`, `lower_hold_buy` 같은 family는 decision row에 side column이 비어 있어도 family alignment가 더 자연스럽게 맞는다.

## 4. 이번에 보강한 suspicious cluster

기존 `fast_adverse_close`, `wait_heavy`, `skip_heavy`, `cut_now_concentration` 중심에서 아래 cluster를 추가/보강했다.

- `coverage_blind_spot_cluster`
- `blocked_pressure_cluster`
- `wait_to_forced_exit_cluster`
- `reverse_now_cluster`
- 기존 `fast_adverse_close_cluster`
- 기존 `cut_now_concentration_cluster`

또한 cluster마다 아래 metadata를 함께 남긴다.

- `symbol`
- `setup_key`
- `regime_key`
- `side_key`
- `family_root_key`
- `score`
- `reason`

## 5. quick read refinement

quick read queue는 이제 raw top-N이 아니라 아래 기준으로 압축한다.

- `cluster_type + symbol + setup_key` 기준 dedupe

즉 같은 setup의 regime 변형이 여러 개 떠도, operator view에서는 더 압축된 concern queue를 먼저 보게 된다.

## 6. 현재 latest report에서 추가로 읽을 수 있는 것

이제 latest report에서 아래를 더 직접 읽을 수 있다.

- 어떤 setup이 어느 side에서 더 취약한가
- symbol 안에서 setup별 lifecycle이 어떻게 갈리는가
- 같은 symbol 안에서 regime별 lifecycle 차이가 있는가
- `blocked pressure`, `forced exit`, `reverse now`가 어떤 family에 몰리는가

## 7. 다음 자연스러운 단계

P1 관점에서 가장 자연스러운 다음 단계는 아래다.

1. `P1-F quick-read memo/operator handoff`를 현재 latest report 기반으로 더 선명하게 다듬기
2. 그다음 `P2 expectancy / attribution`로 넘어가기

즉 P1 자체는 이제 first canonical lifecycle surface를 넘어서, grouping과 suspicious cluster까지 열린 상태다.
