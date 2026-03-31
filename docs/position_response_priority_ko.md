# Position-First / Response-Second 우선순위 규칙

## 목적

이 문서는 현재 CFD 엔진에서 진입/청산 위치가 흐려지는 문제를 줄이기 위해,
`Position`과 `Response`의 우선순위를 다시 고정하기 위한 기준 문서다.

핵심은 간단하다.

- `Position`은 "지금 어디에 있나"를 가장 먼저 고정한다.
- `Response`는 "그 위치에서 무엇이 나오나"를 그 다음에 본다.
- 다른 보조 라벨은 이 두 축을 흐리게 하면 안 된다.

---

## 가장 중요한 1차 원칙

현재 위치 해석의 최우선 기준은 아래 두 개다.

1. 박스 위치
2. 볼린저 밴드 위치

다른 라벨은 있어도 되지만,
이 두 개보다 우선순위가 높아지면 안 된다.

---

## Position의 1차 의미

### 박스 기준

- 박스 하단이면 `BUY` 쪽 위치 에너지
- 박스 상단이면 `SELL` 쪽 위치 에너지

즉 박스는 "현재 어느 쪽 끝에 더 가까운가"를 가장 직접적으로 말해주는 기준이다.

### 볼린저 밴드 기준

- 상단선 근처면 `SELL` 쪽 위치 에너지
- 상단 돌파면 `BUY` continuation 후보
- 하단선 근처면 `BUY` 쪽 위치 에너지
- 하단 돌파면 `SELL` continuation 후보

즉 볼린저는 단순 위치와, break 여부를 함께 구분하는 기준이다.

---

## Position과 Response의 역할 분리

### Position이 소유하는 질문

- 지금 lower / middle / upper 중 어디인가
- 중심에서 얼마나 멀어졌는가
- 위치 에너지가 어느 쪽으로 얼마나 쏠렸는가

### Response가 소유하는 질문

- lower에서 hold/reclaim이 나오는가
- upper에서 reject가 나오는가
- 상단을 break했는가
- 하단을 breakdown 했는가

즉:

- `Position = 장소`
- `Response = 그 장소에서 나타나는 반응`

이다.

---

## 운영상 해석 규칙

### 1. lower에 있다고 해서 무조건 BUY는 아니다

lower는 먼저 "buy 쪽 위치 에너지"를 의미한다.

하지만 실제 진입은:

- lower에서 hold/reclaim이 나오는지
- 하단을 깨고 더 밀리는지

를 `Response`에서 확인해야 한다.

즉:
- lower + hold/reclaim -> `BUY` reversal 후보
- lower + breakdown -> `SELL` continuation 후보

### 2. upper에 있다고 해서 무조건 SELL은 아니다

upper는 먼저 "sell 쪽 위치 에너지"를 의미한다.

하지만 실제 진입은:

- upper에서 reject가 나오는지
- 상단을 break해서 continuation이 나오는지

를 `Response`에서 확인해야 한다.

즉:
- upper + reject -> `SELL` reversal 후보
- upper + breakout -> `BUY` continuation 후보

### 3. 중심에서 멀수록 위치 에너지는 강해야 한다

이건 매우 중요하다.

중심에서 멀어질수록:

- 위치 에너지가 강해지고
- lower / upper 해석의 자신감이 올라가야 한다.

반대로 중심 근처면:

- middle
- bias
- unresolved

가 더 많이 허용되어야 한다.

### 4. 중심에 있을수록 판단 비중은 뒤 레이어로 넘긴다

이 원칙은 아주 중요하다.

중심 부근에서는 `Position`이 해야 할 일은:

- 강한 방향 확정이 아니라
- `middle / neutral / unresolved / weak bias`
- 그리고 "아직 위치만으로는 결론이 약하다"는 신호를 주는 것

이다.

즉 중심에서는 아래 레이어들의 판단 비중이 더 커져야 한다.

- `Response Raw`
- `Response Vector`
- `State Vector`
- `Evidence`
- `Belief`
- `Barrier`

의미를 풀면 이렇다.

- `Position`은 중심 부근에서는 방향 owner가 아니라 위치 owner로만 남는다
- 실제 진입 방향은 반응과 상태와 증거가 더 많이 결정한다
- barrier도 중심 구간에서는 더 중요한 설명층이 된다

즉:

- `edge zone`에서는 `Position` 비중이 크고
- `middle zone`에서는 `Response/State/Evidence/...` 비중이 커진다

이 구조가 맞다.

---

## 현재 엔진에서 바로 적용해야 할 우선순위

### Priority 1. 박스/볼린저 기반 위치 에너지

반드시 먼저 본다.

이 단계에서 결정되는 것:

- `lower / middle / upper`
- 위치 에너지 강도
- 중심 대비 거리 감각

단, 중심 구간에서는 이 단계가 "강한 방향 확정"까지 가져가면 안 된다.

중심에서는 이 단계의 역할이 아래처럼 줄어들어야 한다.

- `middle인지`
- `어느 쪽 bias가 아주 약하게 있는지`
- `아직 unresolved로 남겨야 하는지`

### Priority 2. break / reject / reclaim / hold

그 다음 본다.

이 단계에서 결정되는 것:

- reversal 후보인지
- continuation 후보인지

특히 중심 구간에서는 이 단계의 영향이 커져야 한다.

즉 중심에서는:

- 위치보다 반응
- 장소보다 전이

가 더 중요해진다.

### Priority 3. 보조 컨텍스트

그 다음 본다.

예:

- MA
- SR
- trendline
- 기타 보조 라벨

이 값들은:

- context
- confidence modulation
- 설명 보강

에는 쓰일 수 있지만,
박스/볼린저가 만든 1차 위치 해석을 덮어쓰면 안 된다.

---

## 지금 문제를 어떻게 봐야 하나

현재 "어디서 진입/청산해야 하는지 불명확하다"는 느낌은,
대체로 아래 중 하나에서 발생한다.

### 경우 A. Position이 위치 자체를 너무 빨리 확정

예:

- 아직 middle-lower 정도인데 `ALIGNED_LOWER_WEAK`로 너무 빨리 고정

이 경우는 `T1-1 Position` 문제다.

### 경우 B. Position은 맞는데 Response 없이 바로 방향으로 연결

예:

- lower라는 이유만으로 바로 `BUY`가 강해짐

이 경우는 `Position -> Evidence` 연결이 과민하거나,
`Response`의 역할이 충분히 반영되지 않는 문제다.

### 경우 C. 보조 라벨이 1차 위치 해석을 흐림

예:

- MA/SR/trendline이 박스/볼린저 위치보다 더 큰 영향을 줌

이 경우는 owner 우선순위 문제다.

---

## 실무 수정 순서

### Step 1. Position을 더 단순하게 본다

먼저 아래만 보고 해석이 맞는지 본다.

- `x_box`
- `x_bb20`
- `x_bb44`
- 중심 대비 거리

중심에 가까우면 여기서 강한 side를 만들지 않는 쪽이 우선이다.

### Step 2. secondary axis는 context로만 본다

아래 값들은 일단 설명용으로만 쓴다.

- `x_ma20`
- `x_ma60`
- `x_sr`
- `x_trendline`

즉 secondary axis가 primary location을 덮지 못하게 한다.

### Step 3. 진입 방향은 Position만으로 확정하지 않는다

진입 방향은:

- 위치 에너지
- 반응 종류

의 결합으로 본다.

특히 중심에서는 사실상 아래처럼 본다.

- `Position` = 방향 힌트 약함
- `Response` = 더 중요
- `State/Evidence/Belief/Barrier` = 방향/대기 판정 강화

즉:
- `Position`은 lower/upper bias를 준다
- `Response`는 reversal/continuation 방향을 확정한다

### Step 4. Position이 먼저, Response가 둘째, 나머지는 뒤

앞으로 모든 튜닝은 이 우선순위를 유지한다.

---

## 코드 기준 해석

현재 코드 기준으로 보면:

- `Position`은 `builder.py`, `interpretation.py`
- `Response`는 response engine
- `Evidence`는 두 결과를 합성

구조로 가야 맞다.

특히 `Evidence`에서 Position fit를 줄 때,
"박스/볼린저 기반 위치"가 가장 먼저 들어가고,
보조 컨텍스트는 그다음 약하게 들어가야 한다.

---

## 앞으로의 튜닝 기준

앞으로 케이스를 볼 때는 먼저 아래 질문만 본다.

1. 지금 위치는 박스 기준으로 lower / middle / upper 중 무엇인가
2. 지금 위치는 볼린저 기준으로 lower / middle / upper 중 무엇인가
3. 중심에서 얼마나 멀어졌는가
4. 그 위치에서 hold/reclaim/reject/break 중 무엇이 나왔는가

그리고 중심에 가까울수록 아래 질문이 더 중요해진다.

5. 지금 반응이 실제로 reversal인지 continuation인지
6. state가 이 반응을 얼마나 강화/감쇠하는지
7. evidence가 어느 쪽 setup을 더 강하게 만드는지
8. belief/barrier가 지금 enter보다 wait를 더 설득력 있게 만드는지

이 네 질문으로 먼저 설명되지 않는 경우에만
다른 보조 라벨을 본다.

---

## 한 줄 원칙

`박스와 볼린저 기반 위치 에너지가 항상 1순위이지만, 중심에 가까울수록 Position은 방향을 약하게 말하고 Response/State/Evidence/Belief/Barrier가 더 많이 판단하도록 넘겨야 하며, 나머지 보조 라벨은 이 구조를 보강만 해야 한다.`
