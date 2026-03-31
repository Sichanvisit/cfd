# CFD 시스템에서 ML / DL / LLM 연결 구조 정리

## 문서 목적
이 문서는 현재 CFD 시스템을 왜 이렇게 레이어별로 나눴는지,  
그리고 이 구조가 앞으로 `ML / DL / LLM` 연결까지 어떻게 확장되는지를 한국어 기준으로 한 번에 이해할 수 있게 정리한 문서입니다.

핵심 질문은 이것입니다.

- 왜 `Position / Response / State / Evidence / Belief / Barrier`까지 따로 만들었는가
- 왜 `Forecast`를 별도 계층으로 두는가
- `ML`은 어디에 붙는가
- `DL`은 어디에 붙는가
- `LLM`은 어디에 붙는가
- 무엇은 live 코어이고, 무엇은 offline 분석층인가

이 문서는 현재 구현 상태를 해석하는 관점과, 앞으로의 확장 방향을 같이 설명합니다.

---

## 한 줄 핵심

현재 구조는 단순 규칙 전략이 아니라,

**사람이 설계한 semantic foundation 위에 rule forecast를 먼저 올리고,  
그 위를 나중에 ML / DL forecast로 교체할 수 있게 만든 구조**입니다.

그리고 `LLM`은 이 live forecast 코어를 대체하는 게 아니라,  
**분석 / 설명 / 개선 루프를 돕는 바깥 레이어**로 붙는 게 맞습니다.

---

## 전체 구조

```text
시장 데이터
-> Context 정규화
-> Position
-> Response Raw
-> Response Vector
-> State Vector
-> Evidence
-> Belief
-> Barrier
-> Forecast Features
-> Forecast Engine (Rule / ML / DL)
-> Observe / Confirm / Action
-> Consumer

오프라인 병렬 경로:
Semantic + Forecast Snapshot
-> OutcomeLabeler
-> Validation Report / Replay Dataset
-> Model Training / Shadow Compare
-> LLM 기반 분석 / 리포트 / 개선안
```

이 구조는 크게 두 갈래입니다.

1. 실시간 의사결정 경로
- semantic foundation
- forecast engine
- lifecycle decision
- consumer

2. 오프라인 검증/학습 경로
- semantic snapshot
- forecast snapshot
- outcome label
- validation / dataset / model / LLM analysis

---

## 1. Semantic Foundation이 왜 중요한가

현재 시스템의 바닥은 다음 6개 레이어입니다.

- `Position`
- `Response`
- `State`
- `Evidence`
- `Belief`
- `Barrier`

이 6개는 앞으로도 유지되는 **semantic foundation**입니다.

### 의미
- 현재 상태를 사람이 이해 가능한 의미로 정리합니다
- raw OHLC나 raw detector를 그대로 모델에 넣지 않게 해줍니다
- 향후 rule / ML / DL forecast가 모두 같은 feature layer를 사용하게 합니다

### 중요한 원칙
- 이 레이어는 직접 최종 행동을 만들지 않습니다
- 이 레이어는 “현재 상태를 설명”하는 역할입니다
- 앞으로는 큰 재구성보다 bug fix / acceptance 보정 정도만 하는 것이 맞습니다

### 왜 이게 ML/DL에 유리한가
만약 이 레이어가 없으면, 모델은 raw 데이터에서
- 위치 의미
- 반응 의미
- 장 상태 의미
- 구조 장벽 의미

를 전부 처음부터 배워야 합니다.

지금 구조에서는 이미
- 위치는 `Position`
- 반응은 `Response`
- 해석 강도는 `State`
- 즉시 증거는 `Evidence`
- 누적 확신은 `Belief`
- 구조 장벽은 `Barrier`

로 정리되어 있기 때문에,  
모델은 **의미가 붙은 feature 공간**에서 더 빨리, 더 안정적으로 학습할 수 있습니다.

---

## 2. Forecast를 별도 계층으로 두는 이유

`Forecast`는 semantic foundation과 최종 행동 사이의 예측층입니다.

즉:
- semantic foundation = 현재 상태 설명
- forecast = 다음에 어떤 시나리오가 유력한지 예측
- OCA = 그래서 지금 무엇을 할지 결정

이 구분이 중요합니다.

### Forecast가 하는 일
- `TransitionForecast`
  - confirm / false break / reversal / continuation 쪽 예측
- `TradeManagementForecast`
  - hold / fail / recover / tp1 / re-entry 쪽 예측

### Forecast가 하지 않는 일
- raw detector 재해석
- 직접 `BUY/SELL ACTION` 생성
- consumer 실행

즉 Forecast는 `정책 결정기`가 아니라 **예측 인터페이스**입니다.

---

## 3. Rule Forecast를 먼저 만드는 이유

현재는 `ForecastRuleV1`가 baseline입니다.

이건 임시 땜빵이 아니라, 앞으로 model forecast와 비교할 **공식 기준선**입니다.

### Rule Forecast의 역할
- semantic feature -> scenario score
- 설명 가능
- 디버깅 가능
- calibration 가능
- model과 shadow compare 가능

### 왜 이게 필요하나
모델이 들어왔을 때,
- 정말 rule보다 낫나?
- 특정 심볼에서만 좋아진 거 아닌가?
- fake break를 더 잘 잡나?

를 비교하려면 baseline이 필요합니다.

즉:
- `Rule Forecast`
  = 비교 기준
- `ForecastModelV1`
  = 나중에 들어올 ML baseline
- `ForecastSequenceModelV2`
  = 그 이후 DL/시계열 모델

---

## 4. ML은 어디에 들어오는가

`ML`은 semantic foundation 위의 **forecast engine 구현체**로 들어옵니다.

즉 구조는 그대로 두고,

```text
Forecast Engine
= Rule Forecast 또는 ML Forecast
```

가 됩니다.

### 좋은 형태
- 입력:
  - `ForecastFeaturesV1`
- 출력:
  - `TransitionForecastV1`
  - `TradeManagementForecastV1`

즉 모델도 같은 contract를 내야 합니다.

### 첫 번째 ML 추천
지금 구조에서는 tabular ML이 가장 잘 맞습니다.

예:
- LightGBM
- XGBoost
- CatBoost

이유:
- 현재 feature 구조가 해석 가능한 structured feature라서
- tabular 모델이 baseline을 만들기 좋습니다

### ML이 live에서 하는 역할
- rule forecast 대신 같은 입력을 받고
- 같은 출력 contract를 냅니다
- OCA는 rule이든 model이든 같은 contract만 읽으면 됩니다

---

## 5. DL은 어디에 들어오는가

`DL`은 semantic foundation을 버리는 게 아니라,  
semantic snapshot의 **시계열(sequence)** 를 읽는 forecast 구현체로 들어옵니다.

예:
- 최근 N개 bar의
  - `Evidence`
  - `Belief`
  - `Barrier`
  - `Position/Response/State` 요약
를 시퀀스로 입력

### DL이 잘하는 부분
- delayed continuation
- persistence drift
- fake break 뒤 재돌파
- confirmation이 천천히 누적되는 패턴

### 권장 순서
DL은 tabular ML 이후가 맞습니다.

이유:
- 먼저 tabular baseline이 있어야 비교가 됩니다
- 처음부터 sequence 모델로 들어가면
  - feature 문제인지
  - 데이터셋 문제인지
  - 모델 문제인지
  구분하기 어렵습니다

### DL이 들어와도 안 바뀌는 것
- semantic foundation
- forecast output contract
- outcome label contract

즉 내부 구현만 바뀌고, 외부 계약은 유지해야 합니다.

---

## 6. LLM은 어디에 들어오는가

여기가 제일 자주 오해되는 부분입니다.

`LLM`은 실시간 deterministic decision core에 들어가는 게 아닙니다.

### LLM이 잘 들어가는 위치
- 실패 패턴 분석
- forecast calibration 해석
- validation report 요약
- 어떤 archetype이 왜 자꾸 망가지는지 설명
- feature importance 해석 보조
- 다음 실험안/개선안 제안
- 장문의 로그를 읽고 구조적으로 요약

### LLM이 들어가면 안 되는 위치
- 실시간 `BUY/SELL` action gate
- 숫자 안정성이 필요한 live forecast score 계산
- 매 루프 deterministic 출력이 필요한 core decision

즉:
- `ML / DL`
  = live forecast core 후보
- `LLM`
  = analysis / explanation / iteration support

이게 맞는 역할 분리입니다.

---

## 7. OutcomeLabeler가 왜 ML/DL에 핵심인가

`OutcomeLabeler`는 현재 forecast를 **나중에 채점하는 오프라인 엔진**입니다.

이게 있어야:
- 현재 rule forecast가 맞았는지 검증 가능
- management forecast가 실제로 유효한지 검증 가능
- 나중에 ML/DL 학습용 라벨을 만들 수 있음

### 역할
- semantic snapshot + forecast snapshot을 기준으로
- 미래 N bars / 미래 포지션 결과를 보고
- “그 당시 forecast가 맞았는지” 라벨을 부여

### 이것이 없으면
- forecast는 만들어도 검증이 약함
- management forecast는 특히 제대로 못 닫음
- ML/DL은 학습해도 라벨 품질이 불안정해짐

즉 OutcomeLabeler는
- 보고서용 부가 기능이 아니라
- **학습 가능 구조의 핵심 기반**입니다

---

## 8. 왜 Labeling / Dataset / Shadow Compare가 따로 필요한가

ML/DL까지 생각하면 forecast 다음에 아래 세 층이 꼭 필요합니다.

### 1) OutcomeLabeler
- forecast를 미래 결과 기준으로 채점

### 2) ReplayDatasetBuilder
- semantic snapshot
- forecast snapshot
- outcome label
를 한 row로 묶어 dataset 생성

### 3) Shadow Compare
- rule forecast
- model forecast
- 실제 outcome
를 같은 contract로 비교

이 세 개가 있어야:
- “모델이 좋아 보인다”가 아니라
- “rule baseline보다 실제로 낫다”를 말할 수 있습니다

---

## 9. 현재 구조가 ML/DL/LLM 준비 측면에서 맞는 이유

현재 구조는 아래 장점이 있습니다.

### 1. semantic foundation이 이미 feature engineering 역할을 함
모델이 raw 데이터를 처음부터 해석할 필요가 줄어듭니다.

### 2. forecast contract가 고정돼 있음
rule이든 model이든 같은 출력으로 비교 가능

### 3. outcome labeler가 오프라인 채점층으로 분리돼 있음
live decision과 validation이 섞이지 않음

### 4. consumer와 semantic layer 책임이 분리돼 있음
모델이 들어와도 실행층을 다 갈아엎지 않아도 됨

### 5. LLM을 core 대신 analysis 쪽으로 보낼 수 있음
실시간 안정성을 해치지 않고 생산성을 높일 수 있음

즉 지금 구조는 “복잡해서 과한 것”이 아니라,  
**ML/DL/LLM까지 가려면 오히려 필요한 분해**에 가깝습니다.

---

## 10. 앞으로의 확장 순서

지금 구조를 기준으로 하면 가장 자연스러운 순서는 이렇습니다.

### 1단계
- semantic foundation 유지
- forecast calibration 계속 보정
- outcome label 품질 강화

### 2단계
- `Forecast -> Observe / Confirm / Action` 번역층 완성
- consumer가 다시 해석하지 않게 정리

### 3단계
- outcome label validation report 안정화
- replay dataset builder 정리

### 4단계
- `ForecastModelV1` 추가
- rule forecast와 shadow compare

### 5단계
- tabular ML baseline 채택 여부 판단

### 6단계
- sequence DL 모델 검토

### 7단계
- LLM을 분석/리포트/개선 루프에 붙이기

---

## 11. 하지 말아야 하는 것

이 구조를 유지하려면 몇 가지는 피해야 합니다.

### 피해야 할 것
- semantic foundation을 자꾸 다시 뜯는 것
- symbol 예외를 계속 쌓아 model 전환을 어렵게 만드는 것
- raw detector를 OCA나 consumer가 다시 직접 읽는 것
- ML보다 먼저 DL로 바로 가는 것
- LLM을 live action core로 넣는 것

### 유지해야 할 것
- semantic foundation은 feature layer
- forecast는 예측 인터페이스
- OCA는 정책/lifecycle
- consumer는 실행
- outcome labeler는 채점

---

## 12. 최종 요약

현재 구조는

```text
Semantic Foundation
-> Forecast
-> Observe / Confirm / Action
-> Consumer

오프라인 병렬 경로:
Semantic + Forecast
-> OutcomeLabeler
-> Dataset / Validation / Model / LLM Analysis
```

로 이해하는 것이 맞습니다.

핵심 구분:
- `semantic foundation`
  = 현재 상태를 사람이 이해 가능한 의미로 정리
- `forecast`
  = 다음 시나리오 예측
- `OCA`
  = 지금 무엇을 할지 결정
- `consumer`
  = 실제 실행
- `outcome labeler`
  = 나중에 그 예측이 맞았는지 채점
- `ML / DL`
  = forecast 구현체
- `LLM`
  = 분석/설명/개선 보조

한 줄로 정리하면,

**지금까지 만든 구조는 ML/DL/LLM까지 확장하려고 할 때 오히려 필요한 기반 구조이고,  
앞으로는 semantic foundation을 유지한 채 forecast와 labeler를 중심으로 모델 친화적 구조를 완성해 가는 방향이 맞습니다.**
