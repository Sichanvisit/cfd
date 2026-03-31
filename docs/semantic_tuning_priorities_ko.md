# Semantic Tuning Priorities

## 왜 지금 이 단계가 중요한가

지금은 구조를 더 만드는 단계보다, 이미 만든 semantic layer를 정밀 보정해서:

- 좋은 학습 데이터를 만들고
- 안정적인 rule baseline을 유지하고
- 이후 ML/DL forecast가 배울 만한 상태 공간을 만드는 단계

로 보는 게 맞습니다.

핵심은 이렇습니다.

- `Position / Response / State`가 틀리면 feature 자체가 흔들립니다.
- `Evidence`가 틀리면 setup strength가 과하거나 약해집니다.
- `Barrier`가 틀리면 너무 자주 `WAIT` 하거나 반대로 막아야 할 곳을 못 막습니다.
- `Belief`가 틀리면 persistence 감각이 시장과 어긋납니다.

즉 지금의 튜닝은 단순 운영 보정이 아니라, 이후 학습 품질을 좌우하는 foundation 정리 작업입니다.

---

## 증상별로 어디를 먼저 봐야 하는가

| 증상 | 주 수정층 | 의미 |
| --- | --- | --- |
| 위치 해석 자체가 이상함 | `Position`, `Response`, `State` | 입력 feature 자체가 흔들리는 상태 |
| setup strength가 너무 약하거나 강함 | `Evidence` | semantic을 합성하는 방식이 과/소평가됨 |
| 눌림/충돌 때문에 너무 자주 `WAIT` 됨 | `Barrier`, `Layer Mode`, `Energy` | 진입 억제 구조가 과민하거나 잘못 연결됨 |
| persistence가 너무 빨리 죽거나 오래 감 | `Belief` | 시간축 누적 로직이 실제 시장 감각과 안 맞음 |

이 분류는 지금 구조 기준으로 정확합니다.

---

## 왜 이 순서로 봐야 하는가

### 1. `Position / Response / State`

이건 feature correctness 문제입니다.

여기가 흔들리면:

- `Evidence`는 잘못 합성하고
- `Belief`는 잘못 누적하고
- `Barrier`는 잘못 막고
- 결과적으로 ML도 잘못된 feature를 학습합니다.

즉 여기서의 수정은 좋은 데이터를 만들기 위한 필수 전처리 보정입니다.

#### 여기서 주로 보는 것

- `Position`
  - 좌표 경계
  - `bias / unresolved / conflict` 기준
- `Response`
  - detector -> canonical 매핑
  - `reject / break / reclaim / lose` 대칭성
- `State`
  - gain/damp가 실제 장 해석과 맞는지
  - legacy conflict/noise가 과하게 먹지 않는지

#### 원칙

- consumer guard나 energy hint로 덮지 않습니다.
- semantic foundation 자체를 먼저 바로잡습니다.

---

### 2. `Evidence`

이건 의미 해석의 합성 품질 문제입니다.

`Evidence`는 사실상:

- setup strength
- reversal vs continuation 강도

를 만드는 핵심층입니다.

여기가 과하거나 약하면 OCA 이전부터 방향성과 구조가 틀어집니다.

#### 여기서 주로 보는 것

- `lower_hold_up` vs `mid_reclaim_up` 비중
- `upper_reject_down` vs `mid_lose_down` 비중
- reversal / continuation capped merge
- position fit 강도
- state gain/damp 반영 강도

#### 원칙

- setup을 직접 건드리지 않습니다.
- `Evidence`가 archetype strength를 자연스럽게 만들도록 조정합니다.

---

### 3. `Barrier / Layer Mode / Energy`

이건 너무 자주 `WAIT` 되는 문제를 다루는 층입니다.

다만 여기서 가장 중요한 주의점이 있습니다.

`WAIT`이 많다고 해서 먼저 barrier를 풀어버리면, 사실은 upstream semantic이 틀린데도 action만 늘어납니다.

그래서 barrier는 semantic이 어느 정도 맞아진 다음에 건드리는 게 맞습니다.

#### 여기서 주로 보는 것

- `conflict_barrier`
- `middle_chop_barrier`
- `direction_policy_barrier`
- `liquidity_barrier`
- `Layer Mode` shadow/assist/enforce 영향도
- `Energy Helper`의 soft hint 강도

#### 원칙

- "`WAIT`이 많다"를 곧바로 barrier 문제로 단정하지 않습니다.
- 먼저 semantic conflict인지, barrier 과민인지 분리합니다.

---

### 4. `Belief`

이건 시간축 감각 보정입니다.

여기서 틀어지면:

- persistence가 너무 빨리 죽거나
- 반대로 너무 오래 가서

실제 체감이 완전히 이상해집니다.

#### 여기서 주로 보는 것

- EMA rise/decay
- activation threshold
- dominance deadband
- streak/persistence window
- mode switch 시 carry-over 규칙

#### 원칙

- `Belief`는 semantic layer가 어느 정도 안정된 뒤 만지는 게 좋습니다.
- 아니면 잘못된 evidence를 더 똑똑하게 누적하게 됩니다.

---

## ML 관점에서 왜 이 단계가 중요한가

지금 네가 실제로 하려는 건 단순 튜닝이 아니라:

> 모델이 배울 만한 상태 공간을 만든다

는 작업입니다.

즉 ML 관점에서는:

- `Position / Response / State` = feature correctness
- `Evidence` = feature synthesis correctness
- `Belief` = temporal summary correctness
- `Barrier` = execution friction correctness

이 네 개가 좋아야 나중에 ML이 배우는 것도:

> 이 좋은 상태 공간에서 어떤 outcome이 나왔는가

가 됩니다.

반대로 이게 안 맞으면 모델은:

- 잘못된 위치 해석
- 잘못된 합성 강도
- 잘못된 누적
- 잘못된 `WAIT` 억제

를 그대로 학습합니다.

즉 지금 단계는 튜닝이면서 동시에 데이터셋 품질 관리입니다.

---

## 추천 실행 순서

### Phase T1. Semantic correctness pass

대상:

- `Position`
- `Response`
- `State`

목표:

- 위치 해석
- 전이 해석
- gain/damp

를 먼저 안정화

### Phase T2. Evidence calibration pass

대상:

- `Evidence`

목표:

- archetype strength가 실제 차트 감각과 맞게 합성되도록 조정

### Phase T3. Barrier / LayerMode wait calibration

대상:

- `Barrier`
- `Layer Mode`
- `Energy`

목표:

- 너무 자주 `WAIT` 되는 문제를 해소하되 semantic을 망치지 않기

### Phase T4. Belief temporal calibration

대상:

- `Belief`

목표:

- persistence가 실제 시간 흐름 감각과 맞도록 보정

---

## 하지 말아야 하는 것

### 1. consumer guard로 덮기

upstream semantic이 틀렸는데

- entry/exit guard에서 막아버리면
- 데이터는 계속 오염됩니다.

### 2. energy hint만 만져서 해결하려 하기

`Energy`는 지금 helper/overlay 성격이지,
semantic truth source가 아닙니다.

### 3. symptom별로 여기저기 patch

예를 들어:

- `WAIT` 많으니 barrier 낮추고
- confirm 약하니 evidence 올리고
- fail 많으니 belief 늘리고

이렇게 동시에 하면 원인 추적이 안 됩니다.

---

## 지금 시점의 가장 현실적인 전략

### 먼저 해야 할 것

1. `Position / Response / State` acceptance 다시 점검
2. `Evidence` strength calibration
3. 그 다음 `Barrier` wait calibration
4. 마지막에 `Belief` 시간축 calibration

### 동시에 해야 할 것

- 각 단계별 shadow report 남기기
- 수정 전/후 outcome 비교 가능하게 유지
- version tag 남기기

예:

- `position_contract_v3`
- `response_mapper_v2_r4`
- `evidence_vector_v1_e5`
- `belief_state_v1_b4_tuned`

---

## 최종 정리

지금은 저 네 그룹의 세부 수정이 필요한 단계가 맞습니다.

다만 중요한 건:

> `Position / Response / State -> Evidence -> Barrier -> Belief`

순서로 차례대로 잡아야 하고,
consumer/energy로 덮는 방식은 최대한 뒤로 미뤄야 한다는 점입니다.

이 순서를 지켜야:

- 현재 live behavior도 안정화되고
- 이후 ML/DL용 feature quality도 좋아지고
- tuning 결과가 dataset quality 개선으로 이어집니다.
