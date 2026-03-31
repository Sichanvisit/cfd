# 기다림 재정리 Phase W2 상세 문서

부제: wait 입력 계약을 하나의 frozen context로 고정하는 구현 설계서

작성일: 2026-03-27 (KST)

## 진행 상태 (2026-03-27)

현재 `W2-1 context builder 도입`은 구현과 핵심 회귀 검증까지 완료된 상태다.

- `entry_wait_context_contract.py` 추가
- `entry_wait_context_v1` / compact helper 추가
- `WaitEngine.build_entry_wait_state_from_row(...)` context 기반 caller 치환
- `WaitState.metadata`에 compact `entry_wait_context_v1` 추가
- direct builder tests 추가
- `test_wait_engine.py` 통과
- `test_entry_try_open_entry_policy.py` 통과
- `test_entry_try_open_entry_probe.py` 통과

## 1. 문서 목적

이 문서는 `Phase W2. Wait Context Contract Freeze`를 실제로 시작하기 전에,
무엇을 왜 얼려야 하는지,
지금 어떤 입력이 흩어져 있는지,
어떤 모양의 context contract로 묶어야 하는지를 상세히 정리하기 위한 문서다.

W1이 "누가 해석할 것인가"를 정리한 단계였다면,
W2는 "무엇을 읽고 해석할 것인가"를 고정하는 단계다.


## 2. 왜 W2가 지금 필요한가

W1 이후 `WaitEngine`의 owner 경계는 많이 좋아졌다.

- 상태 기반 bias는 밖으로 빠졌다
- belief 기반 bias도 밖으로 빠졌다
- 방향성 쌍 해석도 밖으로 빠졌다
- probe 장면 해석도 밖으로 빠졌다
- state policy / decision policy도 이미 분리돼 있다

그런데 아직 남은 구조적 문제는 분명하다.

> 해석 owner는 분리됐지만,
> 그 owner들이 읽는 입력 묶음은 아직 하나의 contract로 고정돼 있지 않다.

즉 지금은 owner는 나뉘었지만,
입력 문맥은 여전히 `WaitEngine.build_entry_wait_state_from_row(...)` 안에서 즉석 조합되고 있다.

이 상태가 왜 아쉬우냐면,

- helper가 읽는 입력 범위를 한 번에 설명하기 어렵고
- metadata에 남는 정보와 실제 계산 입력이 완전히 같은 contract가 아니고
- 나중에 row replay / recent diagnostics / end-to-end test에서 동일한 입력 묶음을 재사용하기 어렵기 때문이다

그래서 W2의 목적은 명확하다.

> 기다림 판단에 실제로 들어간 입력 묶음을 하나의 frozen contract로 만든다.


## 3. 지금 입력이 어떻게 흩어져 있는가

현재 entry wait state builder는 아래 정보를 직접 꺼내서 조합한다.

### 3-1. row 상단에서 바로 읽는 값

- wait score / conflict / noise / penalty
- blocked reason
- action 없음 이유
- 현재 action
- box / band 상태
- core / preflight 방향 제한
- setup 상태 / 이유 / trigger state

즉 "기본 wait 문맥"이 row 여러 필드에 흩어져 있다.

### 3-2. observe-confirm에서 읽는 값

- observe reason
- observe metadata
- probe candidate fallback
- edge-pair 관련 metadata

즉 "관찰 상태에서 온 추가 문맥"은 observe-confirm payload 안에 별도로 있다.

### 3-3. state / belief 벡터에서 읽는 값

- state vector와 metadata
- belief state와 metadata

즉 bias owner들이 읽는 핵심 해석 재료도 row 상단이 아니라 별도 payload 블록에 있다.

### 3-4. energy / policy helper에서 읽는 값

- action readiness
- wait vs enter hint
- soft block 활성 여부와 강도
- policy hard block 활성 여부
- policy suppression 여부

즉 helper hint도 또 다른 입력 블록에서 온다.

### 3-5. Config에서 읽는 값

- symbol별 wait soft threshold
- symbol별 wait hard threshold

즉 threshold의 기준값은 row가 아니라 config lookup에서 온다.

### 3-6. helper 결과로 만들어지는 값

- state bias 결과
- belief bias 결과
- edge-pair bias 결과
- probe temperament 결과

즉 일부는 원천 입력이고,
일부는 해석 owner가 만든 결과인데,
현재는 이 둘도 같은 함수 안에서 함께 섞인다.


## 4. 현재 구조가 아쉬운 이유

지금 구조는 동작은 하지만,
다음 네 가지 점에서 contract가 아직 약하다.

### 4-1. 같은 입력을 여러 번 읽는다

예를 들어 observe-confirm은 이미 읽었는데
edge-pair helper 호출 시 다시 건네고,
probe helper 호출 시도 다시 건넨다.

즉 "한 번 정리된 wait 문맥"이 아니라,
"필요할 때마다 다시 꺼내 쓰는 방식"에 가깝다.

### 4-2. 계산 입력과 metadata가 완전히 같은 shape가 아니다

현재 metadata에는 많은 값이 남지만,
그 값들이 하나의 문맥 계약으로 정리된 형태라기보다
필드 나열에 더 가깝다.

즉 지금도 설명은 되지만,
"이게 곧 wait context다"라고 말하기는 조금 어렵다.

### 4-3. row replay와 diagnostics 재사용이 어렵다

나중에 recent diagnostics나 replay를 볼 때,
동일한 입력 묶음을 다시 읽고 싶어도
현재는 그걸 하나의 객체로 바로 꺼내기가 어렵다.

### 4-4. end-to-end 테스트에서 기준점이 분산된다

W4에서 `consumer -> wait state -> wait decision -> row/runtime`를 고정하려면
"wait가 실제로 무엇을 읽었는지"를 한 묶음으로 검증할 수 있어야 한다.

지금은 그 기준점이 여러 로컬 변수와 metadata 필드로 흩어져 있다.


## 5. W2의 핵심 목표

W2의 핵심 목표는 아래 한 문장으로 정리된다.

> entry wait 판단에 실제로 사용된 입력과 해석 결과를
> `entry_wait_context_v1`이라는 하나의 contract로 고정한다.

여기서 중요한 포인트는 두 가지다.

- raw input만 담는 게 아니다
- final metadata 덤프를 그대로 옮기는 것도 아니다

즉 W2의 context는
"wait 해석에 실제로 필요한 정규화된 입력"과
"그 입력을 읽고 만든 해석 결과"를
구분해서 담는 contract여야 한다.


## 6. 권장 contract 이름과 owner

### 권장 contract 이름

- `entry_wait_context_v1`

### 권장 파일

- `backend/services/entry_wait_context_contract.py`

### 권장 public 함수

- `build_entry_wait_context_v1(...) -> dict`

필요하다면 아래 보조 함수도 함께 두는 편이 좋다.

- `compact_entry_wait_context_v1(...) -> dict`
- `build_entry_wait_reason_split_v1(...) -> dict`


## 7. `entry_wait_context_v1`가 담아야 할 층

W2에서 가장 중요한 것은
필드를 많이 넣는 것이 아니라,
의미 층을 분리해 담는 것이다.

권장 층은 아래와 같다.

### 7-1. identity / directional context

이 층은 "지금 누구를 어떤 방향으로 읽고 있는가"를 담는다.

- symbol
- 현재 action
- core / preflight 방향 제한
- 실제 directional 해석에 필요한 기본 문맥

즉 wait helper들이 "현재 어떤 방향 진입 문맥인지"를 다시 계산하지 않도록 한다.

### 7-2. reason context

이 층은 "왜 지금 enter가 아니라 wait 문맥이 되었는가"를 담는다.

- blocked reason
- observe reason
- action-none reason
- reason split

이 층은 매우 중요하다.
W5 handoff나 W4 end-to-end 테스트에서
가장 먼저 읽는 기준점이 되기 때문이다.

### 7-3. market position context

이 층은 현재 위치 문맥을 담는다.

- box 상태
- band 상태
- observe metadata 중 state policy에 직접 영향을 주는 값

즉 상태 policy가 일반 center/noise wait인지,
edge approach인지,
active observe인지 판단할 때 필요한 기본 위치 정보다.

### 7-4. setup context

이 층은 setup 단계에서 넘어온 준비 상태를 담는다.

- setup status
- setup reason
- setup trigger state

wait는 pure observe만 보는 게 아니라
setup 단계에서 온 맥락도 같이 본다.
그래서 이 층을 분리해 두는 편이 좋다.

### 7-5. score context

이 층은 raw wait score family를 담는다.

- wait score
- conflict
- noise
- penalty

이 값들은 wait state와 decision의 기준점이므로,
W2에서 반드시 별도 묶음으로 남겨두는 편이 좋다.

### 7-6. threshold context

이 층은 config lookup으로 만든 base threshold와,
bias 적용 후 threshold를 구분해 담는다.

- symbol별 base soft/hard threshold
- bias 적용 후 effective soft/hard threshold

이 구분이 필요한 이유는,
나중에 "wait가 많아진 이유가 raw threshold 때문인지, bias multiplier 때문인지"를 분리해서 볼 수 있어야 하기 때문이다.

### 7-7. helper hint context

이 층은 energy / policy helper에서 들어온 wait hints를 담는다.

- action readiness
- wait vs enter hint
- soft block 활성 여부와 강도
- soft block reason
- policy hard block 활성 여부
- suppression 여부
- 각 값의 source

이 층은 W3 recent summary와 가장 직접적으로 연결된다.

### 7-8. observe/probe context

이 층은 observe-confirm과 probe 장면 관련 문맥을 담는다.

- observe-confirm compact view
- probe scene compact view
- special scene flags

즉 XAU/BTC/NAS probe 장면처럼
일반 wait와 구분되는 scene-specific 정보가 이 층에 묶여 있어야 한다.

### 7-9. bias context

이 층은 W1에서 분리한 helper 결과를 담는다.

- 상태 기반 bias 결과
- belief 기반 bias 결과
- edge-pair 기반 bias 결과
- probe temperament 결과

이 값은 raw input이 아니라 interpretation 결과다.
그래서 input 층과 분리되어야 한다.

### 7-10. policy context

이 층은 state policy와 decision policy가 읽을 공용 입력과,
state policy 결과를 담는다.

- state policy에 실제로 들어가는 compact 입력
- state policy 결과

decision policy는 이 context를 통해
"무엇을 보고 state가 나왔는지"를 더 쉽게 재활용할 수 있어야 한다.


## 8. W2에서 권장하는 설계 원칙

### 8-1. raw payload 전체를 넣지 않는다

context contract는 row payload의 전체 dump가 아니다.
필요한 값만 정규화해서 담아야 한다.

그렇지 않으면 contract가 커지고,
CSV/runtime metadata도 무거워진다.

### 8-2. compact view와 full build를 구분한다

builder는 full context를 만들 수 있어도,
metadata에는 compact version만 저장하는 편이 좋다.

즉 추천 구조는 아래와 같다.

- 내부 계산용 full context
- metadata/runtime용 compact context

### 8-3. "입력"과 "해석 결과"를 같은 층에 섞지 않는다

예를 들어 `soft_block_strength`는 helper hint input이고,
`prefer_wait_lock`은 bias 해석 결과다.

이 둘을 같은 층에 섞으면
나중에 관측과 해석이 다시 흐려진다.

### 8-4. source provenance를 유지한다

특히 helper hint는 어디서 왔는지 중요하다.

- payload에서 온 것인지
- energy helper에서 온 것인지
- default인지

이 출처를 같이 남겨야 diagnostics 해석이 쉬워진다.


## 9. W2에서 `WaitEngine`이 어떻게 바뀌어야 하는가

현재 `build_entry_wait_state_from_row(...)`는
입력을 직접 읽고, bias를 계산하고, metadata를 직접 조립한다.

W2 이후 이상적인 흐름은 아래와 같다.

1. row/payload를 받는다
2. `entry_wait_context_v1`를 먼저 만든다
3. bias helper는 이 context를 읽는다
4. state policy는 이 context와 bias snapshot을 읽는다
5. WaitState metadata에는 compact context를 남긴다

즉 `WaitEngine`은 로컬 변수 나열 중심에서
"frozen context -> helper chain -> result" 형태로 더 이동해야 한다.


## 10. 권장 구현 순서

W2는 한 번에 끝내기보다 아래 순서가 안전하다.

### W2-1. context builder 도입

먼저 `build_entry_wait_context_v1(...)`를 만들고,
현재 `build_entry_wait_state_from_row(...)`가 읽는 raw inputs를 이 builder로 모은다.

이 단계에서는 behavior를 바꾸지 않는다.
그냥 "흩어진 입력을 한 객체로 모으는 것"이 목적이다.

### W2-2. bias helper caller를 context 기반으로 전환

그다음 state / belief / edge-pair / probe helper가
로컬 변수 대신 context sub-block을 읽도록 바꾼다.

이 단계 역시 의미를 바꾸지 않는다.
입력 진입점을 통일하는 것이 목적이다.

### W2-3. state policy 입력도 context 기반으로 정리

그다음 state policy caller가
지금처럼 개별 인자를 길게 넘기기보다
context에서 필요한 층을 읽어 넘기도록 정리한다.

이 단계에서 state policy signature를 당장 크게 바꿀지,
아니면 caller 쪽만 compact하게 바꿀지는 선택할 수 있다.

내 추천은 먼저 caller 정리 후, 필요하면 다음 단계에서 signature를 줄이는 것이다.

### W2-4. metadata compact context 저장

마지막으로 `WaitState.metadata`에
현재처럼 흩어진 필드만 두지 말고,
compact `entry_wait_context_v1`를 함께 저장하도록 한다.

이 단계가 되어야 W3/W4/W5와 자연스럽게 이어진다.


## 11. direct builder 테스트에서 꼭 잡아야 할 것

W2는 policy 테스트보다
context builder 자체 테스트가 중요하다.

최소한 아래 장면은 고정하는 편이 좋다.

### 11-1. 기본 blocked row

기대 결과:

- reason split이 정확히 분리된다
- score/threshold/helper hints가 올바르게 정규화된다

### 11-2. observe-confirm + probe 장면 row

기대 결과:

- observe reason과 probe scene compact view가 동시에 정리된다
- special scene flags가 유지된다

### 11-3. energy helper hint row

기대 결과:

- action readiness / wait vs enter / soft block의 값과 source가 정확히 들어간다

### 11-4. direction-limited row

기대 결과:

- core/preflight/action directional context가 일관되게 정리된다


## 12. W2에서 건드리면 안 되는 것

이번 W2에서는 아래를 함께 재설계하지 않는 편이 좋다.

- wait 의미 자체 변경
- bias multiplier 수치 조정
- state policy 철학 변경
- decision policy scoring 재설계
- exit wait contract까지 같이 확장

W2의 목적은 behavior redesign이 아니라
input contract freeze다.


## 13. W2 완료 선언 조건

W2는 아래가 만족되면 완료로 본다.

1. `entry_wait_context_v1` builder가 생겼다
2. entry wait state builder가 로컬 변수 나열보다 context 중심으로 바뀌었다
3. bias helper caller가 같은 context contract를 읽는다
4. metadata에 compact context가 남는다
5. builder direct tests가 추가된다
6. 기존 `test_wait_engine.py`와 entry wait 관련 회귀가 그대로 녹색이다


## 14. W2가 끝나면 무엇이 좋아지나

W2가 끝나면 아래가 쉬워진다.

### 14-1. W3 recent wait semantic summary

recent summary를 만들 때
CSV/runtime에서 wait 입력 묶음을 더 일관되게 읽을 수 있다.

### 14-2. W4 end-to-end contract tests

`consumer -> wait state -> wait decision -> row/runtime`에서
"wait가 무엇을 읽었는가"를 하나의 context 기준으로 검증할 수 있다.

### 14-3. W5 handoff / runtime 가이드

새 스레드에서
"이 wait는 어떤 문맥에서 나왔는가"를
context 한 묶음으로 설명할 수 있다.

### 14-4. 이후 tuning의 안정성

threshold나 bias를 조정해도,
입력 contract가 고정돼 있으면
변화의 원인을 훨씬 더 분명하게 설명할 수 있다.


## 15. 한 줄 결론

W2는 `WaitEngine`의 해석 owner를 더 늘리는 단계가 아니라,
이미 분리된 owner들이 공통으로 읽는 입력 문맥을
`entry_wait_context_v1`라는 하나의 frozen contract로 고정하는 단계다.
