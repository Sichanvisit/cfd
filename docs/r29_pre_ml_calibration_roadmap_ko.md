# R2-9 이후 Pre-ML 보정 로드맵

## 목적

이 문서는 `R2-9 Response 6축 재결선` 이후,
바로 `ML`로 넘어가기 전에 반드시 거쳐야 하는
`기본형 보정(calibration)` 단계를 정리한 운영 문서다.

핵심 목적은 아래 3가지다.

1. `기본 semantic 구조`를 더 흔들지 않고 고정한다.
2. `기본 승률`과 `체감 품질`이 높은 상태를 먼저 만든다.
3. 그 다음에야 `ML`이 수치만 미세 보정하도록 준비한다.

즉 이 단계는:

```text
구조 재설계 단계
```

가 아니라

```text
구조는 고정하고 숫자만 맞추는 단계
```

다.

---

## 왜 지금 ML보다 보정이 먼저인가

지금 시스템은 이미 아래 semantic 구조를 갖고 있다.

```text
Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier
-> ObserveConfirm
-> Exit / Wait
```

여기서 중요한 점은:

- `Position`은 위치와 거리 지도를 말한다.
- `Response`는 실제 사건과 반응을 말한다.
- `State`는 큰지도와 시장환경을 말한다.
- `Evidence / Belief / Barrier`는 신뢰와 차단을 만든다.

즉 `의미 구조` 자체는 이미 만들어졌다.

이 상태에서 바로 `ML`을 얹으면
잘못된 기본형을 `ML`이 억지로 보정하려고 하면서
오히려 과최적화되거나 흔들릴 수 있다.

따라서 순서는 반드시 이렇다.

1. `기본 semantic 구조 고정`
2. `실전 관찰`
3. `기본형 숫자 보정`
4. `기본형이 충분히 괜찮은지 확인`
5. 그 다음 `ML shadow`
6. 마지막에 `ML live calibration`

즉 이 문서의 핵심 문장은 이거다.

```text
ML보다 먼저, 기본형 자체가 높은 승률과 자연스러운 진입/청산을 보여야 한다.
```

---

## 현재 고정된 전제

이 문서는 아래 전제를 고정하고 시작한다.

### 1. `R2-9` 구조는 더 안 흔든다

- `Response 6축 owner = context gate candidate`
- `legacy raw merge`는 더 이상 semantic blend가 아니다
- `legacy`는 `gate metadata 자체가 없을 때만` 기술 fallback이다

즉 지금은:

```text
새 구조가 메인
옛 구조는 비상시 기술 fallback
```

으로 본다.

### 2. 지금 수정 대상은 구조가 아니다

지금 수정하는 것은 아래 같은 것들이다.

- `ambiguity_penalty`
- `context gate weight`
- `micro 반응 비중`
- `S/R vs trendline 비중`
- `mid reclaim / mid lose 민감도`
- `wait/confirm threshold`

즉 지금은:

```text
owner 변경
feature 추가
layer 재배치
```

가 아니라

```text
숫자 민감도 조정
```

단계다.

---

## 전체 우선순위

현재 기준으로 우선순위는 아래가 가장 자연스럽다.

### 우선순위 1. `ambiguity_penalty`

가장 먼저 보는 이유:

- 지금 병목의 상당수가 `Response는 읽었는데 WAIT가 너무 많다` 쪽으로 보인다.
- 이때 제일 먼저 의심해야 하는 것이 `애매함(conflict/indecision/middle)`을 과하게 벌점 주고 있는지 여부다.

### 우선순위 2. `conflict gate / outer-band guard`

가장 먼저 보는 이유:

- `Response`는 한 방향을 말하고 있는데
- `ObserveConfirm`이 `conflict_*_observe`나 `outer_band_*_observe`로 막는 케이스가 반복되고 있다.

### 우선순위 3. `micro 반응 비중`

가장 먼저 보는 이유:

- `1M / 5M` 반응을 너무 약하게 보면 타이밍을 놓치고
- 너무 세게 보면 흔들림을 과신하게 된다.

### 우선순위 4. `S/R vs trendline 비중`

가장 먼저 보는 이유:

- 지금 `수평 레벨`과 `대각 추세선` 중 무엇이 더 owner처럼 행동하는지가 실전 체감에 큰 영향을 준다.

### 우선순위 5. `mid_reclaim_up / mid_lose_down`

가장 먼저 보는 이유:

- 끝단 반등/붕괴보다 덜 눈에 띄지만,
- 실제로는 `가짜 반등`, `중심 회복 실패`, `애매한 재진입`을 많이 좌우한다.

### 우선순위 6. `hold/exit` 관련 숫자

가장 먼저 보지 않는 이유:

- 진입 해석과 엔트리 wait 구조가 아직 흔들리면
- hold/exit만 먼저 만져도 원인이 흐려진다.

---

## 점검 순서

보정 전에 케이스를 볼 때는 아래 순서를 유지하는 것이 좋다.

### 1. 먼저 `Response`가 뭐라고 읽었는지 본다

볼 항목:

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

함께 볼 것:

- 최상위 축이 무엇인지
- 1위와 2위 축 차이가 큰지
- buy-type인지 sell-type인지

### 2. 그 다음 `Position`이 그 해석을 받쳐주는지 본다

볼 항목:

- `primary_label`
- `secondary_context_label`
- `position_conflict_score`
- `box_state`
- `bb_state`

### 3. 그 다음 `ObserveConfirm`이 왜 WAIT/CONFIRM을 냈는지 본다

볼 항목:

- `action`
- `side`
- `reason`

### 4. 병목을 분류한다

반드시 아래 4가지 중 하나로 잘라서 본다.

- `Response 문제`
- `ObserveConfirm 문제`
- `정상 WAIT`
- `hold/exit 문제`

### 5. 한 번에 한 항목만 보정한다

예:

- 먼저 `ambiguity_penalty`
- 그 다음 `conflict gate`
- 그 다음 `micro 비중`

이런 식으로 진행한다.

한 번에 여러 항목을 동시에 바꾸면
무엇이 실제 원인이었는지 알기 어려워진다.

---

## 현재 가장 중요한 영어 변수들 설명

아래 변수들은 지금 단계에서 특히 자주 보게 될 값들이다.
각 변수는 `무슨 뜻인지`, `올리면 어떻게 되는지`, `내리면 어떻게 되는지`를 같이 봐야 한다.

---

## 1. Ambiguity / Conflict 계열

### `ambiguity_penalty`

주석:

```text
지금 상황이 얼마나 애매한지에 대한 벌점
```

뜻:

- `middle neutrality`
- `position conflict`
- `micro indecision`
- `UNRESOLVED / CONFLICT label`

같은 요소를 모아 만든 `대기 유도 패널티`다.

올리면:

- `WAIT`가 늘어난다
- 애매한 자리 진입이 줄어든다
- 하지만 좋은 자리도 놓칠 수 있다

내리면:

- 진입은 늘어난다
- conflict 상황에서도 더 빨리 들어간다
- 하지만 잡손실과 churn이 늘 수 있다

의심해야 할 증상:

- `Response는 buy/sell인데 ObserveConfirm이 자꾸 WAIT`
- `conflict_*_observe`가 너무 자주 뜸

---

### `position_conflict_score`

주석:

```text
Position 내부에서 box/bb/label이 서로 얼마나 충돌하는지
```

뜻:

- `box는 lower`
- `bb는 upper`
- `primary_label`이 `CONFLICT_*`

같은 상황에서 커진다.

올리면:

- gate가 더 보수적으로 된다
- 양쪽 힘이 섞인 자리를 더 많이 `WAIT`로 돌린다

내리면:

- conflict 상황도 더 빨리 한쪽 축으로 읽게 된다

의심해야 할 증상:

- `BTC`처럼 `하단 컨텍스트 + 상방 micro break`가 같이 있는 자리에서 너무 오래 못 들어감

---

### `label_penalty`

주석:

```text
primary_label 자체가 UNRESOLVED/CONFLICT일 때 붙는 추가 패널티
```

뜻:

- `UNRESOLVED_POSITION`
- `CONFLICT_*`

같은 label일 때 gate가 신호를 덜 믿게 만드는 값이다.

올리면:

- unresolved/conflict 자리는 더 보수적으로 본다

내리면:

- label이 애매해도 신호를 더 살려준다

---

## 2. Zone / 위치 맥락 계열

### `lower_zone_weight`

주석:

```text
현재 위치가 lower zone 성격을 얼마나 갖는지
```

뜻:

- `box_zone`
- `bb20_zone`
- `bb44_zone`

을 합성해서 만든 `하단 맥락 강도`다.

높을수록:

- 하단 반응을 더 믿기 쉬워진다
- `lower_hold_up`, `lower_break_down` 계열이 유리해진다

---

### `upper_zone_weight`

주석:

```text
현재 위치가 upper zone 성격을 얼마나 갖는지
```

높을수록:

- 상단 반응을 더 믿기 쉬워진다
- `upper_reject_down`, `upper_break_up` 계열이 유리해진다

---

### `middle_zone_weight`

주석:

```text
현재 위치가 middle zone 성격을 얼마나 갖는지
```

높을수록:

- 중심 회복/상실 계열이 살아난다
- 동시에 애매함도 커질 수 있다

의심해야 할 증상:

- middle인데도 너무 성급하게 edge 방향으로 들어감
- 혹은 middle에서 아무것도 못 하고 계속 WAIT만 함

---

## 3. Anchor / 지지저항 맥락 계열

### `support_anchor`

주석:

```text
지금 근처의 support가 실제 반응 anchor로서 얼마나 살아 있는지
```

뜻:

- `sr_support_proximity`
- `support_hold_strength`
- `trend_support_hold_strength`

같은 값을 바탕으로 만든다.

높을수록:

- 하단 반등과 지지형 해석이 살아난다

---

### `support_break_anchor`

주석:

```text
지금 support 붕괴 해석을 얼마나 강하게 열어둘지
```

뜻:

- `support_break_strength`
- `trend_support_break_strength`

같은 값을 바탕으로 만든다.

높을수록:

- `lower_break_down` 계열이 더 쉽게 살아난다

---

### `resistance_anchor`

주석:

```text
지금 근처의 resistance가 실제 반응 anchor로서 얼마나 살아 있는지
```

뜻:

- `sr_resistance_proximity`
- `resistance_reject_strength`
- `trend_resistance_reject_strength`

같은 값을 바탕으로 만든다.

높을수록:

- `upper_reject_down` 계열이 더 쉽게 살아난다

---

### `resistance_break_anchor`

주석:

```text
지금 resistance 돌파 해석을 얼마나 강하게 열어둘지
```

뜻:

- `resistance_break_strength`
- `trend_resistance_break_strength`

같은 값을 바탕으로 만든다.

높을수록:

- `upper_break_up` 계열이 더 쉽게 살아난다

---

## 4. Bias / 큰지도 계열

### `raw_bias`

주석:

```text
상위 MA / 큰지도 해석이 bullish인지 bearish인지 나타내는 순수 bias
```

뜻:

- 양수면 bullish 쪽
- 음수면 bearish 쪽

이 bias 자체는 gate의 직접 owner가 아니라,
후속 `bull_bias_weight`, `bear_bias_weight`의 재료다.

---

### `bull_bias_weight`

주석:

```text
큰지도가 bullish 쪽을 얼마나 받쳐주는지
```

높을수록:

- bullish reversal / bullish break 쪽 가중치가 커질 수 있다

---

### `bear_bias_weight`

주석:

```text
큰지도가 bearish 쪽을 얼마나 받쳐주는지
```

높을수록:

- bearish reversal / bearish break 쪽 가중치가 커질 수 있다

---

## 5. Size / 지도 크기 계열

### `compression_score`

주석:

```text
지금 지도(box/band)가 얼마나 압축되어 있는지
```

뜻:

- 좁은 박스
- 좁은 밴드
- 응축 상태

를 의미한다.

높을수록:

- 압축 후 breakout 가능성을 더 신경 써야 할 수 있다
- noise와 fake move 구간도 같이 고려해야 한다

---

### `expansion_score`

주석:

```text
지금 지도(box/band)가 얼마나 확장되어 있는지
```

뜻:

- 넓은 박스
- 넓은 밴드
- 이미 변동이 크게 벌어진 상태

를 의미한다.

높을수록:

- 돌파 지속보다 exhaustion 가능성도 같이 봐야 할 수 있다

---

## 6. Reversal / Break gate 계열

### `bull_reversal_gate`

주석:

```text
bullish reversal 계열 신호를 지금 자리에서 얼마나 살릴지
```

주로 영향을 주는 것:

- `lower_hold_up`
- 일부 `mid_reclaim_up`

---

### `bear_reversal_gate`

주석:

```text
bearish reversal 계열 신호를 지금 자리에서 얼마나 살릴지
```

주로 영향을 주는 것:

- `upper_reject_down`
- 일부 `mid_lose_down`

---

### `bull_break_gate`

주석:

```text
bullish breakout 계열 신호를 지금 자리에서 얼마나 살릴지
```

주로 영향을 주는 것:

- `upper_break_up`

---

### `bear_break_gate`

주석:

```text
bearish breakdown 계열 신호를 지금 자리에서 얼마나 살릴지
```

주로 영향을 주는 것:

- `lower_break_down`

---

### `mid_reclaim_gate`

주석:

```text
중심 회복형 상승 해석을 얼마나 살릴지
```

주로 영향을 주는 것:

- `mid_reclaim_up`

---

### `mid_lose_gate`

주석:

```text
중심 상실형 하락 해석을 얼마나 살릴지
```

주로 영향을 주는 것:

- `mid_lose_down`

---

## 7. S/R subsystem 계열

### `support_hold_strength`

주석:

```text
수평 support에서 실제로 버틴 힘
```

높을수록:

- `lower_hold_up` 쪽 재료가 강해진다

---

### `support_break_strength`

주석:

```text
수평 support가 실제로 무너진 힘
```

높을수록:

- `lower_break_down` 쪽 재료가 강해진다

---

### `resistance_reject_strength`

주석:

```text
수평 resistance에서 실제로 거절당한 힘
```

높을수록:

- `upper_reject_down` 쪽 재료가 강해진다

---

### `resistance_break_strength`

주석:

```text
수평 resistance를 실제로 돌파한 힘
```

높을수록:

- `upper_break_up` 쪽 재료가 강해진다

---

## 8. Trendline subsystem 계열

### `trend_support_hold_strength`

주석:

```text
추세선 support에서 실제로 버틴 힘
```

---

### `trend_support_break_strength`

주석:

```text
추세선 support가 실제로 무너진 힘
```

---

### `trend_resistance_reject_strength`

주석:

```text
추세선 resistance에서 실제로 거절당한 힘
```

---

### `trend_resistance_break_strength`

주석:

```text
추세선 resistance를 실제로 돌파한 힘
```

주의:

- 지금 단계에서 가장 중요한 것은
  `trendline을 무조건 더 믿느냐`
  가 아니라
  `수평 S/R와 비교해 어느 정도 비중을 줄지`
  다.

---

## 9. Micro-TF subsystem 계열

### `micro_bull_reject_strength`

주석:

```text
1M / 5M에서 아래에서 받치고 올라가려는 reject 반응 세기
```

대표 의미:

- 아래꼬리 반등
- micro bullish rejection
- 짧은 분봉의 하단 지지형 반응

---

### `micro_bear_reject_strength`

주석:

```text
1M / 5M에서 위에서 밀리고 내려가려는 reject 반응 세기
```

대표 의미:

- 위꼬리 reject
- micro bearish rejection

---

### `micro_bull_break_strength`

주석:

```text
1M / 5M에서 실제 상방 돌파 몸통이 나오는 힘
```

---

### `micro_bear_break_strength`

주석:

```text
1M / 5M에서 실제 하방 붕괴 몸통이 나오는 힘
```

---

### `micro_indecision_strength`

주석:

```text
1M / 5M에서 애매함, 힘 균형, 방향 미결정이 얼마나 큰지
```

높을수록:

- `ambiguity_penalty`에 기여한다
- 확신을 낮추고 `WAIT` 쪽으로 기운다

---

### `micro_reclaim_up_strength`

주석:

```text
1M / 5M에서 중심을 되찾으며 올라가려는 회복 세기
```

---

### `micro_lose_down_strength`

주석:

```text
1M / 5M에서 중심을 잃고 다시 밀리는 상실 세기
```

---

## 10. Response 6축

이 값들은 최종 반응 축이다.
지금 단계에서는 이 축 자체를 뒤집지 않고,
이 축이 만들어지는 숫자 민감도만 조정한다.

### `lower_hold_up`

주석:

```text
하단 지지 반등 힘
```

대표 재료:

- `support_hold_strength`
- `trend_support_hold_strength`
- `micro_bull_reject_strength`
- `support_hold_confirm`

---

### `lower_break_down`

주석:

```text
하단 지지 붕괴 힘
```

대표 재료:

- `support_break_strength`
- `trend_support_break_strength`
- `micro_bear_break_strength`

---

### `mid_reclaim_up`

주석:

```text
중심 회복 상승 힘
```

대표 재료:

- `micro_reclaim_up_strength`
- bullish 2봉/3봉 reversal
- lower -> mid 회복 반응

---

### `mid_lose_down`

주석:

```text
중심 상실 하락 힘
```

대표 재료:

- `micro_lose_down_strength`
- bearish 2봉/3봉 reversal
- mid 상실 반응

---

### `upper_reject_down`

주석:

```text
상단 저항 거절 하락 힘
```

대표 재료:

- `resistance_reject_strength`
- `trend_resistance_reject_strength`
- `micro_bear_reject_strength`
- `resistance_reject_confirm`

---

### `upper_break_up`

주석:

```text
상단 저항 돌파 상승 힘
```

대표 재료:

- `resistance_break_strength`
- `trend_resistance_break_strength`
- `micro_bull_break_strength`

---

## 증상별 튜닝 가이드

이 표는 실전에서 가장 자주 참고하게 될 표다.

| 증상 | 먼저 볼 변수 | 왜 보는가 | 일반적인 조정 방향 |
|---|---|---|---|
| `Response는 한쪽인데 WAIT가 너무 많다` | `ambiguity_penalty`, `position_conflict_score`, `label_penalty` | 애매함 벌점이 너무 센지 확인 | `ambiguity_penalty` 소폭 하향 |
| `conflict_*_observe`가 반복된다 | `position_conflict_score`, `label_penalty`, `bull/bear gate` | conflict가 실제보다 과하게 해석되는지 확인 | conflict 관련 패널티 소폭 완화 |
| `outer_band_*_observe`가 반복된다 | `support_anchor`, `resistance_anchor`, `bull_reversal_gate`, `bear_reversal_gate` | anchor가 약해서 reversal이 못 살아나는지 확인 | anchor 조건 또는 reversal gate 소폭 완화 |
| `하단 반등을 너무 늦게 본다` | `micro_bull_reject_strength`, `support_hold_strength`, `trend_support_hold_strength` | 하단 반등 재료가 약하게 합쳐지는지 확인 | hold 쪽 비중 소폭 상향 |
| `하단인데 자꾸 붕괴로 본다` | `support_break_strength`, `trend_support_break_strength`, `bear_break_gate` | break 계열이 과도한지 확인 | break 비중 소폭 하향 또는 hold 비중 상향 |
| `상단인데 돌파로 너무 잘 본다` | `resistance_break_strength`, `trend_resistance_break_strength`, `micro_bull_break_strength` | break가 과하게 살아나는지 확인 | upper break 관련 비중 소폭 하향 |
| `상단 거절을 잘 못 잡는다` | `resistance_reject_strength`, `trend_resistance_reject_strength`, `micro_bear_reject_strength` | reject 계열이 약하게 반영되는지 확인 | upper reject 관련 비중 소폭 상향 |
| `1M / 5M에 너무 흔들린다` | `micro_*_strength`, `micro_indecision_strength` | micro를 과신하는지 확인 | micro 비중 하향, indecision 영향 상향 |
| `수평 S/R를 너무 무시한다` | `support_*_strength`, `resistance_*_strength` | trendline이 상대적으로 과한지 확인 | S/R 비중 상향 |
| `추세선만 너무 믿는다` | `trend_*_strength` | 추세선 비중이 너무 높은지 확인 | trendline 비중 하향 |
| `중앙에서 괜히 들어간다` | `middle_zone_weight`, `mid_reclaim_gate`, `mid_lose_gate`, `ambiguity_penalty` | middle 해석이 너무 공격적인지 확인 | middle 관련 gate 보수화 |
| `중앙인데 너무 아무것도 못 한다` | `mid_reclaim_gate`, `mid_lose_gate`, `ambiguity_penalty` | 중앙 회복/상실을 너무 안 믿는지 확인 | mid gate 소폭 상향 또는 ambiguity 완화 |

---

## 보정 원칙

이 단계에서 반드시 지켜야 할 원칙이다.

### 원칙 1. 한 번에 하나만 조정

예:

- 먼저 `ambiguity_penalty`
- 다음 관찰 후 `micro 비중`
- 그 다음 `S/R vs trendline`

이런 식으로 간다.

### 원칙 2. 조정폭은 작게

권장 시작폭:

- `±5%`

권장 최대폭:

- `±10~15%`

지금 단계에서 큰 폭으로 움직이면
구조가 바뀌는 느낌이 나기 시작하므로 좋지 않다.

### 원칙 3. 먼저 심볼 공통 보정

처음부터:

- `NAS 전용`
- `XAU 전용`
- `BTC 전용`

으로 쪼개지 말고,
먼저 공통 보정으로 해결 가능한지 본다.

정말 필요할 때만 symbol-specific 보정을 고려한다.

### 원칙 4. 먼저 현재 병목을 해결

현재 관찰상 첫 병목은
`Response 오독`보다 `ObserveConfirm 보수화` 가능성이 더 높다.

따라서 지금은:

1. `ambiguity`
2. `conflict / outer-band guard`
3. `micro 타이밍성`

순으로 보는 것이 맞다.

---

## 단계별 로드맵

## Phase 1. Freeze

목표:

- `R2-9` 구조를 더 흔들지 않는다

해야 할 것:

- `6축 owner = context gate candidate` 유지
- `legacy semantic blend` 금지
- `legacy`는 gate 없음 상황에서만 기술 fallback

완료 기준:

- 구조 관련 코드 수정 없이 관찰/보정만 진행

---

## Phase 2. Observation

목표:

- 실제 병목이 무엇인지 정확히 자른다

해야 할 것:

- 케이스를 4종으로 분류
  - `Response 문제`
  - `ObserveConfirm 문제`
  - `정상 WAIT`
  - `hold/exit 문제`

현재 관찰 기준 참고:

- `BTC`: Response는 buy-type인데 `conflict_*_observe`가 반복되는 경향
- `XAU`: 혼합형이라 정상 WAIT에 가까운 경우가 많음
- `NAS`: Response와 ObserveConfirm side가 어긋나는 케이스가 관찰됨

완료 기준:

- 무엇을 먼저 만져야 하는지 우선순위가 분명해짐

---

## Phase 3. Calibration Pass 1

목표:

- `WAIT 과보수`를 먼저 줄인다

추천 순서:

1. `ambiguity_penalty`
2. `position_conflict_score / label_penalty`
3. `bull_reversal_gate / bear_reversal_gate`
4. `outer-band 관련 observe guard`

완료 기준:

- `Response는 맞는데 WAIT` 케이스가 줄어든다
- 성급한 오진입이 급증하지 않는다

---

## Phase 4. Calibration Pass 2

목표:

- 진입 타이밍 체감을 맞춘다

추천 순서:

1. `micro_bull_reject_strength / micro_bear_reject_strength`
2. `micro_bull_break_strength / micro_bear_break_strength`
3. `micro_reclaim_up_strength / micro_lose_down_strength`
4. `micro_indecision_strength`

완료 기준:

- 너무 늦게 들어가거나
- 너무 1M/5M에 흔들리는 문제가 줄어든다

---

## Phase 5. Calibration Pass 3

목표:

- 선 owner의 체감을 맞춘다

추천 순서:

1. `support_* / resistance_*` 계열
2. `trend_support_* / trend_resistance_*` 계열
3. `S/R vs trendline` 상대 비중

완료 기준:

- 수평 S/R를 너무 무시하지도 않고
- 추세선을 과신하지도 않는 균형이 잡힌다

---

## Phase 6. Mid-axis tuning

목표:

- `mid_reclaim_up / mid_lose_down`을 체감에 맞춘다

추천 순서:

1. `middle_zone_weight`
2. `mid_reclaim_gate`
3. `mid_lose_gate`

완료 기준:

- 중앙 회복과 상실이 실제 차트 감각과 더 자주 맞는다

---

## Phase 7. Hold / Exit tuning

목표:

- 좋은 진입이 자잘한 손실이나 너무 빠른 청산으로 끝나지 않게 한다

주의:

- 이 단계는 엔트리 구조가 어느 정도 안정된 뒤에 들어간다

완료 기준:

- "조금만 흔들려도 바로 청산" 현상이 줄어든다

---

## Phase 8. Pre-ML acceptance

목표:

- `ML 없이도 기본형이 괜찮다`는 상태를 만든다

확인해야 할 것:

- 진입 품질
- 기다림 품질
- 보유 품질
- 자잘한 손실 반복 여부
- 심볼별 체감 괴리 정도

완료 기준:

- 이제 ML이 구조를 구하는 역할이 아니라
  숫자 미세 보정만 해도 될 수준이라고 판단됨

---

## 마지막 정리

이 문서의 핵심은 아주 간단하다.

```text
지금은 ML보다 먼저,
기본 semantic 구조가 이미 높은 승률과 자연스러운 진입/청산을 보여야 한다.
```

따라서 우선순위는:

1. `R2-9 고정`
2. `관찰`
3. `ambiguity / conflict / outer-band 보정`
4. `micro 비중 보정`
5. `S/R vs trendline 보정`
6. `mid reclaim / mid lose 보정`
7. `hold/exit 보정`
8. 마지막에 `ML`

즉 지금 당장 가장 중요한 단계는:

```text
구조를 다시 바꾸는 것
```

이 아니라

```text
현재 구조에서 어떤 숫자가 기본 승률을 깎고 있는지 찾아서 작은 폭으로 맞추는 것
```

이다.
