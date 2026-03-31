# Semantic Ablation Playbook (KO)

## 목적

현재처럼 `Position / Response / State / Evidence / Belief / Barrier`가 한꺼번에 작동하면,

- 어디서 side가 잘못 붙었는지
- 어디서 너무 이르게 진입이 확정됐는지
- 어느 레이어가 과하게 덮어쓰는지

를 분리해서 보기 어렵다.

그래서 앞으로는 `한 번에 다 맞추기`보다, 아래처럼 **레이어를 순차적으로 켜는 방식**으로 검증한다.

이 문서에서는 이 과정을 `semantic ablation`이라고 부른다.

---

## 핵심 원칙

| 항목 | 원칙 |
|---|---|
| 기본 원칙 | 한 번에 전체를 맞추지 말고, owner가 맞는지부터 분해해서 본다 |
| 시작점 | `Position`부터 본다 |
| 중요한 주의 | `Position-only`는 **실거래 진입 엔진**이 아니라 **위치 판정 검증 모드**로 봐야 한다 |
| 이유 | `Position`은 어디 있는지를 말하는 레이어이지, 최종 트리거를 단독으로 확정하는 레이어가 아니다 |
| 검증 방식 | 라이브 진입보다 `observe/shadow/log` 기준이 우선이다 |
| 목표 | 각 레이어가 자기 역할만 하는지 확인하고, 그 다음에 합친다 |

---

## 왜 Position부터 보나

| 이유 | 설명 |
|---|---|
| 가장 바닥 의미 | `Position`은 “지금 어디냐”를 정한다 |
| 오판 전파 방지 | 위치가 틀리면 뒤 레이어가 다 맞아도 진입이 꼬인다 |
| 스크린샷 친화적 | 차트를 보고 사람 판단과 직접 비교하기 쉽다 |
| 기준 고정 | 하단/상단/중앙 기준이 먼저 고정돼야 Response와 State가 안 흔들린다 |

---

## 가장 중요한 오해 방지

| 잘못된 접근 | 왜 문제인가 |
|---|---|
| `Position만 켜고 실제 진입을 보자` | Position alone은 trigger owner가 아니다 |
| `Position이 BUY/SELL을 단독 확정해야 한다` | 그러면 Response의 역할이 사라진다 |
| `Position-only에서 수익성까지 보자` | 그 단계는 semantic correctness 검증 단계이지 수익 검증 단계가 아니다 |

즉 `Position-only`에서 확인해야 하는 것은:

- 이 자리가 상단/하단/중앙으로 맞게 읽히는가
- 기본 side seed가 맞는가
- middle에서 과하게 확정하지 않는가

이지,

- 실제 체결이 잘 되는가
- 수익이 좋은가

가 아니다.

---

## 현재 코드상 레이어 기본 모드

현재 `layer_mode` 계약상 기본 모드는 아래와 같다.

| 레이어 | 현재 기본 모드 | 의미 |
|---|---|---|
| `Position` | `enforce` | 구조상 가장 강하게 반영되는 층 |
| `Response` | `enforce` | 실제 트리거 후보이므로 강하게 반영 |
| `State` | `assist` | 환경/레짐 필터 중심 |
| `Evidence` | `enforce` | 세팅 강도 합산 층 |
| `Belief` | `shadow` | 현재는 보조/로그 성격이 강함 |
| `Barrier` | `shadow` | 현재는 보조/로그 성격이 강함 |
| `Forecast` | `shadow` | 현재는 보조/가이드 성격이 강함 |

참고:

- 현재 `layer_mode` 인프라는 이미 존재한다.
- 다만 현 시점 런타임은 `bridge_ready_no_runtime_delta` 상태라서,
- “레이어를 껐다 켠다”가 곧바로 완전한 실거래 런타임 스위치로 연결되지는 않는다.

즉 지금 당장 가장 현실적인 방식은:

- **실거래 직접 on/off**
  보다는
- **observe/shadow/replay 기준의 단계별 검증**

이다.

---

## 권장 검증 순서

| 단계 | 켜둘 레이어 | 이 단계에서 보는 것 | 보면 안 되는 것 |
|---|---|---|---|
| `A1` | `Position` | 위치 해석, side seed, edge/middle authority | 최종 진입/청산 성능 |
| `A2` | `Position + Response` | 위치 위에서 실제 반응이 맞게 읽히는가 | persistence나 risk suppression까지 한 번에 판단 |
| `A3` | `Position + Response + State` | trend/range/shock 환경에서 반응 해석이 맞는가 | 수익성 최적화 |
| `A4` | `+ Evidence` | reversal/continuation 근거 합산이 자연스러운가 | 세부 실행 guard 탓으로 돌리기 |
| `A5` | `+ Belief` | 한두 봉 noise와 지속 신호가 구분되는가 | archetype 재정의 |
| `A6` | `+ Barrier` | 막아야 할 자리를 제대로 막는가 | side 자체를 새로 만드는 것 |

---

## 단계별 질문

### A1. Position-only

| 질문 | 통과 기준 |
|---|---|
| 상단/하단/중앙이 사람 눈과 대체로 맞는가 | 스크린샷 기준 납득 가능 |
| box/band 양끝에서 기본 side seed가 맞는가 | 상단이면 기본 `SELL`, 하단이면 기본 `BUY` |
| middle에서 성급한 확정이 줄었는가 | `bias` 또는 `unresolved`가 적절히 남음 |
| edge에서 에너지가 강해지는가 | 중심보다 끝단에서 stronger label/energy |

### A2. Position + Response

| 질문 | 통과 기준 |
|---|---|
| lower에서 hold/reclaim은 `BUY` 후보가 되는가 | yes |
| lower break는 `SELL` 후보가 되는가 | yes |
| upper reject는 `SELL` 후보가 되는가 | yes |
| upper breakout은 `BUY` 후보가 되는가 | yes |
| global lower 안의 local upper reject를 잡는가 | yes |

### A3. + State

| 질문 | 통과 기준 |
|---|---|
| range에서는 reversal 의미가 더 살아나는가 | yes |
| trend에서는 pullback/continuation이 더 자연스러운가 | yes |
| shock/noise에서는 과한 확정이 줄어드는가 | yes |

### A4. + Evidence

| 질문 | 통과 기준 |
|---|---|
| Position/Response/State가 합쳐졌을 때 근거가 과장되지 않는가 | 동일 의미 중복 가산이 적음 |
| 사람이 보기엔 애매한데 total evidence가 과하지 않은가 | yes |
| 사람이 보기엔 명확한데 total evidence가 너무 약하지 않은가 | yes |

### A5. + Belief

| 질문 | 통과 기준 |
|---|---|
| 한 봉 반짝 신호를 너무 믿지 않는가 | yes |
| 좋은 방향 우세가 몇 봉 지속되면 confidence가 누적되는가 | yes |
| side/archetype을 새로 바꾸지 않는가 | yes |

### A6. + Barrier

| 질문 | 통과 기준 |
|---|---|
| middle chop / conflict / liquidity bad 구간을 막는가 | yes |
| 이미 좋은 side를 새로 뒤집지는 않는가 | yes |
| 막는 이유가 설명 가능한가 | yes |

---

## 추천 운영 방식

### 1. Position-only live entry는 하지 말고, Position-only observe로 본다

| 구분 | 추천 |
|---|---|
| `Position-only 실거래` | 비추천 |
| `Position-only 스크린샷 검증` | 추천 |
| `Position-only watcher/log 검증` | 강력 추천 |

이 단계에서 남겨야 하는 핵심 로그:

- `primary_label`
- `bias_label`
- `raw_alignment_label`
- `box_zone`
- `bb20_zone`
- `bb44_zone`
- `upper_position_force`
- `lower_position_force`
- `middle_neutrality`

### 2. 첫 실전 진입 검증은 `Position + Response`부터 본다

이 조합이 사실상 “첫 번째 실제 side candidate”다.

즉:

- `Position`이 큰 지도
- `Response`가 local trigger

이 둘이 맞아야 비로소 “왜 BUY/SELL인지”가 차트에서 납득된다.

### 3. Belief / Barrier는 가장 나중에 얹는다

현재 문제는 “왜 여기가 BUY/SELL인지 모르겠다”가 핵심이다.

이 문제는 대체로:

- `Position`
- `Response`
- `State`
- `Evidence`

에서 많이 생긴다.

반면:

- `Belief`
- `Barrier`

는 이미 정해진 candidate를 유지하거나 막는 성격이 강하다.

그래서 너무 이르게 얹으면 원인 파악이 흐려진다.

---

## 실제 추천 로드맵

| 순서 | 실행 항목 | 목표 |
|---|---|---|
| `1` | `Position-only screenshot audit` | 위치 해석을 먼저 고정 |
| `2` | `Position-only watcher review` | 실제 런타임 row에서 위치 라벨 점검 |
| `3` | `Position + Response audit` | 로컬 반응이 side candidate를 맞게 만드는지 확인 |
| `4` | `+ State audit` | trend/range/shock 해석 보정 |
| `5` | `+ Evidence audit` | 점수 합산의 과장/과소 확인 |
| `6` | `+ Belief` | persistence 누적 확인 |
| `7` | `+ Barrier` | suppression 품질 확인 |

---

## 지금 상황에 맞는 현실적인 결론

| 질문 | 답 |
|---|---|
| `Position만 켜놓고 진입확인` 해볼까? | 방향은 맞다 |
| 그대로 live entry까지 가도 되나? | 아니다 |
| 그럼 어떻게 해야 하나? | `Position-only observe/shadow`로 시작해야 한다 |
| 그다음 첫 실전 후보는? | `Position + Response` |
| 그다음에 얹을 순서는? | `State -> Evidence -> Belief -> Barrier` |

---

## 한 줄 정리

> 지금은 `Position만 켜서 실제 매매`를 보려는 단계가 아니라,
> `Position만 먼저 분리해서 의미가 맞는지 확인하고`,
> 그 다음 `Response`부터 하나씩 얹어가며 owner를 검증해야 하는 단계다.

