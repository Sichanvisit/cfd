# 캔들 패턴 정리

## 목적

이 문서는 `캔들만` 따로 떼어 정리한 문서다.

- 박스권
- 볼린저밴드
- 위치에너지
- 세션 구조

이런 위치 정보는 여기서 제외한다.

여기서는 오직 아래만 본다.

- 캔들 모양
- 캔들 조합
- 캔들이 말해주는 반응
- 실전에서 어떤 의미로 읽는지
- 앞으로 `Response` 쪽에서 어떻게 묶어 쓸지

즉 이 문서는

- `Position` 문서가 아니라
- `Response` 문서에 가까운 캔들 참고서다.

---

## 핵심 원칙

캔들 패턴은 `단독으로 확정 신호`가 아니라 `반응 해석 도구`로 보는 것이 더 안전하다.

같은 패턴이라도

- 어디에서 나왔는지
- 이전 흐름이 어땠는지
- 다음 캔들이 확인해주는지

에 따라 의미가 달라진다.

그래서 캔들을 읽을 때는 아래 순서가 좋다.

1. 이전 흐름이 상승인지 하락인지 본다.
2. 현재 캔들이 흡수, 거절, 돌파, 망설임 중 무엇인지 본다.
3. 다음 캔들이 확인해주는지 본다.
4. 그 뒤에야 실제 진입/청산 의미를 준다.

---

## 빠른 보기

### 반등 쪽에서 자주 보는 캔들

- Hammer
- Inverted Hammer
- Dragonfly Doji
- Bullish Engulfing
- Morning Star
- Three White Soldiers
- Tweezer Bottom

### 하락 쪽에서 자주 보는 캔들

- Hanging Man
- Shooting Star
- Gravestone Doji
- Bearish Engulfing
- Evening Star
- Three Black Crows
- Tweezer Top

### 방향 애매함 / 힘 균형

- Doji
- Long-legged Doji
- Spinning Top
- Harami
- Harami Cross

### 강한 추세 몸통

- Bullish Marubozu
- Bearish Marubozu

---

## 단일 캔들 패턴

### Hammer

#### 모양

- 아래 꼬리가 길다.
- 몸통은 위쪽에 몰려 있다.
- 보통 하락 말단에서 많이 본다.

#### 의미

- 아래로 밀었지만 다시 사들였다.
- 매도 압수를 누군가 흡수했다는 뜻에 가깝다.

#### 실전 해석

- 단독 매수 확정이라기보다 `하단 지지 가능성` 신호다.
- 다음 캔들이 양봉 확인을 주면 의미가 커진다.

#### 주의

- 횡보 중간에서 뜬 망치형은 힘이 약하다.
- 꼬리가 몸통보다 충분히 길지 않으면 신뢰가 떨어진다.

#### Response 해석

- 기본적으로 `bull_reject_candle`
- 더 넓게는 `support_hold_up` 계열

---

### Inverted Hammer

#### 모양

- 위 꼬리가 길고 몸통은 아래쪽에 있다.
- 하락 끝부분에서 자주 본다.

#### 의미

- 위로 사려는 시도가 처음 들어온 흔적이다.
- 다만 아직 바로 뒤집었다기보다 `매수 시도 등장` 쪽이다.

#### 실전 해석

- 다음 캔들이 상승 확인을 줄 때 의미가 커진다.
- 확인 없이 단독으로 보면 속임수일 수 있다.

#### Response 해석

- `bull_reject_candle`
- 또는 약한 `bull_reversal_2bar` 전조

---

### Hanging Man

#### 모양

- 모양은 Hammer와 비슷하다.
- 하지만 상승 끝에서 나온다.

#### 의미

- 아래로 크게 흔들렸다는 점 자체가 경고다.
- 상승 중 매수 힘이 약해졌을 가능성을 보여준다.

#### 실전 해석

- 단독보다 다음 캔들 하락 확인이 중요하다.

#### Response 해석

- `bear_reject_candle`
- 또는 약한 `resistance_reject_down`

---

### Shooting Star

#### 모양

- 위 꼬리가 길다.
- 몸통은 아래쪽에 있다.
- 보통 상승 말단에서 본다.

#### 의미

- 위로 밀어 올렸지만 끝내 팔아버렸다는 뜻이다.
- 강한 매도 압력 흔적이다.

#### 실전 해석

- 상단 거절 해석에서 매우 자주 쓰는 캔들이다.
- 다음 캔들 하락 확인이 있으면 더 강하다.

#### Response 해석

- `bear_reject_candle`
- `resistance_reject_down`

---

### Doji

#### 모양

- 시가와 종가가 거의 같다.

#### 의미

- 방향 합의가 없는 상태다.
- 힘이 균형인 상태다.

#### 실전 해석

- 단독 방향 신호로 쓰기보다는 `결정 전 정지화면`에 가깝다.
- 다음 캔들 방향이 더 중요하다.

#### Response 해석

- 직접적인 매수/매도 신호보다 `indecision_candle`
- 나중에 `State` 또는 `Barrier` 감점 재료로 쓰기 좋다.

---

### Long-legged Doji

#### 모양

- 꼬리가 양쪽으로 길고 몸통이 작다.

#### 의미

- 위아래로 심하게 흔들렸지만 결론이 안 났다.
- 변동성은 크지만 방향 합의는 없다.

#### 실전 해석

- 유동성 스윕, 손절 사냥 뒤 방향 결정 직전 장면에서 자주 보인다.
- 단독 진입보다 다음 캔들 확인이 중요하다.

#### Response 해석

- `indecision_candle`
- 경우에 따라 `liquidity_sweep_watch` 후보

---

### Dragonfly Doji

#### 모양

- 아래 꼬리가 매우 길고 위쪽에서 마감한다.

#### 의미

- 아래 매도 압력이 거의 다 흡수됐다.
- 하단 reject 성격이 강하다.

#### 실전 해석

- 하단 반등 시그널로 자주 본다.
- 확인 캔들이 붙으면 매수 반전 의미가 커진다.

#### Response 해석

- `bull_reject_candle`
- `support_hold_up`

---

### Gravestone Doji

#### 모양

- 위 꼬리가 매우 길고 아래쪽에서 마감한다.

#### 의미

- 위로 올린 힘을 전부 되돌려 팔아버린 형태다.
- 상단 reject 의미가 강하다.

#### Response 해석

- `bear_reject_candle`
- `resistance_reject_down`

---

### Marubozu

#### 모양

- 꼬리가 거의 없고 몸통이 강하다.

#### 의미

- 한 방향으로 밀어붙인 캔들이다.
- 반전보다 `지속` 의미가 더 크다.

#### 실전 해석

- 양봉 Marubozu는 상방 돌파/상승 지속
- 음봉 Marubozu는 하방 붕괴/하락 지속

#### Response 해석

- 양봉: `bull_break_body`, `resistance_break_up`
- 음봉: `bear_break_body`, `support_break_down`

---

### Spinning Top

#### 모양

- 몸통이 작고 위아래 꼬리가 모두 있다.

#### 의미

- 힘이 균형이고 결론이 약하다.

#### 실전 해석

- 방향 확인용이 아니라 `망설임` 신호다.
- 다른 강한 반응이 있어야 의미가 붙는다.

#### Response 해석

- `indecision_candle`

---

## 2개 캔들 패턴

### Bullish Engulfing

#### 모양

- 큰 양봉이 이전 음봉 몸통을 덮는다.

#### 의미

- 이전 매도 흐름을 매수가 한 번에 뒤집었다.

#### 실전 해석

- 반등 쪽에서 가장 자주 쓰는 패턴 중 하나다.
- 지지, 거래량, 다음 캔들 유지가 붙으면 강해진다.

#### Response 해석

- `bull_reversal_2bar`
- `support_hold_up`
- 경우에 따라 `mid_reclaim_up`

---

### Bearish Engulfing

#### 모양

- 큰 음봉이 이전 양봉 몸통을 덮는다.

#### 의미

- 매수가 밀리며 매도가 우위를 가져왔다.

#### Response 해석

- `bear_reversal_2bar`
- `resistance_reject_down`
- 경우에 따라 `mid_lose_down`

---

### Harami

#### 모양

- 작은 캔들이 큰 캔들 몸통 안에 들어온다.

#### 의미

- 강한 흐름 뒤에 힘이 줄고 있다는 뜻이다.

#### 실전 해석

- 반전 확정이라기보다 `감속` 신호다.
- 다음 캔들 확인이 꼭 필요하다.

#### Response 해석

- 단독 방향 신호보다 `indecision_cluster`
- 보조 확인용

---

### Harami Cross

#### 모양

- Harami 구조인데 안쪽 캔들이 Doji다.

#### 의미

- 힘이 크게 줄고 방향 결정을 미루는 상태다.

#### Response 해석

- `indecision_cluster`
- `Barrier` 또는 `State` 감점용 후보

---

### Tweezer Top

#### 모양

- 비슷한 고점에서 두 번 막힌다.

#### 의미

- 상단에 매도 대기 물량이 있다는 뜻이다.

#### 실전 해석

- 저항 확인 패턴으로 자주 본다.

#### Response 해석

- `bear_reject_candle`
- `resistance_reject_down`

---

### Tweezer Bottom

#### 모양

- 비슷한 저점에서 두 번 받친다.

#### 의미

- 하단에 매수 방어가 있다는 뜻이다.

#### Response 해석

- `bull_reject_candle`
- `support_hold_up`

---

## 3개 캔들 패턴

### Morning Star

#### 구조

```text
큰 음봉
작은 캔들
큰 양봉
```

#### 의미

- 하락 힘이 약해지고 매수가 되돌리는 구조다.

#### 실전 해석

- 하락 말단 반전 패턴으로 강하다.
- 마지막 양봉 확인이 중요하다.

#### Response 해석

- `bull_reversal_3bar`
- `support_hold_up`
- 또는 `mid_reclaim_up`

---

### Evening Star

#### 구조

```text
큰 양봉
작은 캔들
큰 음봉
```

#### 의미

- 상승 힘이 약해지고 매도가 우위를 가져오는 구조다.

#### Response 해석

- `bear_reversal_3bar`
- `resistance_reject_down`
- 또는 `mid_lose_down`

---

### Three White Soldiers

#### 구조

```text
강한 양봉
강한 양봉
강한 양봉
```

#### 의미

- 매수가 계속 우위라는 뜻이다.
- 반전 확인 또는 지속 강화로 본다.

#### 실전 해석

- 저점 반전 뒤 나오면 매우 강하다.
- 이미 많이 오른 곳이면 추격 리스크를 같이 봐야 한다.

#### Response 해석

- `bull_break_body`
- `mid_reclaim_up`
- `resistance_break_up`

---

### Three Black Crows

#### 구조

```text
강한 음봉
강한 음봉
강한 음봉
```

#### 의미

- 매도가 계속 우위라는 뜻이다.

#### Response 해석

- `bear_break_body`
- `mid_lose_down`
- `support_break_down`

---

## 실전에서 특히 많이 보는 핵심 패턴

### 반등 / 매수 쪽

- Hammer
- Dragonfly Doji
- Bullish Engulfing
- Morning Star
- Tweezer Bottom

### 하락 / 매도 쪽

- Shooting Star
- Gravestone Doji
- Bearish Engulfing
- Evening Star
- Tweezer Top

### 지속 / 돌파 쪽

- Bullish Marubozu
- Bearish Marubozu
- Three White Soldiers
- Three Black Crows

### 애매함 / 대기 쪽

- Doji
- Long-legged Doji
- Spinning Top
- Harami
- Harami Cross

---

## 진짜 먹히는 조건

### 1. 위치보다 반응이 먼저가 아니다

캔들은 반응이지, 위치 자체는 아니다.

즉 캔들이 아무리 좋아 보여도

- 하락 중간
- 애매한 횡보 중간
- 유동성 없는 구간

에서는 의미가 약해진다.

---

### 2. 꼬리 길이와 몸통 힘이 중요하다

- 하단 반등 캔들은 아래 꼬리가 길어야 한다.
- 상단 거절 캔들은 위 꼬리가 길어야 한다.
- 돌파 캔들은 몸통이 강해야 한다.

즉 `반전`은 꼬리, `지속`은 몸통이 중요하다.

---

### 3. 다음 캔들 확인이 중요하다

예를 들어:

- Hammer만 보고 바로 매수
- Doji만 보고 바로 반전 확정

이건 위험하다.

보통은

- Hammer 후 양봉
- Shooting Star 후 음봉
- Engulfing 후 유지

같은 확인이 붙을 때 훨씬 의미가 커진다.

---

### 4. 거래량이 붙으면 의미가 커진다

거래량은 현재 Response raw에 직접 안 들어가 있지만,
실전 의미로는 매우 중요하다.

- 꼬리 + 거래량 증가 = 흡수 가능성 강화
- 장악형 + 거래량 증가 = 방향 전환 신뢰도 강화
- 돌파 몸통 + 거래량 증가 = continuation 가능성 강화

---

## 시스템에 넣을 때의 묶음

이 20개를 20개 raw로 그대로 넣기보다,
먼저 기능별로 묶는 것이 더 좋다.

### 1. 하단 reject 계열

- Hammer
- Inverted Hammer
- Dragonfly Doji
- Tweezer Bottom

이 묶음은 보통 `bull_reject_candle`로 본다.

---

### 2. 상단 reject 계열

- Hanging Man
- Shooting Star
- Gravestone Doji
- Tweezer Top

이 묶음은 보통 `bear_reject_candle`로 본다.

---

### 3. 2봉 반전 계열

- Bullish Engulfing
- Bearish Engulfing

이 묶음은

- `bull_reversal_2bar`
- `bear_reversal_2bar`

로 나눠서 본다.

---

### 4. 3봉 반전 계열

- Morning Star
- Evening Star

이 묶음은

- `bull_reversal_3bar`
- `bear_reversal_3bar`

로 나눈다.

---

### 5. 지속 몸통 계열

- Bullish Marubozu
- Bearish Marubozu
- Three White Soldiers
- Three Black Crows

이 묶음은

- `bull_break_body`
- `bear_break_body`

쪽으로 연결하기 좋다.

---

### 6. 애매함 계열

- Doji
- Long-legged Doji
- Spinning Top
- Harami
- Harami Cross

이 묶음은 직접 매수/매도 방향 점수를 올리기보다

- `indecision_candle`
- `indecision_cluster`

같은 식으로 따로 빼는 게 더 낫다.

---

## Response 기준으로 다시 묶으면

### support_hold_up 쪽에 들어가기 쉬운 캔들

- Hammer
- Inverted Hammer
- Dragonfly Doji
- Bullish Engulfing
- Morning Star
- Tweezer Bottom

---

### support_break_down 쪽에 들어가기 쉬운 캔들

- Bearish Marubozu
- Three Black Crows

---

### resistance_reject_down 쪽에 들어가기 쉬운 캔들

- Hanging Man
- Shooting Star
- Gravestone Doji
- Bearish Engulfing
- Evening Star
- Tweezer Top

---

### resistance_break_up 쪽에 들어가기 쉬운 캔들

- Bullish Marubozu
- Three White Soldiers

---

### 방향 애매함으로 따로 둬야 하는 캔들

- Doji
- Long-legged Doji
- Spinning Top
- Harami
- Harami Cross

---

## 캔들 -> Response 6축 기여표

이 섹션은 `현재 코드 구현`이 아니라,
앞으로 캔들을 `Response 6축`에 연결할 때 쓰는 설계 기준표다.

핵심은 이렇다.

- 캔들 이름을 그대로 최종 점수로 쓰지 않는다.
- 캔들은 각 축의 `가산 근거`, `감산 근거`, `애매함 패널티`로 들어간다.
- 같은 캔들이라도 위치와 이전 흐름에 따라 기여 축이 달라질 수 있다.

즉 아래 표는
`이 패턴이 일반적으로 어느 축을 밀어주기 쉬운가`
를 정리한 것이다.

---

### 축 의미 다시 보기

| 축 | 쉬운 뜻 |
|---|---|
| `lower_hold_up` | 하단에서 받치고 위로 가려는 반응 |
| `lower_break_down` | 하단이 깨지고 아래로 밀리는 반응 |
| `mid_reclaim_up` | 중심선을 다시 회복하며 위로 가려는 반응 |
| `mid_lose_down` | 중심선을 잃고 아래로 밀리는 반응 |
| `upper_reject_down` | 상단에서 거절당하고 아래로 내려오려는 반응 |
| `upper_break_up` | 상단을 돌파하고 위로 확장하려는 반응 |

---

### 단일 캔들 기여표

| 패턴 | 1차 기여 축 | 2차 기여 축 | 반대 축에 주는 영향 | 비고 |
|---|---|---|---|---|
| Hammer | `lower_hold_up` | `mid_reclaim_up` | `lower_break_down` 감산 | 하락 말단일수록 강함 |
| Inverted Hammer | `lower_hold_up` | `mid_reclaim_up` | `lower_break_down` 약감산 | 반드시 다음 봉 확인 필요 |
| Hanging Man | `upper_reject_down` | `mid_lose_down` | `upper_break_up` 감산 | 상승 말단일 때만 의미 큼 |
| Shooting Star | `upper_reject_down` | `mid_lose_down` | `upper_break_up` 감산 | 상단 reject 대표 패턴 |
| Dragonfly Doji | `lower_hold_up` | 없음 | `lower_break_down` 감산 | 강한 하단 reject 성격 |
| Gravestone Doji | `upper_reject_down` | 없음 | `upper_break_up` 감산 | 강한 상단 reject 성격 |
| Bullish Marubozu | `upper_break_up` | `mid_reclaim_up` | `upper_reject_down` 감산 | 강한 몸통 돌파 |
| Bearish Marubozu | `lower_break_down` | `mid_lose_down` | `lower_hold_up` 감산 | 강한 몸통 붕괴 |
| Doji | 없음 | 없음 | 모든 방향 축 약감산 | `indecision_candle` 쪽 |
| Long-legged Doji | 없음 | 없음 | 모든 방향 축 감산 | 변동성 크지만 합의 없음 |
| Spinning Top | 없음 | 없음 | 모든 방향 축 약감산 | 힘 균형, 대기 신호 |

---

### 2봉 패턴 기여표

| 패턴 | 1차 기여 축 | 2차 기여 축 | 반대 축에 주는 영향 | 비고 |
|---|---|---|---|---|
| Bullish Engulfing | `lower_hold_up` | `mid_reclaim_up` | `lower_break_down`, `mid_lose_down` 감산 | 하단/지지에서 강함 |
| Bearish Engulfing | `upper_reject_down` | `mid_lose_down` | `upper_break_up`, `mid_reclaim_up` 감산 | 상단/저항에서 강함 |
| Harami | 없음 | 없음 | 방향 축 약감산 | 감속, 확인 대기용 |
| Harami Cross | 없음 | 없음 | 방향 축 감산 | indecision 강함 |
| Tweezer Top | `upper_reject_down` | 없음 | `upper_break_up` 감산 | 같은 고점에서 두 번 막힘 |
| Tweezer Bottom | `lower_hold_up` | 없음 | `lower_break_down` 감산 | 같은 저점에서 두 번 받침 |

---

### 3봉 패턴 기여표

| 패턴 | 1차 기여 축 | 2차 기여 축 | 반대 축에 주는 영향 | 비고 |
|---|---|---|---|---|
| Morning Star | `lower_hold_up` | `mid_reclaim_up` | `lower_break_down`, `mid_lose_down` 감산 | 3봉 반전 확인 구조 |
| Evening Star | `upper_reject_down` | `mid_lose_down` | `upper_break_up`, `mid_reclaim_up` 감산 | 3봉 하락 반전 확인 |
| Three White Soldiers | `upper_break_up` | `mid_reclaim_up` | `upper_reject_down` 감산 | 상승 지속/강한 회복 |
| Three Black Crows | `lower_break_down` | `mid_lose_down` | `lower_hold_up` 감산 | 하락 지속/강한 붕괴 |

---

### 묶음 기준으로 다시 보면

| 묶음 | 포함 패턴 | 주로 올리는 축 |
|---|---|---|
| `bull_reject_candle` | Hammer, Inverted Hammer, Dragonfly Doji, Tweezer Bottom | `lower_hold_up` |
| `bear_reject_candle` | Hanging Man, Shooting Star, Gravestone Doji, Tweezer Top | `upper_reject_down` |
| `bull_reversal_2bar` | Bullish Engulfing | `lower_hold_up`, `mid_reclaim_up` |
| `bear_reversal_2bar` | Bearish Engulfing | `upper_reject_down`, `mid_lose_down` |
| `bull_reversal_3bar` | Morning Star | `lower_hold_up`, `mid_reclaim_up` |
| `bear_reversal_3bar` | Evening Star | `upper_reject_down`, `mid_lose_down` |
| `bull_break_body` | Bullish Marubozu, Three White Soldiers | `upper_break_up`, `mid_reclaim_up` |
| `bear_break_body` | Bearish Marubozu, Three Black Crows | `lower_break_down`, `mid_lose_down` |
| `indecision_candle` | Doji, Long-legged Doji, Spinning Top, Harami, Harami Cross | 직접 가산보다 감산/대기 |

---

### 축별로 보면 어떤 캔들이 들어가나

#### `lower_hold_up`

강하게 올릴 수 있는 패턴:

- Hammer
- Inverted Hammer
- Dragonfly Doji
- Bullish Engulfing
- Morning Star
- Tweezer Bottom

보조로 올릴 수 있는 패턴:

- Three White Soldiers
- Bullish Marubozu

깎을 수 있는 패턴:

- Bearish Marubozu
- Three Black Crows
- Doji 계열

#### `lower_break_down`

강하게 올릴 수 있는 패턴:

- Bearish Marubozu
- Three Black Crows

보조로 올릴 수 있는 패턴:

- Bearish Engulfing
- Evening Star

깎을 수 있는 패턴:

- Hammer
- Dragonfly Doji
- Bullish Engulfing
- Morning Star

#### `mid_reclaim_up`

강하게 올릴 수 있는 패턴:

- Bullish Engulfing
- Morning Star
- Three White Soldiers

보조로 올릴 수 있는 패턴:

- Hammer
- Inverted Hammer
- Bullish Marubozu

깎을 수 있는 패턴:

- Bearish Engulfing
- Evening Star
- Doji/Harami 계열

#### `mid_lose_down`

강하게 올릴 수 있는 패턴:

- Bearish Engulfing
- Evening Star
- Three Black Crows

보조로 올릴 수 있는 패턴:

- Shooting Star
- Hanging Man
- Bearish Marubozu

깎을 수 있는 패턴:

- Bullish Engulfing
- Morning Star
- Doji/Harami 계열

#### `upper_reject_down`

강하게 올릴 수 있는 패턴:

- Shooting Star
- Gravestone Doji
- Hanging Man
- Bearish Engulfing
- Evening Star
- Tweezer Top

보조로 올릴 수 있는 패턴:

- Three Black Crows

깎을 수 있는 패턴:

- Bullish Marubozu
- Three White Soldiers

#### `upper_break_up`

강하게 올릴 수 있는 패턴:

- Bullish Marubozu
- Three White Soldiers

보조로 올릴 수 있는 패턴:

- Bullish Engulfing
- Morning Star

깎을 수 있는 패턴:

- Shooting Star
- Gravestone Doji
- Bearish Engulfing
- Evening Star

---

### 점수 형태는 어떻게 잡나

캔들 패턴은 `최종 점수`가 아니라
각 축에 대한 `기여 점수`로 보는 것이 좋다.

예를 들면:

```text
lower_hold_up
= bull_reject_candle
+ bull_reversal_2bar * 0.8
+ bull_reversal_3bar * 0.9
+ bull_break_body * 0.2
- bear_break_body * 0.6
- indecision_candle * 0.3
```

```text
upper_reject_down
= bear_reject_candle
+ bear_reversal_2bar * 0.8
+ bear_reversal_3bar * 0.9
+ bear_break_body * 0.2
- bull_break_body * 0.6
- indecision_candle * 0.3
```

여기서 중요한 건:

- `반등 패턴`은 reversal 축에 크게
- `지속 몸통 패턴`은 break 축에 크게
- `애매함 패턴`은 방향 점수 가산보다 감산

이 방향으로 가야 한다는 점이다.

---

### 실전에서 특히 중요한 점

같은 패턴도 무조건 같은 축에 1:1로 박으면 안 된다.

예를 들어:

- Hammer는 보통 `lower_hold_up`
- 그런데 위치가 상단 끝이라면 좋은 신호가 아닐 수 있다.

- Bullish Engulfing은 보통 `lower_hold_up` 또는 `mid_reclaim_up`
- 그런데 이미 많이 오른 뒤라면 `upper_break_up` continuation 성격으로 읽힐 수도 있다.

즉 캔들 패턴은
`고정 정답`보다
`기본 기여 축 + 위치에 따른 재해석`
구조로 보는 것이 더 안전하다.

---

## 현재 코드와 비교하면

지금 코드의 캔들 raw는 아주 단순하다.

현재는 사실상 아래 두 개만 직접 있다.

- `candle_lower_reject`
- `candle_upper_reject`

즉 현재 구현은

- 하단 reject 계열
- 상단 reject 계열

정도만 직접 읽고 있고,

- 장악형
- 별형
- soldiers/crows
- doji/harami 애매함

이런 것들은 아직 직접 raw로 안 읽고 있다.

즉 앞으로 캔들을 확장하려면
`패턴 이름을 그대로 늘리기`보다
위에서 정리한 `기능 묶음` 기준으로 늘리는 것이 더 안정적이다.

---

## 정리

캔들은 단독 진입 시스템이 아니라 `반응 해석 언어`로 보는 것이 좋다.

이 문서 기준으로 보면:

- 꼬리 계열은 reject
- 장악형/별형은 reversal
- Marubozu / Soldiers / Crows는 break or continuation
- Doji / Harami / Spinning Top은 indecision

즉 앞으로 `Response` 확장은

1. 패턴 이름 수를 늘리는 방식보다
2. 기능 묶음을 먼저 만들고
3. 그 묶음을 `support_hold_up`, `resistance_reject_down` 같은 축으로 연결하는 방식

으로 가는 것이 가장 자연스럽다.
