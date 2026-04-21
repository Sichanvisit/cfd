# BC2 State25 Weight-Only Translator 상세 계획

## 목표

`BC2`의 목적은 `state25_context_bridge.py` 위에 **첫 실제 translator로 weight-only 번역기**를 올리는 것이다.

이번 단계에서는:
- `AGAINST_HTF`
- `BREAKOUT_HELD`
- `RECLAIMED`

같은 context를 **핵심 weight 2개씩만** 실제 override 후보로 번역한다.

반대로 이번 단계에서 의도적으로 하지 않는 것:
- threshold 조정
- size 조정
- late chase의 적극적 weight 반영


## 왜 weight-only부터 시작하는가

weight는:
- 방향 강제가 아니고
- 해석 비중 재정렬에 가깝고
- threshold / size보다 행동 변화가 더 완만하다

그래서 첫 bounded translator로 가장 안전하다.


## 이번 단계 범위

이번 `BC2`에서 구현할 것:

- `backend/services/state25_context_bridge.py`
- weight pair translator
- requested / effective / suppressed 분리
- `context_bias_side`
- `context_bias_side_confidence`
- `context_bias_side_source_keys`
- cap / overlap guard / stale suppression의 weight 반영
- weight 관련 trace 보강

이번 단계에서 하지 않을 것:

- threshold translator
- size translator
- runtime export 합류
- detector/propose 연결


## 번역 원칙

### 1. context당 2개 weight까지만

한 context 이벤트당 핵심 weight 2개까지만 움직인다.

이유:
- hindsight에서 효과 분리 가능
- 과보정 방지
- rollback 단순화

### 2. interpreted 중심

weight translator는 raw 점수보다 interpreted state를 중심으로 읽는다.

- `AGAINST_HTF`
- `BREAKOUT_HELD`
- `RECLAIMED`

raw는 activation / severity 보정에만 쓴다.

### 3. late chase는 v1에서 weight 우선 아님

`LATE_CHASE_RISK`는 본질적으로 timing / risk 문제에 가깝다.

그래서 v1에서는:
- weight보다는 threshold / size 쪽 손잡이에 우선 연결한다
- BC2에서는 `late chase`가 켜져 있어도 weight에서는 “의도적으로 보류” trace만 남긴다


## 대표 매핑

### AGAINST_HTF

- `reversal_risk_weight` 하향
- `directional_bias_weight` 상향

의미:
- 역추세 해석 과신을 줄이고
- 현재 큰 방향 우세 해석을 조금 올린다

### BREAKOUT_HELD

- `range_reversal_weight` 하향
- `directional_bias_weight` 상향

의미:
- “돌파 유지 장면”에서 박스 반전 해석 과신을 줄인다

### RECLAIMED

- `reversal_risk_weight` 하향
- `participation_weight` 상향

의미:
- 재회복 이후 지속 가능성을 조금 더 반영한다


## output 구조

### requested

translator가 이론상 원한 조정값

### effective

freshness / cap / overlap guard / clamp가 반영된 실제 유효 조정값

### suppressed

조정을 요청했거나 요청할 수 있었지만,
아래 이유로 실제 반영이 0이 되거나 보류된 경우

- stale
- low confidence
- overlap guard
- late chase policy defer


## context bias side

BC2는 weight translator 결과로 아래 필드를 채운다.

- `context_bias_side`
- `context_bias_side_confidence`
- `context_bias_side_source_keys`

이 필드는 hard direction이 아니라
**이번 weight translator가 어느 쪽 해석 우세를 더 지지했는지**를 보여주는 보조 신호다.


## cap / clamp 원칙

BC2의 effective weight delta는 작게 시작한다.

대표 원칙:
- weight delta 절대값 최대 `0.20`
- 최종 값은 state25 weight 허용 범위 안으로 clamp

즉 BC2는 “강하게 바꾸는 번역기”가 아니라,
**작고 되돌리기 쉬운 bias 조정기**다.


## suppression 원칙

### stale HTF

`AGAINST_HTF`가 있어도 HTF activation이 0이면
weight effective는 만들지 않고 suppression만 남긴다.

### low confidence / non-consolidation previous_box

`BREAKOUT_HELD`, `RECLAIMED`가 있어도 previous_box activation이 0이면
suppression만 남긴다.

### overlap guard

forecast / belief / barrier bridge와 겹치면
requested는 남기되 effective는 0으로 눌러서
double counting을 피한다.

### late chase defer

late chase는 BC2에서 weight translation source로 쓰지 않고
`DEFER_TO_THRESHOLD_SIZE_V1` suppression trace만 남긴다.


## trace 원칙

BC2 trace는 최소 아래를 보여줘야 한다.

1. 어떤 context가 weight pair로 번역됐는지
2. 어떤 bias side가 추정됐는지
3. 어떤 조정이 requested였는지
4. 어떤 이유로 effective가 약화되거나 0이 됐는지


## 완료 기준

- weight-only translator가 실제 state25 weight key를 대상으로 requested/effective를 만든다
- `late chase`는 의도적으로 weight에서 빠진다
- overlap guard가 있으면 effective가 구조적으로 suppress된다
- trace에서 requested/effective/suppressed가 모두 보인다


## 다음 단계 연결

BC2 다음은 자연스럽게:

1. `BC3 Runtime Trace Export`
2. 그 뒤 `BC4 Weight-Only Log-Only Review Lane`

즉 BC2는 bridge가 처음으로 **실제 조정값을 계산하기 시작하는 단계**다.
