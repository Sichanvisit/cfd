# BF4 Trend Continuation Maturity Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `BF4 trend_continuation_maturity_v1`를 실제 구현 가능한 순서로 정리한 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf4_trend_continuation_maturity_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/bridge_first_bf4_trend_continuation_maturity_detailed_reference_ko.md)

## 2. 전체 순서

```text
BF4-A. input contract freeze
-> BF4-B. bridge summary shape 정의
-> BF4-C. feature metadata wiring
-> BF4-D. trade management forecast blend + reason trace
-> BF4-E. contract / regression test
-> BF4-F. close-out
```

## 3. BF4-A. input contract freeze

목표:
- BF4에서 쓸 입력을 기존 semantic 입력으로 고정한다.

해야 할 일:
1. `State / Evidence / Belief / Barrier`만 사용한다.
2. raw detector / raw collector direct-use는 추가하지 않는다.
3. BF4가 owner가 아니라 modifier라는 점을 고정한다.

## 4. BF4-B. bridge summary shape 정의

목표:
- 아래 3개 출력을 canonical shape로 고정한다.

- `continuation_maturity`
- `exhaustion_pressure`
- `trend_hold_confidence`

해야 할 일:
1. contract/version/role 정의
2. component score shape 정의
3. reason summary surface 정의

## 5. BF4-C. feature metadata wiring

목표:
- `forecast_features_v1.metadata.bridge_first_v1`에 BF4 summary를 추가한다.

해야 할 일:
1. BF4 helper 구현
2. build_forecast_features에 연결
3. feature contract test 보강

## 6. BF4-D. trade management forecast blend + reason trace

목표:
- management forecast가 BF4 summary를 실제로 읽고 trend continuation confidence를 반영하게 한다.

해야 할 일:
1. BF4 read helper 추가
2. `p_continue_favor`, `p_fail_now`, `p_recover_after_pullback`, `p_reach_tp1`, `p_opposite_edge_reach`에 soft blend
3. metadata / component_scores / forecast_reasons에 BF4 trace 남기기

## 7. BF4-E. contract / regression test

목표:
- BF4가 문서만 있는 게 아니라 테스트 계약으로 잠긴 상태를 만든다.

해야 할 일:
1. feature metadata에 BF4 summary 노출 테스트
2. management forecast metadata/reason trace 테스트
3. BF4가 continue/reach 쪽을 실제로 boost 하는 differential test

## 8. BF4-F. close-out

목표:
- BF4 first-pass를 닫고 다음 bridge로 넘긴다.

해야 할 일:
1. BF4 구현 메모 작성
2. 다음 active step 결정

다음 후보:
- `BF5 advanced_input_reliability_v1`

## 9. 지금 바로 구현할 범위

이번 턴에서 자연스러운 구현 범위는 아래다.

1. `BF4-A`
2. `BF4-B`
3. `BF4-C`
4. `BF4-D`
5. `BF4-E`

즉 BF4 first-pass를 metadata -> management forecast -> tests까지 한 번에 잠그는 것이 목표다.

## 10. 한 줄 요약

```text
BF4는 trend continuation maturity bridge를 feature metadata에 만들고, trade management forecast에 약하게 blend한 뒤 계약 테스트로 잠그는 first-pass 구현 단계다.
```
