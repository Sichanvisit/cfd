# Candle Descriptor -> Response 6축 예시

## 목적

이 문서는 `R2-1 Candle descriptor`가 실제로 무엇을 만들고,
그 값이 어떻게 `Response 6축`까지 이어지는지 감각적으로 이해하기 위한 예시 문서다.

핵심:

- `descriptor`는 매수/매도 신호가 아니다
- `descriptor`는 봉의 생김새를 숫자로 기록한 중립 계층이다
- 최종적으로는 `Response 6축`에서
  - 어느 쪽 힘이 얼마나 강한가
  를 `0~1` 강도값으로 읽게 된다

---

## 전체 흐름

```text
OHLC
-> candle descriptor
-> candle pattern
-> candle motif
-> context gate
-> Response 6축
```

쉽게 번역하면:

- `descriptor`
  - 이 봉이 어떻게 생겼나
- `pattern`
  - 그래서 이 생김새를 Hammer, Engulfing 같은 이름으로 볼 수 있나
- `motif`
  - 그 패턴이 bullish reject인지 bearish reject인지
- `context gate`
  - 그런데 그게 지금 자리에서 의미가 있나
- `Response 6축`
  - 그래서 최종적으로 아래/위 어느 쪽 힘을 올릴 건가

---

## 예시 봉 1개

아래 같은 봉을 하나 가정한다.

- `open = 100`
- `high = 102`
- `low = 90`
- `close = 101`

이 봉은 사람 눈으로 보면:

- 양봉
- 아래꼬리가 매우 길다
- 위꼬리는 짧다
- 종가가 고가 근처다

즉 "망치형 비슷하다"라고 느낄 수 있다.

---

## 1. Candle descriptor

### 먼저 계산하는 기본 값

- `range = high - low = 12`
- `body = abs(close - open) = 1`
- `upper_wick = high - max(open, close) = 1`
- `lower_wick = min(open, close) - low = 10`

---

## descriptor 후보와 뜻

### `body_signed_energy`

- 뜻:
  - 양봉/음봉 방향이 얼마나 강한가
- 범위:
  - `-1 ~ 1`
- 예시 계산:

```text
(close - open) / range
= (101 - 100) / 12
= 0.083
```

해석:

- `+0.083`
- 약한 양봉

---

### `body_shape_energy`

- 뜻:
  - 이 봉 안에서 몸통 비중이 얼마나 큰가
- 범위:
  - `0 ~ 1`
- 예시 계산:

```text
body / range
= 1 / 12
= 0.083
```

해석:

- 몸통 비중이 매우 작다

---

### `upper_wick_energy`

- 뜻:
  - 위꼬리 비중이 얼마나 큰가
- 범위:
  - `0 ~ 1`
- 예시 계산:

```text
upper_wick / range
= 1 / 12
= 0.083
```

해석:

- 위꼬리는 짧다

---

### `lower_wick_energy`

- 뜻:
  - 아래꼬리 비중이 얼마나 큰가
- 범위:
  - `0 ~ 1`
- 예시 계산:

```text
lower_wick / range
= 10 / 12
= 0.833
```

해석:

- 아래꼬리가 매우 길다

---

### `close_location_energy`

- 뜻:
  - 종가가 고가 쪽에 붙었나 저가 쪽에 붙었나
- 범위:
  - `-1 ~ 1`
- 예시 계산:

```text
2 * ((close - low) / range) - 1
= 2 * ((101 - 90) / 12) - 1
= 2 * (11 / 12) - 1
= 0.833
```

해석:

- 종가가 고가 쪽에 매우 가깝다

---

### `wick_balance_energy`

- 뜻:
  - 아래꼬리가 우세한가, 위꼬리가 우세한가
- 범위:
  - `-1 ~ 1`
- 예시 계산:

```text
lower_wick_energy - upper_wick_energy
= 0.833 - 0.083
= 0.750
```

해석:

- 아래꼬리 우세가 매우 강하다

---

### `range_size_energy`

- 뜻:
  - 이번 봉 전체 길이가 최근 평균 대비 얼마나 큰가
- 범위:
  - 보통 `0 ~ 3+`
- 예시 가정:
  - 최근 평균 range가 `8`

```text
range / avg_range_20
= 12 / 8
= 1.50
```

해석:

- 이번 봉은 평균보다 꽤 큰 편이다

---

### `body_size_energy`

- 뜻:
  - 몸통 길이가 최근 평균 대비 얼마나 큰가
- 범위:
  - 보통 `0 ~ 3+`
- 예시 가정:
  - 최근 평균 body가 `3`

```text
body / avg_body_20
= 1 / 3
= 0.33
```

해석:

- 몸통 자체는 평균보다 작다

---

## descriptor 결과 요약

이 봉의 descriptor는 대충 이렇게 된다.

```text
body_signed_energy   = 0.083
body_shape_energy    = 0.083
upper_wick_energy    = 0.083
lower_wick_energy    = 0.833
close_location_energy= 0.833
wick_balance_energy  = 0.750
range_size_energy    = 1.50
body_size_energy     = 0.33
```

사람 말로 다시 읽으면:

- 양봉이긴 하지만 몸통은 작다
- 아래꼬리가 아주 길다
- 위꼬리는 짧다
- 종가는 위쪽에서 끝났다
- 전체 길이는 평균보다 크다

---

## 2. Candle pattern

이제 descriptor를 보고 패턴 점수를 만든다.

중요:

- 아직 `BUY/SELL`이 아니다
- 그냥 "이 봉이 hammer-like한가"를 보는 단계다

### 예시: `hammer_score`

예시 수식:

```text
hammer_shape
= 0.45 * lower_wick_energy
+ 0.30 * max(close_location_energy, 0)
+ 0.25 * max(body_signed_energy, 0)

= 0.45 * 0.833
+ 0.30 * 0.833
+ 0.25 * 0.083

= 0.375 + 0.250 + 0.021
= 0.646
```

이제 크기 가중을 곱한다.

예시:

```text
size_weight = 0.7 + 0.6 * softclip(range_size_energy)
```

여기서 `range_size_energy = 1.50`이면
대충 `size_weight ~= 1.18` 정도로 가정할 수 있다.

그러면:

```text
hammer_score_raw = 0.646 * 1.18 = 0.762
hammer_score = clamp(0.762, 0, 1) = 0.762
```

즉:

- `hammer_score = 0.76`

이 봉은 hammer-like 성격이 꽤 강하다.

### 다른 패턴은?

같은 봉에서:

```text
shooting_star_score = 0.05
doji_score = 0.20
bullish_engulfing_score = 0.00
```

정도로 나올 수 있다.

즉 이 봉은:

- 상단 반전형은 아니다
- 장악형도 아니다
- hammer-like가 가장 강하다

---

## 3. Candle motif

이제 패턴 이름을 더 큰 의미 묶음으로 압축한다.

예:

- `Hammer`
- `Dragonfly Doji`
- `Tweezer Bottom`

이런 것들은 다 `bull_reject` 쪽으로 묶을 수 있다.

### 예시 결과

```text
bull_reject = 0.74
bear_reject = 0.06
bull_break_body = 0.10
bear_break_body = 0.02
indecision = 0.12
```

사람 말로 읽으면:

- 아래서 받치고 올라가는 성격이 강하다
- 위에서 밀리는 성격은 약하다
- 강한 돌파 몸통은 아니다
- 애매함은 조금 있다

---

## 4. Context gate

여기가 아주 중요하다.

같은 hammer라도:

- 하단 support 근처에서 나온 hammer
- 박스 중간에서 나온 hammer

의 의미는 다르다.

즉 `motif`를 그대로 6축에 넣지 않고,
현재 위치와 맥락으로 먼저 보정해야 한다.

---

## 같은 봉, 다른 자리 예시

### Case A. lower zone + support 근처

가정:

- Position이 lower zone
- support 근처
- 최근 하락 뒤

그러면 `bull_reject`를 강하게 살린다.

예시:

```text
context_multiplier_for_bull_reject = 0.85

bull_reject_after_context
= 0.74 * 0.85
= 0.63
```

### Case B. box middle + support 없음

가정:

- Position이 middle
- support 없음
- 추세도 애매함

그러면 같은 봉이라도 의미를 크게 낮춘다.

예시:

```text
context_multiplier_for_bull_reject = 0.35

bull_reject_after_context
= 0.74 * 0.35
= 0.26
```

즉 같은 봉이어도 자리 때문에 해석이 달라진다.

---

## 5. Response 6축

이제 최종적으로 어느 축에 힘을 줄지 계산한다.

### 6축

- `lower_hold_up`
- `lower_break_down`
- `mid_reclaim_up`
- `mid_lose_down`
- `upper_reject_down`
- `upper_break_up`

---

## 최종 예시 1

### lower zone + support 근처에서 나온 hammer-like 봉

최종 결과 예시:

```text
lower_hold_up     = 0.68
lower_break_down  = 0.09
mid_reclaim_up    = 0.14
mid_lose_down     = 0.05
upper_reject_down = 0.03
upper_break_up    = 0.11
```

사람 말로 읽으면:

- 하단 지지 반등 힘이 `0.68`
- 하단 붕괴 힘은 `0.09`
- 즉 지금은 "아래쪽에서 받치고 올라가려는 힘"이 더 강하다

이게 네가 말한:

- "아래쪽 몇 % 강함"

느낌에 해당한다.

단 정확히는:

- `확률`이 아니라
- `정규화된 반응 강도`

라고 보는 게 더 안전하다.

---

## 최종 예시 2

### middle에서 나온 같은 hammer-like 봉

최종 결과 예시:

```text
lower_hold_up     = 0.26
lower_break_down  = 0.08
mid_reclaim_up    = 0.18
mid_lose_down     = 0.07
upper_reject_down = 0.03
upper_break_up    = 0.09
```

사람 말로 읽으면:

- 봉 모양은 비슷하지만
- 지금 자리가 lower support가 아니어서
- `lower_hold_up`가 확실한 진입축까지는 못 올라간다

즉 이 경우는:

- 바로 진입보다
- observe 또는 wait

쪽이 더 자연스럽다.

---

## 핵심 정리

### descriptor는 뭘 만드는 단계인가

답:

- `이 봉이 어떻게 생겼는지`
- 중립 숫자로 바꾸는 단계

즉 아직:

- `BUY`
- `SELL`
- `반등 확정`

같은 판단을 안 한다.

### 최종적으로 어떻게 읽히나

결국 `Response 6축`에서는:

- `아래쪽 반등 힘이 얼마나 강한가`
- `아래쪽 붕괴 힘이 얼마나 강한가`
- `위쪽 거절 힘이 얼마나 강한가`
- `위쪽 돌파 힘이 얼마나 강한가`

로 읽히게 된다.

### 중요한 구분

- `descriptor` = 재료
- `pattern` = 이름
- `motif` = 의미 묶음
- `context gate` = 지금 유효한가
- `Response 6축` = 최종 힘의 방향과 세기

---

## 한 줄 결론

`R2-1 Candle descriptor`는 결국 "이 봉의 생김새를 숫자로 기록해서, 나중에 Response 6축에서 어느 쪽 힘이 얼마나 강한지 계산할 수 있게 만드는 준비 단계"라고 이해하면 된다.
