# BF1 Act-vs-Wait Bias Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 `BF1 act_vs_wait_bias_v1`를 실제로 구현하는 순서를 정리한 로드맵이다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf1_act_vs_wait_bias_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_bf1_act_vs_wait_bias_detailed_reference_ko.md)

## 2. 전체 순서

```text
BF1-A. input contract freeze
-> BF1-B. bridge summary shape 정의
-> BF1-C. forecast feature wiring
-> BF1-D. transition forecast blend + reason trace
-> BF1-E. product acceptance awareness wiring
-> BF1-F. audit / close-out
```

## 3. BF1-A. input contract freeze

### 목표

BF1이 읽을 입력을 먼저 고정한다.

### 해야 할 일

1. `State / Evidence / Belief / Barrier`만 BF1 입력으로 사용한다.
2. secondary raw / order_book / 새 raw field는 이번 단계에 포함하지 않는다.
3. BF1이 owner가 아니라 modifier라는 점을 코드/문서로 고정한다.

### 주 대상 파일

- `backend/trading/engine/core/forecast_features.py`
- `backend/services/consumer_contract.py`

### 완료 기준

- BF1 input contract가 metadata에 설명 가능하게 남는다.

## 4. BF1-B. bridge summary shape 정의

### 목표

아래 세 값을 canonical shape로 고정한다.

- `act_vs_wait_bias`
- `false_break_risk`
- `awareness_keep_allowed`

### 해야 할 일

1. contract/version/name 정의
2. component score shape 정의
3. reason summary surface 정의

### 완료 기준

- `forecast_features_v1.metadata.bridge_first_v1.act_vs_wait_bias_v1` shape가 고정된다.

## 5. BF1-C. forecast feature wiring

### 목표

BF1 summary를 forecast feature metadata에 실제로 심는다.

### 해야 할 일

1. bridge summary helper 구현
2. build_forecast_features에 연결
3. forecast feature contract test 보강

### 완료 기준

- feature build 결과에서 BF1 summary가 항상 읽힌다.

## 6. BF1-D. transition forecast blend + reason trace

### 목표

transition forecast가 BF1 summary를 읽고
`p_false_break` pressure에 약하게 반영하도록 한다.

### 해야 할 일

1. BF1 summary read helper 추가
2. false-break pressure에 additive blend
3. metadata / component_scores / forecast_reasons에 BF1 흔적 남기기

### 완료 기준

- transition forecast metadata에 BF1 summary와 reason이 같이 남는다.

## 7. BF1-E. product acceptance awareness wiring

### 목표

consumer/product acceptance 쪽에서 BF1 summary를 awareness preserve에 제한적으로 사용한다.

### 해야 할 일

1. payload에서 BF1 summary 읽기
2. soft wait / awareness 장면에서 `awareness_keep_allowed`를 제한적으로 반영
3. `bridge_first_adjustment_reason` surface 남기기

### 완료 기준

- chart/product acceptance 쪽에서도 BF1 summary를 읽고 최소한 awareness preserve에 활용한다.

## 8. BF1-F. audit / close-out

### 목표

BF1의 첫 효과를 검증하고 다음 step을 정한다.

### 해야 할 일

1. BF1 contract / regression 테스트 통과
2. false-break / awareness 관련 latest audit 확인
3. BF2 또는 BF3로 handoff

### 완료 기준

- BF1 first-pass close-out memo가 생긴다.

## 9. 지금 바로 구현할 범위

현재 턴에서 가장 자연스러운 구현 범위는 아래다.

1. `BF1-A`
2. `BF1-B`
3. `BF1-C`
4. `BF1-D`
5. `BF1-E`의 awareness preserve 최소 연결

즉 BF1은 문서만 쓰고 끝내지 않고,
`forecast_features -> transition_forecast -> consumer_check_state`
까지 첫 흐름을 실제로 연결하는 것이 목표다.

## 10. 한 줄 요약

```text
BF1은 feature metadata에 bridge를 만들고,
transition false-break와 chart wait awareness에 같이 연결하는 첫 구현 단계다.
```
