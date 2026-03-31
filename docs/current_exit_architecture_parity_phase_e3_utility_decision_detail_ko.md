# 청산 구조 정렬 Phase E3 상세

작성일: 2026-03-29 (KST)
현재 상태: E3 완료, exit utility decision owner separation core implemented

## 1. E3가 맡는 일

E3의 목표는 `WaitEngine.evaluate_exit_utility_decision(...)`를
entry / wait 때와 같은 수준으로 owner별로 분리하는 것이다.

한 문장으로 줄이면 아래와 같다.

`청산 utility decision을 base utility, recovery utility, scene bias, reverse eligibility, final winner/taxonomy owner로 나눈다.`


## 2. 왜 지금 E3가 필요한가

E2를 통해 청산 wait state는 이미

- 입력 계약
- base state policy
- rewrite policy
- surface contract

로 분리됐다.

즉 이제 `청산 상태가 왜 그런가`는 꽤 잘 읽힌다.

하지만 아직 `그래서 왜 hold / wait_exit / reverse_now / exit_now가 됐는가`
는 한 함수 안에서 크게 만들어지고 있다.

지금 구조는 아래와 같은 비대칭 상태다.

- state 쪽은 분리되기 시작함
- decision 쪽은 아직 한 함수가 너무 많은 의미를 가짐

그래서 E3는 청산 쪽에서 entry / wait parity를 이어가기 위한 다음 본체다.


## 3. 현재 evaluate_exit_utility_decision이 실제로 하는 일

현재 본문은 아래 층을 한 번에 다 맡고 있다.

### 3-1. utility input 해석

- profit, peak profit, giveback, duration
- adverse risk, score gap
- regime / box / bb 위치
- entry direction
- wait state metadata
- recovery policy 관련 제한값


### 3-2. base utility 계산

- exit now utility
- hold utility
- reverse utility
- wait-exit utility

이 네 값을 직접 만든다.


### 3-3. state bias 기반 utility 조정

- aligned with entry
- countertrend with entry
- prefer hold through green
- prefer fast cut

같은 bias가 utility를 직접 가감한다.


### 3-4. scene / symbol / setup 특례 조정

- range middle observe hold bias
- opposite edge completion bias
- lower reversal hold bias
- XAU lower edge-to-edge hold bias
- BTC upper tight protect exit bias
- BTC lower hold bias
- BTC lower mid noise hold bias
- NAS upper hold bias

같은 것들이 utility를 다시 조정한다.


### 3-5. recovery utility / reverse eligibility

- u_cut_now
- u_wait_be
- u_wait_tp1
- u_reverse
- allow wait BE / TP1
- prefer reverse
- reverse min prob / hold seconds / gap

같은 recovery / reverse 관련 utility와 gate를 같이 만든다.


### 3-6. 최종 winner / reason / taxonomy 연결

마지막에는

- winner 선택
- decision reason 선택
- wait-selected 여부
- taxonomy 생성

까지 한 번에 끝낸다.

즉 E3 시점의 문제는 명확하다.

`청산 decision이 이제 recent summary로는 잘 보이는데, 그 decision의 owner 경계는 아직 두껍다.`


## 4. E3가 끝나면 어떤 구조가 되어야 하나

E3가 끝나면 청산 decision은 아래 흐름으로 읽혀야 한다.

1. canonical decision input을 읽는다.
2. base utility bundle이 1차 점수를 만든다.
3. recovery utility bundle이 recovery 계열 후보를 만든다.
4. scene / symbol / setup bias bundle이 utility를 조정한다.
5. reverse eligibility resolver가 reverse 가능 여부를 고정한다.
6. final winner resolver가 winner / reason / selected를 만든다.
7. taxonomy builder가 의미 표면을 만든다.

즉 `청산 wait state 이후 decision layer`도
`입력 -> base -> overlay -> final surface`
구조로 바뀌어야 한다.


## 5. E3를 어떻게 나눌 것인가

E3는 크게 4개 묶음으로 보는 것이 좋다.

## E3-1. Exit Utility Input / Base Bundle Freeze

### 목표

base utility 계산에 들어가는 입력과 1차 utility 결과를 contract로 고정한다.

### 여기서 다룰 것

- locked profit
- upside / giveback cost / reverse edge
- wait improvement / wait miss cost
- base utility 4종
  - exit now
  - hold
  - reverse
  - wait exit

### 추천 파일

- `backend/services/exit_utility_input_contract.py`
- `backend/services/exit_utility_base_bundle.py`

### 완료 기준

`evaluate_exit_utility_decision(...)`이 더 이상 base utility 숫자를 본문에서 직접 만들지 않는다.


## E3-2. Recovery Utility / Reverse Eligibility 분리

### 목표

recovery utility와 reverse gate를 별도 owner로 뺀다.

### 여기서 다룰 것

- u_cut_now
- u_wait_be
- u_wait_tp1
- u_reverse
- allow wait BE / TP1
- tight protect green peak disable
- reverse min prob / hold seconds / gap
- reverse eligible 여부

### 추천 파일

- `backend/services/exit_recovery_utility_bundle.py`
- `backend/services/exit_reverse_eligibility_policy.py`

### 완료 기준

recovery / reverse 후보의 생성과 차단 이유가 utility owner로 분리되어 있다.


## E3-3. Symbol / Setup Special Bias 분리

### 목표

scene-specific utility 조정을 별도 owner bundle로 뺀다.

### 여기서 다룰 것

- range middle hold relief
- opposite edge completion exit boost
- lower reversal hold bias
- XAU lower edge-to-edge hold bias
- BTC upper support bounce exit bias
- BTC lower hold bias
- BTC lower mid noise hold bias
- NAS upper hold bias
- tight protect generic green protection bias

### 추천 파일

- `backend/services/exit_utility_scene_bias_policy.py`

### 완료 기준

scene bias가 더 이상 utility 본문 안에 흩어져 있지 않고,
하나의 bundle 결과로 관리된다.


## E3-4. Final Winner / Decision Surface 분리

### 목표

최종 winner 선택과 decision reason, wait-selected, taxonomy 연결을 별도 owner로 뺀다.

### 여기서 다룰 것

- positive/green path winner selection
- negative/recovery path winner selection
- priority rules
- decision reason mapping
- wait-selected / wait-decision mapping
- taxonomy input shaping

### 추천 파일

- `backend/services/exit_utility_decision_policy.py`

### 완료 기준

최종 decision이 `utility candidates -> winner policy -> taxonomy` 순서로 읽힌다.


## 6. E3에서 특히 조심할 것

### 첫째, recovery utility와 final winner를 한 번에 섞지 말 것

recovery utility는 후보 생성 owner다.
final winner는 선택 owner다.

이 둘을 다시 한 파일에서 섞으면 E3의 의미가 약해진다.


### 둘째, symbol/setup bias를 recovery utility 안에 넣지 말 것

BTC, XAU, NAS 특례와 lower/upper reversal 특례는
recovery base logic가 아니라 scene bias layer다.

이걸 recovery utility 파일 안에 섞으면 다시 큰 함수가 된다.


### 셋째, taxonomy는 마지막 단계에서만 만들 것

taxonomy는 decision surface이지,
utility 계산 owner가 아니다.

즉 utility owner들은 숫자와 후보를 만들고,
마지막 단계에서만 taxonomy에 연결하는 편이 좋다.


## 7. 테스트는 어떻게 잠가야 하나

E3는 direct helper 테스트와 기존 통합 회귀를 같이 가져가야 한다.

### direct helper 테스트 후보

- base utility bundle direct test
- recovery utility bundle direct test
- reverse eligibility direct test
- scene bias direct test
- final winner policy direct test

### 기존 회귀와 연결해야 할 테스트

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_trading_application_runtime_status.py`


## 8. E3 완료 선언 조건

E3는 아래가 충족되면 완료로 볼 수 있다.

1. base utility 숫자 생성이 분리되어 있다.
2. recovery utility / reverse eligibility가 분리되어 있다.
3. scene bias bundle이 분리되어 있다.
4. final winner / decision reason 선택이 분리되어 있다.
5. taxonomy 연결이 마지막 layer로 정리되어 있다.
6. direct helper 테스트와 기존 회귀가 모두 녹색이다.


## 9. 가장 먼저 시작할 실제 순서

가장 자연스러운 시작점은 `E3-1`이다.

이유는 명확하다.

- base utility bundle이 먼저 얼어야
- recovery utility와 scene bias가 그 위에 쌓일 수 있고
- 마지막 winner policy도 같은 언어로 선택할 수 있다

즉 다음 실제 구현 순서는 아래가 좋다.

1. `exit_utility_input_contract.py`
2. `exit_utility_base_bundle.py`
3. `E3-1 direct test`
4. 그다음 `E3-2`로 이동
