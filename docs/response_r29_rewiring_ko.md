# Response R2-9 재결선 상세 설명

## 목적

이 문서는 `R2-9. Response 6축 재결선`이 정확히 무엇을 바꾸는 단계인지,
왜 기존 6축을 버리지 않고 유지하는지,
그리고 각 축이 어떤 재료를 받아 최종 반응 축이 되는지를 자세히 설명하는 문서다.

핵심은 간단하다.

- 6축 자체를 새로 만드는 것이 아니다.
- 6축의 이름도 유지한다.
- 대신 6축에 들어가는 재료를 더 의미 있게 바꾼다.

즉 `R2-9`는

```text
기존 6축을 폐기하는 단계
```

가 아니라

```text
기존 6축을 더 체계적인 재료로 다시 배선하는 단계
```

다.

---

## 한 줄 요약

예전 구조:

```text
BB / Box / candle / pattern raw
-> 바로 Response 6축
```

새 구조:

```text
raw
-> descriptor
-> pattern
-> motif
-> subsystem
-> context gate
-> Response 6축
```

즉 6축은 그대로 두고,
그 6축을 만드는 입력층을 훨씬 더 정리된 의미 단위로 바꾸는 것이다.

---

## 왜 이 단계가 필요한가

기존 `transition_vector.py` 구조는 다음 장점이 있었다.

- 빠르게 축을 만들 수 있었다.
- BB/Box 기반 위치 반응을 곧바로 6축으로 변환할 수 있었다.

하지만 점점 문제가 커졌다.

### 기존 구조의 대표 문제

1. 같은 의미가 여러 번 들어간다.
- `bb20_upper_reject`
- `box_upper_reject`
- `candle_upper_reject`
- `pattern_head_shoulders`

이들이 전부 사실상 같은 방향 의미를 밀 수 있다.

2. raw의 추상화 수준이 다르다.
- 어떤 것은 단순 터치 반응이다.
- 어떤 것은 패턴이다.
- 어떤 것은 구조 확인이다.
- 어떤 것은 짧은 분봉의 micro 반응이다.

그런데 이걸 같은 층에서 바로 6축으로 넣으면,
각 재료의 역할이 섞인다.

3. context가 늦게 반영된다.
- 같은 `hammer_like`라도
  - lower zone + support 근처의 hammer
  - middle zone 한가운데 hammer
는 의미가 전혀 다르다.

그런데 raw를 바로 6축에 넣으면 이런 차이를 충분히 반영하기 어렵다.

4. 새 subsystem을 붙일 자리가 불명확하다.
- `S/R subsystem`
- `trendline subsystem`
- `micro-TF subsystem`

이런 것들이 생겼는데,
옛 구조는 `BB/Box 중심 merge`라서 새 subsystem을 체계적으로 연결하기 어렵다.

즉 `R2-9`는
지금까지 만든 subsystem들을 진짜 최종 6축에 연결하는 단계다.

---

## 6축은 왜 유지하는가

6축은 여전히 유효하다.

현재 Response가 최종적으로 말해야 하는 것은 결국 아래 6가지뿐이기 때문이다.

- 하단에서 받치고 올라가려는가
- 하단이 깨지고 내려가려는가
- 중심을 회복하고 위로 가려는가
- 중심을 잃고 아래로 가려는가
- 상단에서 거절되고 내려가려는가
- 상단을 돌파하고 위로 가려는가

즉 6축은 매우 좋은 최종 반응 인터페이스다.

문제는 축 자체가 아니라,
거기까지 올라가는 재료와 경로가 조악했던 것이다.

따라서 `R2-9`의 방향은:

- 6축 유지
- 재료층 교체
- gate 이후에만 최종 축 기여 허용

이다.

---

## 새 재결선의 큰 그림

새 구조는 다음처럼 보면 된다.

```text
1. candle motif
2. structure motif
3. S/R subsystem strength
4. trendline subsystem strength
5. micro-TF subsystem strength
6. context gate
7. pre-axis candidates
8. Response 6축
```

여기서 중요한 포인트는:

- raw는 더 이상 직접 6축으로 가지 않는다.
- 먼저 subsystem 안에서 의미를 정리한다.
- 그다음 context gate에서 위치/환경과 맞는지 확인한다.
- 마지막에만 6축으로 올라간다.

즉 `R2-9`는 사실상

```text
subsystem -> context gate -> 6축
```

이라는 최종 wiring 단계다.

---

## 각 층이 하는 일

## 1. Candle motif

캔들 pattern 이름을 직접 6축에 넣지 않고,
조금 더 큰 의미 묶음으로 압축한 층이다.

예:

- `bull_reject`
- `bear_reject`
- `bull_reversal_2bar`
- `bear_reversal_2bar`
- `bull_reversal_3bar`
- `bear_reversal_3bar`
- `bull_break_body`
- `bear_break_body`
- `indecision`
- `climax`

이 층은
“캔들 쪽에서 어떤 방향의 힘이 보이는가”를 말한다.

---

## 2. Structure motif

더블탑, 더블바텀, H&S 같은 구조 패턴을 다시 정리한 층이다.

예:

- `reversal_base_up`
- `reversal_top_down`
- `support_hold_confirm`
- `resistance_reject_confirm`

이 층은
“구조적으로 바닥 확인인가, 천장 확인인가”를 말한다.

---

## 3. S/R subsystem

S/R 그 자체가 아니라,
이미 잡혀 있는 지지/저항선에서 실제 어떤 사건이 났는지를 정리한 층이다.

최종 strength 예:

- `support_hold_strength`
- `support_break_strength`
- `resistance_reject_strength`
- `resistance_break_strength`

이 층은
“레벨 반응이 실제로 있었는가”를 말한다.

---

## 4. Trendline subsystem

추세선 자체의 위치는 Position이 말하고,
추세선에서 튕김/붕괴/거절/돌파가 있었는지만 Response가 받는다.

최종 strength 예:

- `trend_support_hold_strength`
- `trend_support_break_strength`
- `trend_resistance_reject_strength`
- `trend_resistance_break_strength`

이 층은
“기울어진 구조선에서 실제 반응이 있었는가”를 말한다.

---

## 5. Micro-TF subsystem

`1M / 5M`의 실제 타이밍 반응을 정리한 층이다.

예:

- `micro_bull_reject_strength`
- `micro_bear_reject_strength`
- `micro_bull_break_strength`
- `micro_bear_break_strength`
- `micro_indecision_strength`
- `micro_reclaim_up_strength`
- `micro_lose_down_strength`

이 층은
“지금 짧은 분봉에서 당장 어떤 방향 촉감이 살아 있나”를 말한다.

---

## 6. Context gate

같은 motif/strength라도 지금 위치에서 의미가 다르면,
그 차이를 먼저 반영하는 층이다.

예:

- lower zone + support 근처의 `bull_reject`
- middle zone의 `bull_reject`

같은 값으로 쓰면 안 된다.

따라서 gate는:

- lower/upper/middle zone
- support/resistance anchor
- big-map bias
- ambiguity
- compression/expansion

같은 맥락을 보고,
살아야 할 반응은 키우고
자리와 안 맞는 반응은 줄인다.

즉 `R2-8`이 준비한 것을
`R2-9`가 최종 축 연결에 사용하게 되는 것이다.

---

## 7. Pre-axis candidates

이제 각 subsystem 출력을 바로 6축으로 넣지 않고,
한 번 더 `축 후보값`으로 모은다.

예:

- `lower_hold_candidate`
- `lower_break_candidate`
- `mid_reclaim_candidate`
- `mid_lose_candidate`
- `upper_reject_candidate`
- `upper_break_candidate`

이건 사실상
“최종 6축 직전 단계”다.

---

## 각 6축 상세 설명

## 1. `lower_hold_up`

### 뜻

하단에서 지지를 받고 위로 올라가려는 힘

### 이 축이 담당하는 상황

- 지지선에서 받침
- 하단 구조에서 반등
- 추세선 지지에서 튕김
- 짧은 분봉에서 하단 reject
- 구조적 바닥 확인

즉 “하단이 깨진 게 아니라 버티고 올라간다”를 의미한다.

### 새 재료

- `support_hold_strength`
- `trend_support_hold_strength`
- `micro_bull_reject_strength`
- `support_hold_confirm`
- `reversal_base_up`
- `bull_reject`
- `bull_reversal_2bar`
- `bull_reversal_3bar`

### 왜 이렇게 묶나

이 재료들은 다 본질적으로 같은 방향이다.

- 레벨 관점: 하단 지지
- 구조 관점: 바닥 형성
- micro 관점: 아래서 받아 올림
- candle 관점: bullish reject / reversal

즉 `lower_hold_up`은
단순히 `볼밴 하단에서 튕김`이 아니라,
하단 반등에 관한 여러 독립 evidence를 하나로 묶는 축이 된다.

---

## 2. `lower_break_down`

### 뜻

하단 지지가 깨지고 아래로 내려가려는 힘

### 이 축이 담당하는 상황

- 지지선 붕괴
- 추세선 지지 붕괴
- 하단 break body
- micro 하락 붕괴

즉 “하단에 있다는 사실”보다
“하단에서 버티지 못하고 깨진다”는 사건을 말한다.

### 새 재료

- `support_break_strength`
- `trend_support_break_strength`
- `micro_bear_break_strength`
- `bear_break_body`
- `micro_lose_down_strength`
- 일부 bearish reversal

### 왜 이렇게 묶나

예전에는 하단이라는 이유만으로 buy 쪽으로 빨려가는 경우가 있었는데,
이제는 `하단 붕괴`를 별도 축으로 확실히 분리할 수 있다.

즉:

- 하단 + 반등 = `lower_hold_up`
- 하단 + 붕괴 = `lower_break_down`

이 둘을 더 명확히 분리하려는 목적이다.

---

## 3. `mid_reclaim_up`

### 뜻

중심을 다시 회복하고 위로 올라가려는 힘

### 이 축이 담당하는 상황

- micro reclaim
- 2봉/3봉 bullish reversal
- lower에서 시작했지만 결국 중심선을 재회복
- 애매한 자리에서 bullish side가 중심을 다시 장악

### 새 재료

- `micro_reclaim_up_strength`
- `bull_reversal_2bar`
- `bull_reversal_3bar`
- `bull_reject`
- 일부 `bull_break_body`
- 일부 `reversal_base_up`

### 왜 중요한가

이 축은 바닥 반등과 다르다.

- `lower_hold_up` = 바닥 지지
- `mid_reclaim_up` = 중심 회복

실전에서는 이 차이가 매우 중요하다.
특히 “이미 조금 올라왔지만 더 볼 수 있는가?”를 판단할 때
`mid_reclaim_up`이 핵심이 된다.

---

## 4. `mid_lose_down`

### 뜻

중심을 잃고 아래로 밀리는 힘

### 이 축이 담당하는 상황

- micro lose
- bearish engulfing / evening star
- 중심 회복 실패
- middle에서 아래쪽으로 재이탈

### 새 재료

- `micro_lose_down_strength`
- `bear_reversal_2bar`
- `bear_reversal_3bar`
- `bear_reject`
- 일부 `bear_break_body`
- 일부 `reversal_top_down`

### 왜 중요한가

이 축은 상단 reject와 다르다.

- `upper_reject_down` = 상단 저항 거절
- `mid_lose_down` = 중심 상실

즉 꼭 상단까지 안 가더라도
중심을 못 지키고 다시 아래로 미끄러지는 장면을 잡기 위한 축이다.

---

## 5. `upper_reject_down`

### 뜻

상단에서 저항을 받고 아래로 내려가려는 힘

### 이 축이 담당하는 상황

- S/R 저항 거절
- trendline 저항 거절
- micro 상단 reject
- structure 상단 천장 확인
- candle bearish reject

### 새 재료

- `resistance_reject_strength`
- `trend_resistance_reject_strength`
- `micro_bear_reject_strength`
- `resistance_reject_confirm`
- `reversal_top_down`
- `bear_reject`
- `bear_reversal_2bar`
- `bear_reversal_3bar`

### 왜 중요한가

이 축이 강화되면
네가 자주 지적했던
“왜 저기 상단에서 sell을 못 잡냐”
문제를 줄일 수 있다.

왜냐하면 이제 상단 sell은
볼린저/박스 하나가 아니라

- 저항
- 추세선
- micro reject
- 구조 천장

이 합으로 올라오기 때문이다.

---

## 6. `upper_break_up`

### 뜻

상단 저항을 뚫고 위로 확장하려는 힘

### 이 축이 담당하는 상황

- 저항 돌파
- 추세선 돌파
- micro bull break
- breakout body

### 새 재료

- `resistance_break_strength`
- `trend_resistance_break_strength`
- `micro_bull_break_strength`
- `bull_break_body`
- 일부 bullish reversal continuation

### 왜 중요한가

상단이라고 무조건 sell이 아니기 때문이다.

즉:

- 상단에서 막힘 = `upper_reject_down`
- 상단을 뚫음 = `upper_break_up`

이 둘을 더 명확히 갈라서,
상단 sell과 상단 breakout buy를 혼동하지 않게 하려는 목적이다.

---

## R2-9 이후의 최종 그림

`R2-9`가 끝나면 최종 Response 구조는 이렇게 읽으면 된다.

```text
candle / structure / S/R / trendline / micro
-> 각각 subsystem strength
-> context gate
-> pre-axis candidate
-> Response 6축
```

즉 최종 6축은 더 이상 raw의 단순합이 아니라,
정리된 subsystem output의 의미 합성 결과가 된다.

---

## Evidence와의 관계

`R2-9`가 끝나도 Response는 여전히 최종 진입 신호가 아니다.

Response는 단지

- 하단 반등 쪽이 강한지
- 하단 붕괴 쪽이 강한지
- 상단 거절 쪽이 강한지
- 상단 돌파 쪽이 강한지

를 더 정교하게 말해주는 축일 뿐이다.

그 다음은 여전히:

- `Position`이 어디냐
- `State`가 어떤 장이냐
- `Evidence`가 그걸 얼마나 믿느냐

가 결정한다.

즉 `R2-9`는 진입 엔진을 만드는 단계가 아니라,
진입 엔진이 읽을 수 있는 더 좋은 반응 벡터를 만드는 단계다.

---

## 구현 관점에서 무엇이 바뀌는가

실제 코드 기준으로는 [transition_vector.py](c:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/response/transition_vector.py)의 역할이 바뀐다.

예전:

- `bb20_*`
- `box_*`
- `candle_*`
- `pattern_*`

를 바로 `lower_hold_up`, `upper_reject_down` 같은 축으로 merge

이제:

- `response_context_gate_v1.pre_axis_candidates`
- `sr_subsystem_v1.strengths`
- `trendline_subsystem_v1.strengths`
- `micro_tf_subsystem_v1.strengths`
- gated motif

를 받아 6축을 만든다

즉 `transition_vector.py`는 더 이상
raw merger가 아니라
subsystem merger에 가까워진다.

---

## Acceptance 기준

`R2-9`가 잘 끝났다고 보려면 아래가 만족돼야 한다.

1. 같은 하단 자리에서도
- 지지 반등이면 `lower_hold_up`
- 붕괴면 `lower_break_down`
이 확실히 갈린다.

2. 같은 상단 자리에서도
- 거절이면 `upper_reject_down`
- 돌파면 `upper_break_up`
이 확실히 갈린다.

3. middle에서는
- `mid_reclaim_up`
- `mid_lose_down`
이 따로 의미 있게 산다.

4. candle 하나가 곧바로 축을 결정하지 않는다.
- subsystem
- context gate
- pre-axis candidate
를 거쳐야만 최종 축으로 올라간다.

5. `S/R / trendline / micro-TF`가 실제로 축에 반영된다.
- 존재만 하는 메타데이터가 아니라
- 최종 Response 6축의 재료로 쓰여야 한다.

---

## 한 문장 정리

`R2-9는 6축을 없애는 단계가 아니라, candle·structure·S/R·trendline·micro subsystem을 context gate 뒤에서 다시 묶어 훨씬 더 의미 있는 6축으로 재배선하는 단계다.`
