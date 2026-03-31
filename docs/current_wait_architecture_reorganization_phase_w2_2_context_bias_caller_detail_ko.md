# 기다림 재정리 Phase W2-2 상세 문서

부제: `entry_wait_context_v1`를 bias/helper caller의 단일 입력으로 쓰기 위한 정리 가이드

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 `W2-2`를 실제로 구현하기 전에,
W2-1에서 만든 `entry_wait_context_v1`를
어떤 방식으로 bias/helper caller의 기준 입력으로 바꿔야 하는지 정리하기 위한 문서다.

W2-1이 "입력을 한 묶음으로 모으는 단계"였다면,
W2-2는 "그 묶음을 실제 caller들이 읽게 바꾸는 단계"다.


## 2. 왜 W2-2가 필요한가

W2-1 이후 `WaitEngine.build_entry_wait_state_from_row(...)`는
이제 시작하자마자 `entry_wait_context_v1`를 만든다.

이건 큰 진전이다.
하지만 아직 구조적으로는 한 단계가 더 남아 있다.

현재 함수는

- context를 만든 다음
- 다시 context를 로컬 변수 여러 개로 풀고
- 그 로컬 변수를 bias helper에 넘긴다

즉 contract는 생겼지만,
caller는 아직 완전히 contract 중심으로 읽고 있지는 않다.

그래서 현재 상태는 비유하면 이렇다.

> 큰 서랍장에 물건을 다 정리해 넣었는데,
> 실제로 쓸 때는 다시 바닥에 다 꺼내놓고 쓰는 상태

W2-2의 목적은 이걸 줄이는 것이다.


## 3. W2-1 이후에도 남아 있는 구조적 문제

### 3-1. bias caller가 아직 로컬 변수에 의존한다

현재 state / belief / edge-pair / probe helper는
결과적으로 context에서 온 값을 읽지만,
그 전에 `WaitEngine`이 다시 로컬 변수로 풀어주는 단계가 남아 있다.

즉 context가 single input contract가 아니라
"중간 저장소"에 가까운 상태다.

### 3-2. edge-pair / probe helper는 아직 payload 중심 흔적이 남아 있다

state / belief는 비교적 context sub-block을 직접 읽게 바뀌었지만,
edge-pair와 probe 쪽은 여전히 `payload + observe_confirm_v2` 중심 호출 흔적이 남아 있다.

즉 context 중심 전환이 덜 끝났다.

### 3-3. threshold bias 적용도 inline으로 퍼져 있다

현재 effective soft/hard threshold는
`WaitEngine` 안에서 bias helper 결과를 곱해가며 계산한다.

즉 bias caller와 threshold 조정 책임이 아직 한 군데에 같이 있다.

### 3-4. bias 결과를 context에 넣는 시점도 caller 안에 남아 있다

현재는 helper를 부르고,
threshold를 조정하고,
그 결과를 다시 context의 `bias`/`thresholds`에 집어넣는다.

이 역시 "context consumer orchestration"이 아직 `WaitEngine` 안에 남아 있다는 뜻이다.


## 4. W2-2의 목표

W2-2의 목표는 한 문장으로 정리할 수 있다.

> bias/helper caller가 `entry_wait_context_v1`를 직접 읽어
> 하나의 bias bundle과 threshold adjustment 결과를 만들게 한다.

즉 W2-2는 helper public API를 전면 재설계하는 단계가 아니다.
오히려 **existing helper를 유지한 채, context를 읽는 caller adapter 층을 추가하는 단계**에 가깝다.


## 5. W2-2에서 권장하는 방향

내 기준에서 가장 안정적인 방향은
기존 helper 시그니처를 유지하고,
그 위에 context-aware adapter/bundle owner를 하나 두는 것이다.

즉 아래 구조가 좋다.

- 기존 helper
  - state bias helper
  - belief bias helper
  - edge-pair bias helper
  - probe temperament helper
- 새 caller bundle layer
  - context를 읽는다
  - helper들을 호출한다
  - 결과를 하나의 bias bundle로 묶는다
  - threshold adjustment까지 같이 정리한다

이 방향의 장점은 명확하다.

- helper 자체 의미를 바꾸지 않는다
- direct helper tests를 거의 그대로 유지할 수 있다
- `WaitEngine` 본문이 더 얇아진다
- W2-3 state policy context 전환과 자연스럽게 이어진다


## 6. 권장 새 owner 형태

### 권장 파일

- `backend/services/entry_wait_context_bias_bundle.py`

### 권장 public 함수

- `resolve_entry_wait_bias_bundle_v1(entry_wait_context_v1) -> dict`

### 선택적 보조 함수

- `apply_entry_wait_threshold_bias_v1(entry_wait_context_v1, bias_bundle_v1) -> dict`
- `compact_entry_wait_bias_bundle_v1(bias_bundle_v1) -> dict`

핵심은 `WaitEngine`이 더 이상
각 bias helper의 입력을 하나씩 꺼내 조합하지 않는 방향으로 가는 것이다.


## 7. bias bundle이 담아야 할 것

W2-2의 산출물은 단순 dict 묶음이 아니라,
"wait 해석 caller 단계의 정규화된 결과"여야 한다.

권장 묶음은 아래와 같다.

### 7-1. state bias 결과

- prefer_confirm_release
- prefer_wait_lock
- threshold multiplier
- 필요한 라벨 요약

### 7-2. belief bias 결과

- prefer_confirm_release
- prefer_wait_lock
- threshold multiplier
- spread/persistence 관련 핵심 요약

### 7-3. edge-pair bias 결과

- present 여부
- context label
- winner side
- pair gap
- prefer_confirm_release / prefer_wait_lock

### 7-4. probe temperament 결과

- scene id
- active / ready
- prefer_confirm_release / prefer_wait_lock
- enter/wait delta

### 7-5. threshold adjustment 결과

- base soft/hard
- effective soft/hard
- 어떤 bias가 얼마나 곱해졌는지 요약

즉 bundle은 "helper raw output 묶음"과
"그 helper 묶음을 반영한 threshold 결과"를 함께 담는 편이 좋다.


## 8. W2-2 이후 WaitEngine이 어떻게 달라져야 하나

현재 흐름은 대략 이렇다.

1. context를 만든다
2. state/belief/edge-pair/probe helper를 각각 부른다
3. threshold를 직접 곱한다
4. 결과를 다시 context에 넣는다

W2-2 이후 이상적인 흐름은 이렇다.

1. context를 만든다
2. bias bundle resolver를 한 번 부른다
3. bundle에서 effective threshold와 bias snapshot을 받는다
4. state policy로 넘어간다

즉 `WaitEngine` 입장에선
"bias layer orchestration"이 밖으로 한 단계 더 빠지는 셈이다.


## 9. W2-2에서 권장하는 구현 순서

### W2-2-1. bias bundle resolver 추가

먼저 context를 읽어
네 bias/helper를 호출하는 bundle resolver를 만든다.

이 단계에서는 behavior를 바꾸지 않는다.
현재 `WaitEngine` 안의 호출 순서를 그대로 옮기는 것이 목적이다.

### W2-2-2. threshold adjustment를 bundle layer로 이동

그다음 effective soft/hard threshold 계산을
`WaitEngine` 본문이 아니라 bundle layer에서 하게 만든다.

이 단계가 중요하다.
왜냐하면 threshold 조정도 사실 bias caller orchestration의 일부이기 때문이다.

### W2-2-3. WaitEngine caller 치환

그다음 `WaitEngine`에서
개별 helper 호출과 threshold 곱셈을 지우고,
bundle resolver 결과만 읽도록 바꾼다.

### W2-2-4. compact context와 bias summary 동기화

마지막으로 compact context가
새 bundle summary를 읽어 동일한 의미를 담도록 맞춘다.


## 10. W2-2에서 건드리지 말아야 할 것

이번 단계에서는 아래를 함께 건드리지 않는 편이 좋다.

- state bias 수치 변경
- belief bias 철학 변경
- edge-pair 기준 재설계
- probe scene 의미 변경
- state policy signature 대폭 변경

그건 W2-2의 목표가 아니다.
이번 목표는 **caller 정리**다.


## 11. direct 테스트에서 꼭 잡아야 할 것

W2-2는 helper 직접 테스트보다
bias bundle 직접 테스트가 중요해진다.

최소한 아래 장면을 잡는 편이 좋다.

### 11-1. neutral row

기대 결과:

- 모든 bias가 neutral
- effective threshold가 base threshold와 같다

### 11-2. belief release + edge-pair release가 함께 있는 row

기대 결과:

- bundle이 두 release를 모두 반영한다
- effective threshold가 완화 방향으로 움직인다

### 11-3. helper soft block + policy block이 있는 row

기대 결과:

- helper hint는 context에 남고
- threshold adjustment는 bias bundle과 분리돼 설명 가능해야 한다

### 11-4. probe scene row

기대 결과:

- probe scene bias가 bundle에 들어간다
- compact context의 probe summary와 모순되지 않는다


## 12. 완료 선언 조건

W2-2는 아래가 만족되면 완료로 본다.

1. bias bundle resolver가 생겼다
2. `WaitEngine`에서 개별 bias helper caller가 사라지거나 크게 줄었다
3. effective threshold 계산이 bundle layer로 이동했다
4. compact context가 bundle summary와 같은 의미를 담는다
5. 새 bundle direct tests가 추가된다
6. 기존 `test_wait_engine.py`와 entry wait 관련 회귀가 그대로 녹색이다


## 13. W2-2가 끝나면 무엇이 쉬워지나

W2-2가 끝나면 다음이 쉬워진다.

- W2-3에서 state policy caller를 context 기반으로 더 깔끔하게 묶기
- W3에서 bias summary를 recent diagnostics로 요약하기
- W4에서 "이 row는 어떤 bias bundle을 읽었는가"를 end-to-end로 고정하기

즉 W2-2는 W2의 중간 다리 역할을 한다.


## 14. 한 줄 결론

W2-2는 `entry_wait_context_v1`를 만든 것에서 멈추지 않고,
그 context를 실제 bias/helper caller의 단일 입력으로 쓰도록
caller orchestration을 바깥 bundle layer로 밀어내는 단계다.
