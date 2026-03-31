# 기다림 구조정리 Phase W2-3 상세 문서

부제: state policy caller를 frozen wait context 기반으로 정리하기 위한 구현 가이드

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 `W2-3`를 실제로 구현하기 전에,
현재 `WaitEngine`이 `entry_wait_context_v1`와 `bias bundle`을 이미 가지고 있음에도
왜 아직 state policy caller가 충분히 정리되지 않았는지,
그리고 어떤 형태로 `state policy input contract`를 세워야 하는지를 상세하게 정리하기 위한 문서다.

W2-1은 wait 입력을 한 덩어리 context로 모으는 단계였고,
W2-2는 bias/helper caller를 그 context 위에서 묶는 단계였다.
W2-3은 그 다음 단계로,
`state policy`가 실제로 읽는 입력을 하나의 명시적 계약으로 고정하는 단계다.


## 2. 왜 W2-3가 필요한가

W2-2 이후 구조는 분명 좋아졌다.

- `entry_wait_context_v1`가 생겼다.
- bias helper 4종이 `bias bundle`로 묶였다.
- effective soft/hard threshold 계산이 bundle layer로 이동했다.
- compact context에도 bias bundle summary가 남기 시작했다.

하지만 `WaitEngine.build_entry_wait_state_from_row(...)`는 아직
context를 다시 펼쳐서 많은 로컬 변수로 바꾸고,
그 로컬 변수를 긴 인자 목록으로 `resolve_entry_wait_state_policy_v1(...)`에 넘긴다.

즉 지금 상태는 이렇게 요약할 수 있다.

> 입력 context는 얼려졌지만
> state policy 직전의 caller는 아직 flat argument 조립 단계에 머물러 있다.

이 구조는 당장 동작에는 문제가 없지만,
아래와 같은 불편을 남긴다.

- state policy가 실제로 무엇을 읽었는지 한 객체로 말하기 어렵다.
- replay/runtime/handoff에서 state policy 입력면만 따로 재현하기 어렵다.
- 나중에 state policy를 더 세분화할 때 `WaitEngine`의 caller 코드가 다시 커질 가능성이 있다.
- end-to-end 테스트에서 "이 row는 어떤 state-policy input을 읽고 이런 state가 됐는가"를 바로 고정하기 어렵다.


## 3. W2-2 이후에도 남아 있는 구조 문제

### 3-1. state policy caller가 여전히 로컬 변수 다발을 만든다

현재 `WaitEngine`은 context에서

- 방향 정보
- reason 정보
- market/setup 정보
- helper hint 정보
- effective threshold
- bias snapshot

을 다시 개별 변수로 꺼낸 뒤 state policy에 전달한다.

즉 frozen contract가 있음에도,
state policy 직전에는 다시 옛 구조로 풀어 헤치는 셈이다.

### 3-2. state policy 입력과 state policy 결과가 같은 층위에서 다뤄진다

지금 compact context에는

- bias 요약
- threshold 요약
- 최종 policy 결과

는 남지만,
정작 "state policy가 읽은 입력 compact view"는 별도 계약으로 남지 않는다.

그래서 지금은
"state policy output은 보이는데, input은 사람이 역으로 재구성해야 하는 상태"에 가깝다.

### 3-3. state policy helper signature가 너무 넓다

현재 `resolve_entry_wait_state_policy_v1(...)`는
상당히 긴 인자 목록을 받는다.

이건 helper 자체가 나쁘다는 뜻은 아니다.
다만 caller 관점에서는

- 무엇이 raw wait input인지
- 무엇이 bias 결과인지
- 무엇이 helper hint인지
- 무엇이 special scene flag인지

를 한눈에 보기 어렵게 만든다.

### 3-4. observability 관점에서 "state policy input snapshot"이 없다

지금 recent diagnostics에서 읽기 좋은 것은

- helper hint
- energy trace
- bias bundle summary
- final wait state/result

쪽이다.

그런데 state policy 입력면이 따로 고정되지 않으면,
나중에 "왜 CENTER가 아니라 ACTIVE였는가", "왜 hard wait가 풀렸는가" 같은 질문은
여전히 사람이 여러 블록을 합쳐서 해석해야 한다.


## 4. W2-3의 목표

W2-3의 목표는 한 문장으로 정리하면 아래와 같다.

> state policy가 실제로 읽는 입력을
> `entry_wait_state_policy_input_v1`라는 하나의 명시적 contract로 고정한다.

여기서 중요한 점은,
W2-3의 목적이 state policy 규칙을 바꾸는 것이 아니라는 점이다.

이번 단계의 목적은 어디까지나 아래다.

- state policy caller 정리
- state policy input contract 명시화
- metadata/runtime/replay에서 다시 읽기 쉬운 구조 확보


## 5. 이번 단계에서 추천하는 방향

이번 단계에서는 helper public API를 한 번에 갈아엎기보다,
먼저 `context -> state policy input -> state policy result`의 adapter 층을 두는 방향이 안전하다.

추천 구조는 아래와 같다.

- 기존 helper 유지
  - `resolve_entry_wait_state_policy_v1(...)`
- 새 contract builder/adapter 추가
  - `build_entry_wait_state_policy_input_v1(entry_wait_context_v1) -> dict`
  - `compact_entry_wait_state_policy_input_v1(...) -> dict`
  - `resolve_entry_wait_state_policy_from_context_v1(entry_wait_context_v1) -> dict`

즉 이번 단계에서는
기존 state policy helper 내부 규칙은 최대한 유지하고,
그 앞단 caller를 정리하는 데 집중하는 편이 좋다.


## 6. 추천 파일 구조

### 추천 새 파일

- `backend/services/entry_wait_state_policy_contract.py`

### 추천 public 함수

- `build_entry_wait_state_policy_input_v1(entry_wait_context_v1) -> dict`
- `compact_entry_wait_state_policy_input_v1(entry_wait_state_policy_input_v1) -> dict`
- `resolve_entry_wait_state_policy_from_context_v1(entry_wait_context_v1) -> dict`

### 권장 역할 분리

- `entry_wait_context_contract.py`
  - wait 전반 입력 context를 만든다
- `entry_wait_context_bias_bundle.py`
  - bias/helper 결과와 threshold adjustment를 묶는다
- `entry_wait_state_policy_contract.py`
  - state policy가 읽을 입력면만 따로 구성한다
- `entry_wait_state_policy.py`
  - 실제 state 분류 규칙을 유지한다

이렇게 가면 책임 경계가 꽤 선명해진다.


## 7. state policy input contract에 들어가야 할 층

`entry_wait_state_policy_input_v1`는 단순 field dump가 아니라
"state policy가 읽는 의미 단위"를 보여주는 계약이어야 한다.

추천 층은 아래와 같다.

### 7-1. identity / directional block

- symbol
- 현재 action
- core 허용 방향
- preflight 허용 방향

이 블록은 `AGAINST_MODE`와 required-side 해석에 직접 연결된다.

### 7-2. reason block

- blocked reason
- observe reason
- action-none reason
- reason split

이 블록은 state policy가 wait 상태 이름과 reason을 만들 때 가장 먼저 읽는 층이다.

### 7-3. market / setup block

- box 상태
- band 상태
- observe metadata에서 필요한 특례 정보
- setup 상태
- setup reason
- setup trigger state

이 블록은 `EDGE_APPROACH`, `NEED_RETEST`, `CENTER`, probe 특례 해석에 중요하다.

### 7-4. score block

- wait score
- conflict
- noise
- penalty

이 블록은 `ACTIVE`, `CONFLICT`, `NOISE` 같은 기본 분기와 hard-wait 판정의 기초가 된다.

### 7-5. threshold block

- base soft threshold
- base hard threshold
- effective soft threshold
- effective hard threshold

이 블록은 hard-wait 판정과 release/lock bias 적용 후 경계값을 설명해준다.

### 7-6. helper hint block

- action readiness
- wait vs enter hint
- soft block active/reason/strength
- policy hard block 여부
- policy suppressed 여부
- source provenance

이 블록은 `POLICY_BLOCK`, `POLICY_SUPPRESSED`, `HELPER_SOFT_BLOCK`, `HELPER_WAIT`를 해석하는 데 필요하다.

### 7-7. bias snapshot block

- state bias compact
- belief bias compact
- edge-pair bias compact
- probe temperament compact
- bias bundle summary

이 블록은 hard-wait 완화/강화의 설명면이다.

### 7-8. special scene block

- XAU second support probe relief
- XAU upper sell probe 관련 compact flag
- BTC lower strong score soft wait 관련 전제 조건 compact flag

이 층은 일반 wait 규칙이 아니라 상징적인 특례 장면을 설명한다.


## 8. 무엇을 넣지 말아야 하나

이번 contract는 state policy 입력면을 설명하려는 것이지,
원본 payload 전체를 옮기려는 것이 아니다.

그래서 아래는 가급적 넣지 않는 편이 좋다.

- raw `observe_confirm_v2` 전체 dump
- raw `entry_probe_plan_v1` 전체 dump
- raw `probe_candidate_v1` 전체 dump
- decision policy 전용 utility 입력
- entry row 전체 복사본

이런 것까지 넣으면 contract가 금방 무거워지고,
"무엇이 state policy의 진짜 입력인가"가 다시 흐려진다.


## 9. W2-3 이후 WaitEngine의 이상적인 흐름

W2-3 이후 entry wait state 쪽 흐름은 아래처럼 보이는 것이 좋다.

1. `entry_wait_context_v1`를 만든다.
2. `bias_bundle_v1`를 만든다.
3. context에 bias/threshold 결과를 반영한다.
4. `entry_wait_state_policy_input_v1`를 만든다.
5. state policy resolver가 그 input을 읽는다.
6. final state/result를 context와 metadata에 남긴다.

즉 `WaitEngine`은
"값을 하나하나 꺼내서 state policy에 넘기는 조합기"가 아니라
"context pipeline을 순서대로 호출하는 orchestration layer"에 가까워져야 한다.


## 10. 추천 구현 순서

### W2-3-1. state policy input contract 파일 추가

먼저 `entry_wait_state_policy_contract.py`를 만들고,
`build_entry_wait_state_policy_input_v1(...)`를 구현한다.

이 단계에서는 behavior를 바꾸지 않는다.
목적은 state policy 입력을 하나의 객체로 모으는 것이다.

### W2-3-2. adapter resolver 추가

그 다음
`resolve_entry_wait_state_policy_from_context_v1(entry_wait_context_v1)`를 만들고,
이 adapter가 내부에서 기존 `resolve_entry_wait_state_policy_v1(...)`를 호출하도록 한다.

즉 helper 내부 규칙은 그대로 두고 caller만 context 기반으로 바꾼다.

### W2-3-3. WaitEngine caller 치환

그 다음 `WaitEngine.build_entry_wait_state_from_row(...)`에서
flat argument 조립 부분을 걷어내고,
context adapter를 한 번 호출하도록 바꾼다.

### W2-3-4. compact state-policy input 저장

마지막으로 metadata와 compact context 안에
`entry_wait_state_policy_input_v1`의 compact summary를 남긴다.

이 단계가 있어야 replay/handoff/recent diagnostics에서
state policy 입력면을 바로 읽을 수 있다.


## 11. 이번 단계에서 건드리지 말아야 할 것

W2-3에서는 아래를 일부러 건드리지 않는 편이 좋다.

- state policy 규칙 자체
- hard-wait 철학
- probe 특례 규칙
- bias multiplier 수치
- decision policy 로직
- exit wait 구조

이번 단계의 목적은 behavior redesign이 아니라
state policy caller contract freeze다.


## 12. direct 테스트에서 꼭 잡아야 할 것

### 12-1. state policy input builder 테스트

최소한 아래를 direct test로 고정하는 것이 좋다.

- blocked/observe/action-none reason split가 정확히 들어간다
- effective threshold가 bias bundle 이후 값으로 들어간다
- helper hint source가 유지된다
- probe 특례 관련 compact flag가 입력면에 보인다

### 12-2. adapter parity 테스트

같은 row를 넣었을 때

- 기존 flat state policy 호출 결과
- 새 context adapter 호출 결과

가 같아야 한다.

이 테스트는 W2-3의 핵심 안전장치다.

### 12-3. WaitEngine metadata 노출 테스트

`WaitState.metadata` 안에

- compact `entry_wait_context_v1`
- compact `entry_wait_bias_bundle_v1`
- compact `entry_wait_state_policy_input_v1`

가 함께 남는지 고정해야 한다.

### 12-4. 기존 wait 회귀 유지

기존 `test_wait_engine.py`와 entry wait 관련 회귀는 그대로 녹색이어야 한다.


## 13. 완료 선언 조건

W2-3는 아래가 만족되면 완료로 볼 수 있다.

1. `entry_wait_state_policy_input_v1` builder가 생겼다.
2. `WaitEngine`이 flat 인자 다발 대신 context adapter를 호출한다.
3. state policy input compact summary가 metadata/context에 남는다.
4. adapter parity direct tests가 추가된다.
5. 기존 wait 회귀가 그대로 통과한다.


## 14. W2-3가 끝나면 좋아지는 점

W2-3가 끝나면 아래가 쉬워진다.

- W2-4 또는 이후 단계에서 state policy helper signature 자체를 더 줄이기
- W3 recent diagnostics에서 state-policy input면 요약하기
- W4 end-to-end에서 "이 state는 어떤 policy input을 읽고 나왔는가"를 고정하기
- 새 스레드 handoff에서 wait state 해석을 더 짧게 설명하기

즉 W2-3는 단순 cleanup이 아니라,
wait 구조를 "해석 가능한 파이프라인"으로 완성하는 중간 핵심 단계다.


## 15. 한 줄 결론

W2-3의 본질은
`bias bundle` 다음에 오는 `state policy caller`를
긴 flat 인자 호출에서 `state policy input contract` 기반 호출로 바꾸는 것이다.

그래야 wait 구조가
`context -> bias -> state policy -> decision`
형태로 끝까지 같은 언어를 유지하게 된다.
