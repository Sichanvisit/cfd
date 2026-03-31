# R2-2 Candle Pattern 정의표

## 목적

이 문서는 `R2-2 Candle pattern`에서

- 패턴이 본질적으로 무엇인지
- 어떤 기준으로 점수화할지
- 어떤 패턴이 어떤 `motif`로 연결될지

를 한눈에 보기 좋게 정리한 문서다.

---

## 먼저 결론

캔들 패턴은 절대적인 진실이 아니다.

즉:

- `Hammer`
- `Shooting Star`
- `Bullish Engulfing`
- `Morning Star`

같은 이름은

`사람들이 자주 보이는 봉의 모양과 조합에 붙여놓은 라벨`

에 가깝다.

그래서 시스템에서는 이렇게 보는 게 맞다.

```text
descriptor 조합
-> pattern_like score
-> motif
-> context gate
-> Response 6축
```

즉 우리가 만들려는 것은:

- `"이건 Hammer다 / 아니다"`가 아니라
- `"이건 hammer-like가 0.73이다"` 같은 연속 점수다.

---

## 패턴 정의의 4가지 기준

캔들 패턴은 아래 4개를 섞어서 정의하는 게 가장 안정적이다.

### 1. shape

- 몸통 방향
- 몸통 비중
- 윗꼬리 비중
- 아랫꼬리 비중
- 종가 위치

즉:

- 봉이 어떻게 생겼나

### 2. size

- 전체 range가 최근 평균 대비 얼마나 큰가
- 몸통이 최근 평균 대비 얼마나 큰가

즉:

- 이 봉이 평소보다 의미 있게 큰가

### 3. sequence

- 이전 1봉, 2봉과 어떤 관계인가
- engulf 했는가
- 3봉 구조가 reversal에 가까운가
- 3연속 강세/약세인가

즉:

- 이 봉 하나가 아니라 직전 흐름까지 포함하면 어떤 모양인가

### 4. context

- 하락 끝인가
- 상승 끝인가
- lower zone인가
- upper zone인가
- support/resistance 근처인가

즉:

- 지금 자리에서 이 패턴이 살아남는가

---

## 점수 구조 기본식

패턴은 hard rule보다 soft score가 안전하다.

기본 형태:

```text
pattern_score
= shape_score
 * size_weight
 * sequence_weight
 * context_weight
```

또는

```text
pattern_score
= 0.50 * shape
+ 0.20 * size
+ 0.20 * sequence
+ 0.10 * context
```

둘 중 무엇을 쓰든 중요한 건:

- 이름을 바로 확정하지 말 것
- `*_like_score`로 둘 것

이다.

---

## 1. 단일봉 패턴

## Hammer

### 사람 해석

- 아래꼬리가 길고
- 몸통은 위쪽에 있으며
- 하단 rejection 느낌이 강한 봉

### 시스템 해석

- `lower_wick_energy` 높음
- `upper_wick_energy` 낮음
- `close_location_energy` 높음
- `body_shape_energy` 너무 크지 않음

### 예시 규칙

```text
hammer_like
= 0.45 * lower_wick_energy
+ 0.30 * max(close_location_energy, 0)
+ 0.15 * max(body_signed_energy, 0)
+ 0.10 * (1 - upper_wick_energy)
```

### 주 연결 motif

- `bull_reject`

### 주 연결 축

- `lower_hold_up`
- 보조로 `mid_reclaim_up`

---

## Inverted Hammer

### 사람 해석

- 하락 끝에서 위꼬리 긴 봉
- 아직 반전 확정은 아니지만 위쪽 시도가 보임

### 시스템 해석

- `upper_wick_energy` 높음
- `close_location_energy` 중립 이상
- `body_shape_energy` 작음
- 하락 후에서 나와야 의미 증가

### 주 연결 motif

- `bull_probe`
- 약한 `bull_reversal`

### 주 연결 축

- `mid_reclaim_up`
- 약한 `lower_hold_up`

---

## Hanging Man

### 사람 해석

- 상승 끝의 망치형
- 하단이 한 번 크게 열렸다는 경고

### 시스템 해석

- 외형은 Hammer와 비슷
- 하지만 `상승 이후`, `upper zone`, `resistance`에서 의미 증가

### 주 연결 motif

- `bear_warning`
- 약한 `bear_reject`

### 주 연결 축

- `upper_reject_down`

---

## Shooting Star

### 사람 해석

- 위꼬리가 길고
- 상단에서 밀린 봉

### 시스템 해석

- `upper_wick_energy` 높음
- `lower_wick_energy` 낮음
- `close_location_energy` 낮음
- `body_shape_energy` 크지 않음

### 예시 규칙

```text
shooting_star_like
= 0.45 * upper_wick_energy
+ 0.30 * max(-close_location_energy, 0)
+ 0.15 * max(-body_signed_energy, 0)
+ 0.10 * (1 - lower_wick_energy)
```

### 주 연결 motif

- `bear_reject`

### 주 연결 축

- `upper_reject_down`
- 보조로 `mid_lose_down`

---

## Doji

### 사람 해석

- 시가와 종가가 거의 같음
- 방향성보다 애매함이 강함

### 시스템 해석

- `body_shape_energy` 매우 낮음
- 윗꼬리/아랫꼬리 중 한쪽이 특별히 강하지 않음

### 주 연결 motif

- `indecision`

### 주 연결 축

- 직접 가산보다 `패널티/보류`

---

## Long-legged Doji

### 사람 해석

- 꼬리 양쪽이 길고 몸통이 매우 작음
- 변동성은 컸지만 방향은 미정

### 시스템 해석

- `body_shape_energy` 낮음
- `upper_wick_energy`, `lower_wick_energy` 모두 높음
- `range_size_energy` 높음

### 주 연결 motif

- `indecision`
- `volatility_pause`

### 주 연결 축

- 직접 가산보다 `wait/penalty`

---

## Dragonfly Doji

### 사람 해석

- 아래꼬리 매우 길고 몸통은 거의 없음
- 아래에서 쓸어담고 복귀

### 시스템 해석

- `lower_wick_energy` 매우 높음
- `body_shape_energy` 매우 낮음
- `close_location_energy` 높음

### 주 연결 motif

- `bull_reject`

### 주 연결 축

- `lower_hold_up`

---

## Gravestone Doji

### 사람 해석

- 위꼬리 매우 길고 몸통은 거의 없음
- 위에서 밀림

### 시스템 해석

- `upper_wick_energy` 매우 높음
- `body_shape_energy` 매우 낮음
- `close_location_energy` 낮음

### 주 연결 motif

- `bear_reject`

### 주 연결 축

- `upper_reject_down`

---

## Marubozu

### 사람 해석

- 꼬리가 거의 없고 몸통이 큰 추세 봉

### 시스템 해석

- `body_shape_energy` 높음
- `upper_wick_energy`, `lower_wick_energy` 낮음
- `body_size_energy` 높음

### 분기

- 양봉 Marubozu
  - `bull_break_body`
  - `upper_break_up`
- 음봉 Marubozu
  - `bear_break_body`
  - `lower_break_down`

---

## Spinning Top

### 사람 해석

- 몸통이 작고 꼬리가 양쪽으로 있음
- 힘 균형

### 시스템 해석

- `body_shape_energy` 낮음
- `upper_wick_energy`, `lower_wick_energy` 둘 다 중간 이상

### 주 연결 motif

- `indecision`

### 주 연결 축

- 직접 가산보다 `감산/대기`

---

## 2. 2봉 패턴

## Bullish Engulfing

### 사람 해석

- 이전 음봉을 현재 큰 양봉이 덮음

### 시스템 해석

- 이전 봉 음봉
- 현재 봉 양봉
- 현재 몸통이 이전 몸통을 engulf
- 현재 body size가 충분히 큼

### 예시 규칙

```text
bullish_engulfing_like
= 0.35 * prev_bear_strength
+ 0.40 * engulf_up
+ 0.25 * current_bull_body_strength
```

### 주 연결 motif

- `bull_reversal_2bar`

### 주 연결 축

- `lower_hold_up`
- `mid_reclaim_up`

---

## Bearish Engulfing

### 사람 해석

- 이전 양봉을 현재 큰 음봉이 덮음

### 시스템 해석

- 이전 봉 양봉
- 현재 봉 음봉
- 현재 몸통이 이전 몸통을 engulf
- 현재 body size가 충분히 큼

### 주 연결 motif

- `bear_reversal_2bar`

### 주 연결 축

- `upper_reject_down`
- `mid_lose_down`

---

## Harami

### 사람 해석

- 큰 봉 뒤에 작은 봉이 몸통 안으로 들어옴
- 멈춤/감속

### 시스템 해석

- 현재 body size 작음
- 현재 몸통이 이전 몸통 내부

### 주 연결 motif

- `indecision`
- `pause`

### 주 연결 축

- 직접 가산보다 보류/약화

---

## Harami Cross

### 사람 해석

- Harami + Doji
- 힘 빠짐이 더 강함

### 주 연결 motif

- `indecision`

### 주 연결 축

- 직접 가산보다 보류

---

## Tweezer Top

### 사람 해석

- 비슷한 고점 두 번
- 저항 확인

### 시스템 해석

- 두 봉 고점이 매우 유사
- 둘째 봉이 위에서 밀리는 성격

### 주 연결 motif

- `bear_reject`
- `resistance_reject_confirm`

### 주 연결 축

- `upper_reject_down`

---

## Tweezer Bottom

### 사람 해석

- 비슷한 저점 두 번
- 지지 확인

### 시스템 해석

- 두 봉 저점이 매우 유사
- 둘째 봉이 아래에서 받아 올리는 성격

### 주 연결 motif

- `bull_reject`
- `support_hold_confirm`

### 주 연결 축

- `lower_hold_up`

---

## 3. 3봉 패턴

## Morning Star

### 사람 해석

- 큰 음봉
- 작은 멈춤 봉
- 큰 양봉 회복

### 시스템 해석

- 1봉 전 하락 강함
- 중간 봉 pause/indecision
- 현재 봉 recovery 강함

### 예시 규칙

```text
morning_star_like
= 0.30 * bar1_bear_strength
+ 0.20 * bar2_pause
+ 0.35 * bar3_recovery_up
+ 0.15 * close_back_inside
```

### 주 연결 motif

- `bull_reversal_3bar`

### 주 연결 축

- `lower_hold_up`
- `mid_reclaim_up`

---

## Evening Star

### 사람 해석

- 큰 양봉
- 작은 멈춤 봉
- 큰 음봉 회복 실패

### 시스템 해석

- 1봉 전 상승 강함
- 중간 봉 pause/indecision
- 현재 봉 하락 회복 실패

### 주 연결 motif

- `bear_reversal_3bar`

### 주 연결 축

- `upper_reject_down`
- `mid_lose_down`

---

## Three White Soldiers

### 사람 해석

- 양봉 3개가 연속으로 강하게 전진

### 시스템 해석

- 연속 양봉
- 종가가 지속적으로 위로 이동
- 위꼬리가 짧고 body가 의미 있음

### 주 연결 motif

- `bull_break_body`
- `bull_continuation`

### 주 연결 축

- `upper_break_up`
- 보조로 `mid_reclaim_up`

---

## Three Black Crows

### 사람 해석

- 음봉 3개가 연속으로 강하게 전진

### 시스템 해석

- 연속 음봉
- 종가가 지속적으로 아래로 이동
- 아래꼬리가 짧고 body가 의미 있음

### 주 연결 motif

- `bear_break_body`
- `bear_continuation`

### 주 연결 축

- `lower_break_down`
- 보조로 `mid_lose_down`

---

## R2-2에서 중요한 원칙

## 1. 패턴명은 hard rule이 아니라 soft score로 둔다

좋은 방식:

- `hammer_like = 0.73`
- `shooting_star_like = 0.18`
- `bullish_engulfing_like = 0.00`

나쁜 방식:

- `is_hammer = True / False`

---

## 2. 패턴은 바로 BUY/SELL가 아니다

패턴은 다음 단계에서 `motif`로 압축된다.

예:

- `Hammer` -> `bull_reject`
- `Shooting Star` -> `bear_reject`
- `Bullish Engulfing` -> `bull_reversal_2bar`
- `Morning Star` -> `bull_reversal_3bar`

---

## 3. context가 없으면 패턴 해석은 약하다

같은 Hammer라도:

- lower zone + support 근처 = 강함
- middle = 약함
- upper zone = 거의 무의미

즉 R2-2는 패턴 정의까지만 하고,
실제 의미 증폭은 다음 `R2-4 context gate`에서 한다.

---

## R2-2 결과물 형태 추천

최소 출력 예시:

```text
single_candle_patterns_v1 = {
  hammer_like,
  inverted_hammer_like,
  hanging_man_like,
  shooting_star_like,
  doji_like,
  long_legged_doji_like,
  dragonfly_doji_like,
  gravestone_doji_like,
  bullish_marubozu_like,
  bearish_marubozu_like,
  spinning_top_like,
}

two_bar_patterns_v1 = {
  bullish_engulfing_like,
  bearish_engulfing_like,
  harami_like,
  harami_cross_like,
  tweezer_top_like,
  tweezer_bottom_like,
}

three_bar_patterns_v1 = {
  morning_star_like,
  evening_star_like,
  three_white_soldiers_like,
  three_black_crows_like,
}
```

---

## 한 줄 결론

`R2-2 Candle pattern`은 사람들이 붙여놓은 이름을 믿는 단계가 아니라, descriptor 조합에 soft score 이름을 붙여서 다음 motif 단계로 넘기기 위한 정리 단계라고 보면 된다.
