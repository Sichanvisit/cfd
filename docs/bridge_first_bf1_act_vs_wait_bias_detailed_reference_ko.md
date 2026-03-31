# BF1 Act-vs-Wait Bias Detailed Reference

작성일: 2026-03-31 (KST)

## 1. 목적

BF1은 `WAIT / observe / directional act`를 더 잘 구분하는 첫 bridge를 만든다.

이 bridge는 아래 두 곳에 동시에 쓰여야 한다.

- `transition_forecast`
- `chart / product acceptance wait awareness`

즉 BF1은 forecast 내부 보정만이 아니라,
차트에서 `왜 이 자리가 W로 눌려야 하는지`, `왜 awareness 1개는 남겨야 하는지`
를 같은 언어로 설명하기 위한 공통 summary다.

## 2. 왜 BF1이 먼저인가

SF6 기준:

- `p_false_break separation_gap = -0.0147`
- `high_low_rate_gap = -0.0039`

즉 false-break / wait discrimination이 가장 평평하다.

그리고 이 문제는 forecast 내부 branch의 정확도 문제이면서 동시에
product acceptance에서

- 너무 무표정한 WAIT
- 너무 과장된 continuation
- awareness가 필요한데 체크가 안 남는 구간

으로도 이어진다.

그래서 BF1은 `forecast refinement`와 `product acceptance`를 동시에 건드리는 첫 bridge다.

## 3. 입력 레이어

BF1은 새 raw를 추가하지 않는다.

아래 레이어를 bridge 입력으로 묶는다.

- `State`
- `Evidence`
- `Belief`
- `Barrier`

구체적으로는 아래 성격의 값들을 본다.

- `State`
  - conflict / neutrality / friction / event risk / quality
- `Evidence`
  - dominant evidence
  - asymmetry
- `Belief`
  - dominant belief
  - persistence
  - flip readiness
  - instability
- `Barrier`
  - middle chop
  - conflict barrier

## 4. 출력 표면

BF1의 canonical output은 아래 세 개다.

- `act_vs_wait_bias`
- `false_break_risk`
- `awareness_keep_allowed`

의미는 이렇다.

### 4-1. act_vs_wait_bias

지금 장면이 directional act 쪽으로 더 기울어 있는지,
아니면 wait 쪽으로 더 눌려야 하는지를 0~1 요약값으로 표현한다.

- 높을수록 act 쪽
- 낮을수록 wait 쪽

### 4-2. false_break_risk

지금 directional act로 과장하면 false-break로 흘러갈 위험이 큰지를 표현한다.

- 높을수록 false-break 위험 큼

### 4-3. awareness_keep_allowed

강한 act는 아니어도,
chart/product acceptance에서 `1개 awareness`는 남겨도 되는지 여부를 표현한다.

즉:

- `강한 entry-ready`는 아님
- 하지만 `완전 무표정`도 아니어야 하는 장면

을 살리기 위한 bridge다.

## 5. 구현 원칙

### 5-1. owner를 바꾸지 않는다

BF1은 scene owner를 대체하지 않는다.

- `scene`은 여전히 scene owner
- BF1은 modifier

즉 `이 자리가 어떤 종류의 자리인가`는 scene이 결정하고,
`지금 얼마나 act / wait / awareness로 보여야 하는가`는 BF1이 돕는다.

### 5-2. raw payload를 직접 노출하지 않는다

BF1은 raw detector나 raw forecast payload를 그대로 chart에 주지 않는다.
항상 요약된 bridge 값만 전달한다.

### 5-3. additive wiring으로 시작한다

첫 구현은 기존 `p_false_break`를 뒤엎지 않고,
작게 blend하는 수준으로 시작한다.

product acceptance 쪽도
대규모 suppress/unsuppress가 아니라
`awareness preserve` 위주로 제한적으로 시작한다.

## 6. 연결 위치

### 6-1. feature build

- `forecast_features_v1.metadata`

여기에 `bridge_first_v1.act_vs_wait_bias_v1` 형태로 summary를 심는다.

### 6-2. forecast

- `transition_forecast_v1.metadata`

여기서 BF1 summary를 읽고,
`p_false_break` 관련 pressure/metadata/reason에 약하게 반영한다.

### 6-3. product acceptance

- `consumer_check_state_v1`

여기서 BF1 summary를 읽고,
soft wait / awareness 구간에서 `완전 무표정`이 되지 않게 보조한다.

## 7. BF1에서 기대하는 변화

### forecast 쪽

- `p_false_break`가 완전히 flat한 상태에서 조금 더 separation을 가지게 된다
- false-break 관련 이유 설명이 richer 해진다

### chart / product acceptance 쪽

- act는 아니지만 awareness 1개는 남겨야 하는 장면을 더 설명 가능하게 다룬다
- NAS/XAU/BTC 조정에서 `왜 W로 눌렀는지 / 왜 1개는 남겼는지`를 같은 bridge로 설명할 수 있다

## 8. BF1에서 아직 하지 않을 것

- raw field 확장
- order_book collector 재작업
- threshold-only tuning
- management hold / fast-cut bridge까지 한 번에 같이 넣기

## 9. 완료 기준

BF1은 아래를 만족하면 1차 close-out 가능하다.

1. `forecast_features_v1.metadata`에 BF1 summary가 생긴다.
2. `transition_forecast_v1.metadata`가 BF1 summary와 이유를 남긴다.
3. `consumer_check_state_v1`이 BF1 summary를 awareness preserve에 제한적으로 사용한다.
4. 테스트로 BF1 contract와 최소 회귀가 잠긴다.

## 10. 한 줄 요약

```text
BF1은 false-break / wait discrimination을 개선하기 위해,
state/evidence/belief/barrier를 act_vs_wait_bias / false_break_risk / awareness_keep_allowed 로 요약하는 첫 공통 bridge다.
```
