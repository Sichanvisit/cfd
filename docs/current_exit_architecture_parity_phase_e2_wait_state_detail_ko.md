# 청산 구조 정렬 Phase E2 상세

작성일: 2026-03-29 (KST)
현재 상태: E1 완료 이후, E2-4 surface/metadata freeze 구현 완료

## 1. E2가 맡는 일

E2의 목표는 청산 wait state를
entry / wait에서 했던 것처럼
하나의 큰 본문이 아니라
몇 개의 분리된 owner로 재구성하는 것이다.

한 문장으로 쓰면 이렇다.

`WaitEngine의 exit wait state 빌더를 context adapter, state policy, state rewrite, surface contract로 나눈다.`


## 2. 왜 지금 E2가 필요한가

E1이 끝나면서 아래가 정리됐다.

- 기본 exit profile identity
- lifecycle posture adjustment
- recovery base policy
- state / belief / edge temperament overlay

즉 이제 청산 wait state는
정책 입력을 받아먹을 바닥이 어느 정도 정리된 상태다.

반대로 말하면,
이 다음 병목은 `build_exit_wait_state(...)` 자체다.

현재 이 함수는 여전히 아래를 한 번에 한다.

- exit manage context를 읽고 보정한다
- risk / market / identity 값을 풀어 쓴다
- recovery policy를 해석한다
- green close / recovery / reverse / cut-immediate 같은 state를 직접 판정한다
- state bias를 적용해 state를 다시 바꾼다
- metadata surface를 만든다

이걸 그대로 두면
청산은 최근 summary와 taxonomy는 좋아졌는데
정작 state 본문은 큰 함수 중심으로 남게 된다.


## 3. 현재 build_exit_wait_state가 실제로 하는 일

현재 청산 wait state 빌더는 크게 네 층을 한 함수 안에서 수행한다.

### 3-1. 입력 수집 층

이 층은 아래를 모은다.

- canonical exit manage context
- trade context fallback
- stage input fallback
- risk numbers
- regime / box / bb 위치
- entry direction
- state / belief payload

이 층의 문제는 “계산에 쓰는 입력”과 “표면에 남기기 위한 값”이 아직 분리되지 않았다는 점이다.


### 3-2. policy input 해석 층

이 층은 recovery policy에서 아래를 꺼낸다.

- wait BE 허용 여부
- wait TP1 허용 여부
- prefer reverse 여부
- recovery loss thresholds
- reverse score gap
- belief / symbol edge overlay 결과

즉 E1의 출력이 실제 wait state 조건문에 들어가는 지점이다.


### 3-3. state candidate 판정 층

이 층은 현재 장면을 보고 먼저 “기본 state 후보”를 정한다.

예를 들면 아래 장면들이다.

- opposite signal이 있지만 confirm이 아직 부족한 상태
- range middle에서 아직 바로 청산할 필요가 없는 상태
- breakeven recovery를 기다릴 수 있는 상태
- TP1 recovery를 기다릴 수 있는 상태
- reverse를 열어도 되는 상태
- 즉시 cut이 필요한 상태
- green close hold가 가능한 상태

이건 청산 wait state의 핵심 policy layer다.


### 3-4. state rewrite와 surface 층

이 층은 base state를 그대로 끝내지 않고
state / belief / symbol edge bias를 바탕으로 다시 바꾼다.

예를 들어

- green close를 그냥 hold로 둘지
- same-side confirmation이면 hold를 더 연장할지
- opposite belief 상승이면 recovery를 cut으로 내릴지
- symbol edge hold bias가 있으면 green close를 active로 완화할지

를 후처리한다.

그리고 마지막에

- score
- penalty
- hard_wait
- metadata

를 붙여 `WaitState`를 반환한다.


## 4. E2가 끝났을 때의 목표 형태

E2가 끝나면 청산 wait state는 아래 흐름으로 읽혀야 한다.

1. canonical exit manage context를 읽는다.
2. exit wait state input contract를 만든다.
3. base state policy가 state 후보를 만든다.
4. rewrite policy가 후보를 조정한다.
5. surface contract가 metadata / compact summary를 만든다.
6. WaitEngine은 이것들을 조합해 `WaitState`를 반환한다.

즉 WaitEngine은 점점
`청산 wait state를 직접 판단하는 곳`
이 아니라
`이미 분리된 판단 owner를 연결하는 곳`
이 되어야 한다.


## 5. E2를 어떻게 쪼개는가

E2는 네 조각으로 가는 것이 가장 안전하다.

## E2-1. Exit Wait State Input Freeze

### 목표

청산 wait state가 실제로 읽는 입력을 별도 contract로 얼린다.

### 이 단계에서 만들 것

- canonical exit manage context를 읽는 adapter
- risk / market / identity / policy input을 묶은 state input contract

### 추천 새 파일

- `backend/services/exit_wait_state_input_contract.py`

### 추천 함수

- `build_exit_wait_state_input_v1(...)`
- `compact_exit_wait_state_input_v1(...)`

### 완료 기준

WaitEngine이 긴 local variable 다발을 직접 조립하지 않고,
하나의 `exit_wait_state_input_v1`를 기준으로 state 판단을 시작한다.


## E2-2. Exit Wait State Policy Extraction

### 목표

기본 state 후보 판정을 별도 policy owner로 분리한다.

### 이 단계에서 다루는 것

- REVERSAL_CONFIRM
- ACTIVE
- RECOVERY_TP1
- RECOVERY_BE
- REVERSE_READY
- CUT_IMMEDIATE
- GREEN_CLOSE
- NONE

같은 base state 결정

### 추천 새 파일

- `backend/services/exit_wait_state_policy.py`

### 추천 함수

- `resolve_exit_wait_state_policy_v1(...)`

### 완료 기준

“현재 장면에서 기본 청산 wait state가 무엇인가”에 대한 답이
WaitEngine 밖의 단일 owner에 존재한다.


## E2-3. Exit Wait State Rewrite Extraction

### 목표

기본 state 후보를 bias로 조정하는 후처리를 별도 owner로 분리한다.

### 이 단계에서 다루는 것

- state bias 기반 green-close hold rewrite
- belief hold extension
- opposite belief fast-cut rewrite
- symbol edge hold rewrite
- recovery state에서 cut-immediate rewrite

### 추천 새 파일

- `backend/services/exit_wait_state_rewrite_policy.py`

### 추천 함수

- `apply_exit_wait_state_rewrite_v1(...)`

### 완료 기준

base state와 rewritten state가 개념적으로 분리되고,
왜 state가 바뀌었는지가 owner 기준으로 설명 가능해진다.


## E2-4. Exit Wait State Surface / Metadata Freeze

### 목표

청산 wait state metadata와 compact surface를 별도 contract로 정리한다.

### 이 단계에서 다루는 것

- score / penalty / hard_wait
- recovery thresholds
- applied policy ids
- rewritten reason
- compact state surface

### 추천 새 파일

- `backend/services/exit_wait_state_surface_contract.py`

### 추천 함수

- `build_exit_wait_state_surface_v1(...)`
- `compact_exit_wait_state_surface_v1(...)`

### 완료 기준

청산 wait state가 row / runtime / recent summary로 넘어갈 때
surface key가 더 안정적으로 관리된다.


## 6. E2에서 특히 조심할 점

### 첫째, base state와 rewrite를 섞지 말 것

이 둘을 분리하지 않으면
나중에 “왜 GREEN_CLOSE가 ACTIVE로 바뀌었는지”
또 다시 큰 함수 안으로 내려가야 한다.

### 둘째, E1의 recovery policy 경계를 다시 허물지 말 것

E2는 state policy를 정리하는 단계이지
recovery base policy를 다시 안으로 가져오는 단계가 아니다.

### 셋째, metadata key를 급하게 흔들지 말 것

청산 recent summary와 taxonomy가 이미 runtime surface에 올라와 있으므로
surface key를 불필요하게 재명명하지 않는 편이 좋다.


## 7. 테스트는 어떻게 잠가야 하나

E2는 direct helper 회귀와 기존 WaitEngine 회귀를 둘 다 써야 한다.

### E2-1 direct 회귀

- input contract가 trade context / stage input / exit manage context를 올바르게 결합하는지

### E2-2 direct 회귀

- reversal confirm scene
- recovery TP1 scene
- recovery BE scene
- reverse ready scene
- cut immediate scene
- green close scene

### E2-3 direct 회귀

- green close -> active hold rewrite
- recovery -> cut immediate rewrite
- belief hold extension
- symbol edge hold rewrite

### E2-4 회귀

- compact surface가 row/runtime에 그대로 남는지
- downstream taxonomy와 recent summary가 안 깨지는지

### 같이 붙여볼 기존 회귀

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_exit_wait_taxonomy_contract.py`
- `tests/unit/test_decision_models.py`
- `tests/unit/test_trading_application_runtime_status.py`


## 8. E2 완료 선언 조건

E2는 아래가 충족되면 완료로 본다.

1. 청산 wait state 입력 계약이 분리되어 있다.
2. base state policy owner가 분리되어 있다.
3. state rewrite owner가 분리되어 있다.
4. surface / metadata contract가 분리되어 있다.
5. WaitEngine exit wait state 빌더는 조합기 역할이 강해졌다.
6. direct helper 회귀가 각 층별로 존재한다.
7. exit taxonomy / recent runtime summary 회귀가 유지된다.


## 9. 가장 먼저 시작할 실제 작업

가장 먼저 할 것은 `E2-1`이다.

이유는 명확하다.

- 지금 함수 안의 local variable 다발을 먼저 얼려야
- base state policy extraction과 rewrite extraction이 안전해진다.

즉 다음 실제 작업 순서는 아래가 가장 좋다.

1. `exit_wait_state_input_contract.py` 추가
2. WaitEngine이 그 input contract를 쓰게 변경
3. direct helper 회귀 추가
4. 그 다음 E2-2로 이동
