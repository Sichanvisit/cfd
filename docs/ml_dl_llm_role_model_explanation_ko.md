# ML / DL / LLM 역할 분류와 사고방식 정리

## 문서 목적
이 문서는 현재 CFD 구조에서 `ML`, `DL`, `LLM`을 어떻게 분류해서 생각해야 하는지,  
그리고 왜 `ML`과 `DL`이 서로 대체 관계가 아니라 **같이 쓸 수도 있는 구조**인지 설명하기 위한 문서입니다.

특히 아래 질문에 답하는 것이 목적입니다.

- `ML`은 정확히 무엇을 학습하는가
- `DL`은 정확히 무엇을 학습하는가
- `ML`이 먼저이고 `DL`은 더 발전된 버전이라고 보면 되는가
- 왜 둘을 같이 쓸 수도 있는가
- 각각 무엇이 필요한가
- `LLM`은 왜 “두뇌”라고 생각할 수 있지만, live core는 아닌가

---

## 먼저 한 줄 핵심

지금 구조에서 가장 정확한 분류는 이겁니다.

- **ML** = 한 시점의 semantic snapshot을 보고 미래 outcome을 예측하는 모델
- **DL** = 여러 시점의 semantic snapshot sequence를 보고 미래 outcome을 예측하는 모델
- **LLM** = 그 예측과 시장 상태를 해석/설명/감독하는 관찰자

즉:
- ML은 **정적인 의미 상태**
- DL은 **시간 흐름이 포함된 의미 상태**
- LLM은 **설명과 감독**

입니다.

---

## 1. 네가 지금 잡고 있는 직관은 어느 정도 맞지만, 조금 수정이 필요하다

네가 지금 느끼는 직관은 대략 이렇습니다.

### 직관 1
`ML`은

```text
Position
-> Response
-> State
-> Evidence
-> Belief
-> Barrier
```

을 보고,

“어떤 자리에서 어떤 결과가 잘 나왔는지”
를 학습하는 것 같다

### 직관 2
`DL`은

```text
Forecast Features
-> Transition Forecast / Trade Management Forecast
```

에서 나온 미래 예측을 다시 학습하는 것 같다

이 직관은 **반은 맞고 반은 수정해야 합니다.**

---

## 2. 가장 정확한 구분

## ML은 무엇을 학습하나
ML은 보통 **한 시점의 semantic snapshot**을 입력으로 사용합니다.

즉 한 row 기준으로:

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

또는 이걸 묶은:

- `ForecastFeaturesV1`

을 보고,

그 시점 이후의 미래 결과를 학습합니다.

즉 ML은:

**“이 순간 상태가 이럴 때, 이후 어떤 outcome이 자주 나왔는가”**

를 배우는 모델입니다.

### ML의 가장 좋은 사고방식
ML은

**semantic snapshot classifier / regressor**

로 생각하는 게 가장 정확합니다.

---

## DL은 무엇을 학습하나
DL은 보통 **최근 N개 시점의 semantic snapshot 흐름(sequence)** 을 입력으로 사용합니다.

예:
- 최근 5 bars
- 최근 10 bars
- 최근 20 bars

의

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

또는 이걸 묶은 semantic feature sequence를 봅니다.

즉 DL은:

**“지금 이 순간 값이 얼마냐”보다,  
“최근 몇 개 시점 동안 이 값들이 어떻게 변해왔느냐”**

를 배우는 모델입니다.

### DL의 가장 좋은 사고방식
DL은

**semantic sequence model**

로 생각하는 게 가장 정확합니다.

---

## 3. 가장 중요한 정정: DL이 Forecast를 배우는 건 아니다

여기서 많이 헷갈릴 수 있는데,  
`DL`이 `Forecast` 결과 자체를 배우는 게 본질은 아닙니다.

정확히는:

- `ML`도 `Forecast`를 직접 배우는 게 아니라
  - semantic snapshot -> outcome
  를 학습합니다
- `DL`도 `Forecast`를 직접 배우는 게 아니라
  - semantic sequence -> outcome
  를 학습합니다

즉 둘 다 본질적으로는 **forecast 생성기**입니다.

다만 차이는:

- ML은 snapshot 기반
- DL은 sequence 기반

입니다.

`TransitionForecast`와 `TradeManagementForecast`는  
나중에 ML/DL이 내야 할 **출력 계약**입니다.

즉 DL은 `Forecast`를 입력으로 배우는 게 아니라,
**semantic feature sequence를 입력으로 받아 `Forecast contract`를 출력하게 만드는 것**에 가깝습니다.

---

## 4. 그럼 ML과 DL의 입력은 어떻게 다르냐

## ML 입력
한 시점 row

예:
- `position_primary_label`
- `position_bias_label`
- `position_conflict_score`
- `response_vector_v2`
- `state_vector_v2`
- `evidence_vector_v1`
- `belief_state_v1`
- `barrier_state_v1`

즉:

```text
현재 semantic snapshot 한 장
```

## DL 입력
여러 시점 sequence

예:

```text
t-9 semantic snapshot
t-8 semantic snapshot
t-7 semantic snapshot
...
t semantic snapshot
```

즉:

```text
최근 N개의 semantic snapshot 흐름
```

---

## 5. 왜 ML과 DL을 같이 쓸 수 있나

핵심은 둘이 “이전 단계 / 다음 단계”만의 관계가 아니라,  
**서로 다른 강점을 가진 예측기**라는 점입니다.

## ML이 강한 점
- 데이터가 비교적 적어도 시작 가능
- 빠름
- 안정적
- 설명 가능성이 높음
- feature importance 보기 좋음
- baseline으로 쓰기 좋음

## DL이 강한 점
- 시간 흐름을 더 잘 봄
- delayed continuation
- persistence drift
- fake break 후 재전개
- regime transition
같은 sequence 패턴을 더 잘 잡음

즉 둘은:
- ML = static semantic understanding
- DL = temporal semantic understanding

으로 볼 수 있습니다.

### 같이 쓰는 가장 좋은 형태

```text
Semantic Foundation
-> ForecastFeaturesV1
-> ML Forecast
-> DL Forecast
-> Forecast Selector / Ensemble
-> Observe / Confirm / Action
```

즉:
- ML은 baseline / anchor
- DL은 time-flow specialist

처럼 같이 쓸 수 있습니다.

---

## 6. 그렇다고 무조건 ML 다음에 DL로 가야 하는 건 아니다

이건 매우 중요합니다.

**ML은 단계일 수도 있지만, 최종 해법일 수도 있습니다.**

왜냐면 지금 구조는 이미 semantic engineering이 많이 되어 있기 때문입니다.

즉 모델은 raw 차트를 처음부터 배우는 게 아니라,
이미 사람이 해석한 feature를 입력으로 받습니다.

이런 구조에서는 종종:
- tabular ML만으로도 충분히 성능이 좋고
- explainability도 좋고
- 운영도 쉽고
- latency도 안정적입니다

그래서:

- ML이 먼저
- DL은 필요할 때만

이 더 정확한 사고방식입니다.

즉:
**ML -> DL은 자동 진화가 아니라, 필요성 기반 확장**입니다.

---

## 7. 그럼 언제 DL이 필요하다고 판단하나

DL이 필요한 순간은 보통 이런 경우입니다.

### 1) snapshot 정보만으로는 부족할 때
현재 한 시점 semantic state만으로는 예측이 약한데,
최근 5~20 bars의 흐름을 같이 보면 잘 맞을 때

### 2) 시간이 핵심일 때
예:
- continuation이 천천히 형성되는 패턴
- fake break 뒤 재전개
- belief가 흔들리다가 다시 살아나는 패턴

### 3) 충분한 데이터가 있을 때
DL은 보통:
- 더 많은 데이터
- 더 좋은 라벨
- 더 안정적인 replay/dataset

가 필요합니다.

즉 DL은:
**sequence 정보가 정말 가치 있을 때만 가는 게 맞습니다.**

---

## 8. 이 구조에서 ML에 필요한 것

ML을 제대로 하려면 최소한 아래가 필요합니다.

### 1. semantic foundation
- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

### 2. feature packaging
- `ForecastFeaturesV1`

### 3. outcome labels
- `OutcomeLabeler`

예:
- `buy_confirm_success_label`
- `false_break_label`
- `continue_favor_label`
- `fail_now_label`

### 4. dataset builder
- semantic snapshot
- forecast snapshot
- outcome label
를 한 row로 묶는 builder

### 5. validation / shadow compare
- rule baseline과 실제 비교
- ML 예측과 실제 비교

즉 ML에는:

**좋은 snapshot feature + 좋은 label + 비교 기준 baseline**

이 필요합니다.

---

## 9. 이 구조에서 DL에 필요한 것

DL은 ML보다 요구사항이 더 많습니다.

### 1. semantic snapshot sequence
예:
- 최근 10개 snapshot
- 최근 20개 snapshot

### 2. sequence window 정의
예:
- 몇 bars를 볼 것인가
- bar 간격이 일정한가
- missing data를 어떻게 처리할 것인가

### 3. 같은 label contract
DL도 결국
- `TransitionForecast`
- `TradeManagementForecast`

와 같은 contract를 내야 합니다.

### 4. 더 많은 데이터
DL은 대체로:
- 더 많은 샘플
- 더 긴 기간
- 더 안정적인 라벨

이 필요합니다.

### 5. replay reproducibility
sequence를 만들려면 replay가 안정적이어야 합니다.

즉 DL에는:

**semantic sequence + stable labeling + 충분한 데이터량**

이 필요합니다.

---

## 10. LLM은 왜 “두뇌” 같지만 같은 계층이 아닌가

`LLM`은 성격이 다릅니다.

### LLM이 하는 데 좋은 일
- 시장 상황을 말로 설명
- semantic layer와 forecast를 읽고 요약
- forecast disagreement 설명
- anomaly / regime shift 경고
- calibration report 해석
- 실패 사례 정리
- 개선안 제안

### LLM이 하면 안 되는 일
- 실시간 deterministic forecast core 대체
- `BUY/SELL` 직접 생성
- `archetype_id` 뒤집기
- action gate 직접 제어

즉 LLM은:

**예측 엔진**이 아니라  
**관찰자 / 설명자 / 감독자 / 리서치 보조 두뇌**

로 붙는 게 가장 좋습니다.

---

## 11. 가장 추천하는 연결 구조

지금 구조에서 가장 자연스러운 형태는 이겁니다.

```text
Semantic Foundation
-> ForecastFeaturesV1
-> Rule Forecast
-> ML Forecast
-> DL Forecast
-> Forecast Selector / Shadow Compare
-> Observe / Confirm / Action
-> Consumer

Offline:
semantic snapshots
+ forecast snapshots
-> OutcomeLabeler
-> Validation / Dataset / Model Training
-> LLM Analysis
```

이 구조에서:
- Rule = baseline
- ML = 첫 실전 모델
- DL = sequence specialist
- LLM = 분석/설명/개선

으로 역할이 나뉩니다.

---

## 12. 지금 네가 어떻게 생각하면 가장 좋은가

가장 추천하는 사고방식은 아래입니다.

### 잘못된 분류
- ML은 foundation 학습
- DL은 forecast 학습

### 더 정확한 분류
- **ML은 semantic snapshot 기반 forecast**
- **DL은 semantic sequence 기반 forecast**
- **LLM은 forecast/semantic 해석 보조**

즉 둘 다 결국 forecast를 만드는데,
입력 구조와 강점이 다릅니다.

---

## 13. 최종 요약

지금 구조에서:

- `ML`
  - 한 시점 semantic snapshot을 보고 미래 결과를 예측하는 모델
- `DL`
  - 여러 시점 semantic snapshot 흐름을 보고 미래 결과를 예측하는 모델
- `LLM`
  - 그 예측과 상태를 설명하고 관찰하고 감독하는 보조 두뇌

그리고 가장 중요한 점은:

**ML은 반드시 DL로 넘어가기 위한 임시 단계가 아닙니다.**  
지금처럼 semantic foundation이 잘 정리된 구조에서는  
**ML이 최종 실전 해법이 될 수도 있고, DL은 sequence 정보가 정말 필요할 때만 추가하는 확장 옵션**이라고 보는 게 맞습니다.
