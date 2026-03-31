# BF3 Management Fast Cut Risk Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `BF3 management_fast_cut_risk_v1`를 실제 구현 가능한 순서로 정리한 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf3_management_fast_cut_risk_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/bridge_first_bf3_management_fast_cut_risk_detailed_reference_ko.md)

## 2. 전체 순서

```text
BF3-A. input contract freeze
-> BF3-B. bridge summary shape 정의
-> BF3-C. feature metadata wiring
-> BF3-D. trade management forecast blend + reason trace
-> BF3-E. contract / regression test
-> BF3-F. close-out
```

## 3. BF3-A. input contract freeze

목표:
- BF3에서 쓸 입력을 기존 semantic 입력으로 고정한다.

해야 할 일:
1. `State / Evidence / Belief / Barrier`만 사용한다.
2. raw detector / raw collector direct-use는 추가하지 않는다.
3. BF3가 owner가 아니라 modifier라는 점을 고정한다.

## 4. BF3-B. bridge summary shape 정의

목표:
- 아래 4개 출력을 canonical shape로 고정한다.

- `fast_cut_risk`
- `collision_risk`
- `event_caution`
- `cut_now_allowed`

해야 할 일:
1. contract/version/role 정의
2. component score shape 정의
3. reason summary surface 정의

## 5. BF3-C. feature metadata wiring

목표:
- `forecast_features_v1.metadata.bridge_first_v1`에 BF3 summary를 추가한다.

해야 할 일:
1. BF3 helper 구현
2. build_forecast_features에 연결
3. feature contract test 보강

## 6. BF3-D. trade management forecast blend + reason trace

목표:
- management forecast가 BF3 summary를 실제로 읽고 fail/reentry 쪽 negative caution을 반영하게 한다.

해야 할 일:
1. BF3 read helper 추가
2. `p_continue_favor`, `p_fail_now`, `p_recover_after_pullback`, `p_reach_tp1`, `p_opposite_edge_reach`, `p_better_reentry_if_cut`에 soft blend
3. metadata / component_scores / forecast_reasons에 BF3 trace 남기기

## 7. BF3-E. contract / regression test

목표:
- BF3가 문서만 있는 게 아니라 테스트 계약으로 잠긴 상태를 만든다.

해야 할 일:
1. feature metadata에 BF3 summary 노출 테스트
2. management forecast metadata/reason trace 테스트
3. BF3가 fail/reentry 쪽을 실제로 boost 하는 differential test

## 8. BF3-F. close-out

목표:
- BF3 first-pass를 닫고 다음 bridge로 넘긴다.

해야 할 일:
1. BF3 구현 메모 작성
2. 다음 active step 결정

다음 후보:
- `BF4 trend_continuation_maturity_v1`

## 9. 지금 바로 구현할 범위

이번 턴에서 자연스러운 구현 범위는 아래다.

1. `BF3-A`
2. `BF3-B`
3. `BF3-C`
4. `BF3-D`
5. `BF3-E`

즉 BF3 first-pass를 metadata -> management forecast -> tests까지 한 번에 잠그는 것이 목표다.

## 10. 한 줄 요약

```text
BF3는 fast-cut caution bridge를 feature metadata에 만들고, trade management forecast에 약하게 blend한 뒤 계약 테스트로 잠그는 first-pass 구현 단계다.
```
