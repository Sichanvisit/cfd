# Response R2-5+ Redesign

## 목적

이 문서는 기존 `R2-5. S/R raw 추가` 이후 단계를, 현재 CFD 시스템의 owner 기준에 맞게 다시 설계한 로드맵이다.

핵심 이유는 간단하다.

- `Position`은 이제 박스/볼린저/MA/추세선의 **위치와 거리 지도**를 담당한다.
- `Response`는 짧은 분봉에서 실제로 나온 **반응 사건**을 담당한다.
- `State`는 상위 시간대의 큰 방향과 신뢰도, 인내심을 담당한다.

즉 예전처럼 `R2-5 = raw 4개 추가`로 가는 것보다,
이제는 `Response 안에 어떤 서브시스템을 둘 것인가`를 다시 정의하는 편이 더 맞다.

---

## 왜 R2-5가 달라졌는가

기존 생각:

- `sr_support_hold`
- `sr_support_break`
- `sr_resistance_reject`
- `sr_resistance_break`

정도의 raw 4개만 추가하면 된다고 봤다.

하지만 지금은 구조가 달라졌다.

1. `Position`에 박스/볼린저 위치와 크기, MA 거리 지도, 추세선 거리 지도가 이미 들어갔다.
2. 큰지도 weight는 `Position`이 아니라 `State` 후보로 분리됐다.
3. `Response`는 짧은 분봉의 실제 반응을 모아 6축으로 보내는 owner가 되어야 한다.

그래서 이제 `S/R raw`는 단순 보조 raw가 아니라,
`Response` 안의 하나의 정식 반응 서브시스템으로 보는 게 맞다.

---

## 현재 owner 기준

### Position

- 박스/볼린저 위치
- 박스/볼린저 크기와 압축/확장 메타데이터
- MA 거리 지도
- 추세선 거리 지도

즉 `지금 어디에 있나`, `이 지도가 얼마나 좁거나 넓나`를 말한다.

### Response

- 1M / 5M 중심의 짧은 분봉 반응
- S/R에서의 실제 반응
- 추세선에서의 실제 반응
- 캔들 descriptor / pattern / motif
- 구조 motif

즉 `그 자리에서 무슨 사건이 벌어졌나`를 말한다.

### State

- D1 / H4 / H1 / M30 / M15 큰 방향
- MTF MA / trendline weight의 해석
- trend / range / shock
- volatility / liquidity / noise / conflict

즉 `그 반응을 얼마나 믿고 얼마나 기다릴 수 있나`를 보정한다.

---

## 새 Response 구조

기존:

```text
BB / Box / Candle / Pattern raw
-> Response 6축
```

재설계:

```text
OHLC / level / swing / micro-TF
-> descriptor
-> pattern
-> motif
-> reaction subsystem
-> context gate
-> Response 6축
```

핵심 차이:

- `descriptor/pattern/motif`는 이미 만든 중간 semantic 층이다.
- 여기에 `S/R`, `trendline`, `micro-TF`를 그냥 raw로 던지지 않고,
  각 반응 서브시스템에서 먼저 정리한 뒤 `context gate`로 보낸다.

---

## R2-5 이후 새 단계

### R2-5. S/R Response Subsystem

#### 목표

`S/R` 자체를 새로 정의하는 게 아니라,
이미 잡혀 있는 지지/저항선에서 실제로 어떤 반응이 나왔는지 `Response` 안에서 정리한다.

#### 기본 원칙

- 선 자체의 위치/거리 = `Position`
- 선에서의 반응 = `Response`
- 선의 상위 시간대 중요도/신뢰도 = `State`

#### 최소 raw 후보

- `sr_support_touch`
- `sr_support_hold`
- `sr_support_reclaim`
- `sr_support_break`
- `sr_resistance_touch`
- `sr_resistance_reject`
- `sr_resistance_reclaim`
- `sr_resistance_break`

#### 추가 메타 후보

- `sr_active_support_tf`
- `sr_active_resistance_tf`
- `sr_support_proximity`
- `sr_resistance_proximity`
- `sr_touch_count`
- `sr_level_rank`

#### 이 단계의 출력 목적

최종적으로는 아래 4개 의미 묶음으로 정리하는 것이 목표다.

- `support_hold_strength`
- `support_break_strength`
- `resistance_reject_strength`
- `resistance_break_strength`

이 값들은 나중에 `Response 6축`의 재료가 된다.

#### 완료 기준

- 지지선에서 받은 반응과, 지지선이 깨진 반응이 서로 다른 raw로 분리된다.
- 저항선에서 밀리는 반응과, 저항선을 돌파하는 반응이 서로 다른 raw로 분리된다.
- `Position`은 여전히 선의 위치만 말하고, `Response`만 사건을 말한다.

---

### R2-6. Trendline Response Subsystem

#### 목표

이미 `Position`에 들어간 `x_tl_*`, `tl_proximity_*`와 별도로,
추세선에서 어떤 사건이 벌어졌는지 `Response`에 만든다.

#### 기본 원칙

- 추세선 거리 지도 = `Position`
- 추세선 반응 = `Response`

#### raw 후보

- `trend_support_touch_m1`
- `trend_support_hold_m1`
- `trend_support_break_m1`
- `trend_resistance_touch_m1`
- `trend_resistance_reject_m1`
- `trend_resistance_break_m1`

- `trend_support_touch_m15`
- `trend_support_hold_m15`
- `trend_support_break_m15`
- `trend_resistance_touch_m15`
- `trend_resistance_reject_m15`
- `trend_resistance_break_m15`

- `trend_support_touch_h1`
- `trend_support_hold_h1`
- `trend_support_break_h1`
- `trend_resistance_touch_h1`
- `trend_resistance_reject_h1`
- `trend_resistance_break_h1`

- `trend_support_touch_h4`
- `trend_support_hold_h4`
- `trend_support_break_h4`
- `trend_resistance_touch_h4`
- `trend_resistance_reject_h4`
- `trend_resistance_break_h4`

#### 출력 묶음

- `trend_support_hold_strength`
- `trend_support_break_strength`
- `trend_resistance_reject_strength`
- `trend_resistance_break_strength`

#### 완료 기준

- 추세선의 위/아래 위치는 `Position` 메타데이터로 남는다.
- 추세선에서 튕김/붕괴/거절/돌파는 `Response` raw로 분리된다.

---

### R2-7. Micro-TF Response Layer

#### 목표

짧은 분봉의 실제 진입 타이밍 반응을 `Response` owner로 묶는다.

#### 시간대 기준

- `1M`
- `5M`

#### 구성 요소

- candle descriptor
- candle pattern
- candle motif
- micro swing 반응
- micro level 반응

#### 여기서 보는 것

- 1분봉 하단 reject가 떴는가
- 5분봉에서 장악형이 이어지는가
- 1분봉 3연속 강세/약세가 나왔는가
- micro reclaim / micro lose가 나왔는가

#### 출력 후보

- `micro_bull_reject_strength`
- `micro_bear_reject_strength`
- `micro_bull_break_strength`
- `micro_bear_break_strength`
- `micro_indecision_strength`

#### 완료 기준

- 짧은 분봉 패턴은 이제 `Position`이나 `State`로 새지 않는다.
- 실제 타이밍 반응은 `Response` 안에서만 정리된다.

---

### R2-8. Context Gate 재설계

#### 목표

같은 motif라도, 지금 위치에서 의미가 다르면 그 차이를 먼저 걸러낸다.

예:

- lower zone + support 근처의 `hammer_like`
- middle zone 한가운데의 `hammer_like`

두 개는 같은 값으로 쓰면 안 된다.

#### gate 입력

- `Position`
  - `x_box`
  - `x_bb20`
  - `x_bb44`
  - `compression_score`
  - `expansion_score`
  - `x_tl_*`
  - `tl_proximity_*`
  - `mtf_ma_big_map_v1`
- `State`
  - big-map bias
  - trend/range/shock
  - liquidity/noise/conflict

#### gate 역할

- 살아야 하는 반응은 키움
- 자리와 안 맞는 반응은 약화
- 애매함은 `WAIT` 쪽으로 넘김

#### 완료 기준

- 패턴 점수만 높다고 바로 축 점수가 높아지지 않는다.
- 위치/환경을 거친 뒤에만 축 기여가 생긴다.

---

### R2-9. Response 6축 재결선

#### 목표

이제는 raw를 바로 6축에 넣지 않고,
서브시스템 출력을 받아서 6축을 만든다.

#### 새 6축 재료

- `lower_hold_up`
  - `support_hold_strength`
  - `trend_support_hold_strength`
  - `micro_bull_reject_strength`
  - `structure support_hold_confirm`

- `lower_break_down`
  - `support_break_strength`
  - `trend_support_break_strength`
  - `micro_bear_break_strength`

- `mid_reclaim_up`
  - micro reclaim
  - 2봉/3봉 bullish reversal
  - lower->mid 회복 반응

- `mid_lose_down`
  - micro lose
  - 2봉/3봉 bearish reversal
  - mid 상실 반응

- `upper_reject_down`
  - `resistance_reject_strength`
  - `trend_resistance_reject_strength`
  - `micro_bear_reject_strength`
  - `structure resistance_reject_confirm`

- `upper_break_up`
  - `resistance_break_strength`
  - `trend_resistance_break_strength`
  - `micro_bull_break_strength`

#### 설계 원칙

- 같은 의미는 여러 번 세지 않는다.
- favor 점수와 conflict 점수를 따로 만든다.
- 최종 축은 `favor - penalty` 구조로 만든다.
- saturation을 피하기 위해 soft clip을 우선한다.

#### 완료 기준

- raw 수가 늘어나도 6축 해석은 더 안정적이어야 한다.
- `support hold`와 `support break`가 동시에 높을 때는 ambiguity가 따로 드러난다.

---

### R2-10. State 이관 준비

#### 목표

큰지도 weight와 상위 시간대 bias는 `Position`이 아니라 `State` owner로 보낸다.

#### 현재 후보 메타데이터

- `mtf_ma_weight_profile_v1`
- `mtf_trendline_weight_profile_v1`
- `mtf_context_weight_profile_v1`

#### State에서 맡길 것

- D1/H4/H1/M30/M15 방향 가중치
- 같은 방향일 때 신뢰도 증폭
- 반대 방향일 때 반응 감쇠
- 인내심 조절

#### 완료 기준

- 상위 시간대 weight는 더 이상 `Position`의 직접 해석을 건드리지 않는다.
- 대신 `Response`를 얼마나 믿을지 `State`에서만 조절한다.

---

## 재설계 후 전체 그림

```text
Position
= 지도

Response
= 사건

State
= 해석과 신뢰도 보정
```

조금 더 풀어 쓰면:

```text
Position
-> 지금 어디 있고, 얼마나 좁거나 넓은가

Response
-> 지금 그 자리에서 무엇이 벌어졌는가

State
-> 그 사건을 얼마나 믿고 얼마나 기다릴 수 있는가
```

---

## 지금 바로 할 다음 순서

### 1순위

`R2-5 S/R Response Subsystem`

이유:

- 지금 비어 있는 핵심 raw다.
- 네가 중요하게 보는 지지/저항 반응이 여기서 처음 직접 owner를 갖게 된다.

### 2순위

`R2-8 Context Gate 재설계`

이유:

- 지금 descriptor/pattern/motif를 이미 붙였기 때문에,
  다음 병목은 `자리에서 살릴지 죽일지`의 문제다.

### 3순위

`R2-9 Response 6축 재결선`

이유:

- 이제 BB/Box 중심 축을 서브시스템 출력 기반 축으로 천천히 바꿔야 한다.

### 4순위

`R2-6 Trendline Response Subsystem`

이유:

- 추세선 거리 지도는 이미 Position에 붙어 있다.
- 다음은 사건 owner를 Response로 넘기면 된다.

### 5순위

`R2-10 State 이관 준비`

이유:

- 큰지도 weight는 이미 계산되지만 해석 owner를 아직 정식 이관하지 않았다.

---

## 한 줄 결론

지금부터의 `R2-5 이후`는
`raw 4개 추가`가 아니라,

`S/R / trendline / micro-TF 반응 서브시스템을 만들고, 그 출력을 context gate를 거쳐 Response 6축으로 재결선하는 과정`

으로 보는 것이 현재 시스템과 가장 잘 맞다.
