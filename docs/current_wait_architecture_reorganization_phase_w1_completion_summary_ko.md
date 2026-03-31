# 기다림 재정리 Phase W1 완료 정리 문서

부제: wait bias / scene owner extraction이 실제로 무엇을 바꿨는지에 대한 전체 정리

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 `Phase W1`이 끝난 시점에서,
기다림 레이어가 구조적으로 어떻게 달라졌는지를 한 장으로 정리하기 위한 문서다.

W1은 단순한 리팩터링 묶음이 아니었다.
핵심 목적은 `WaitEngine` 안에 섞여 있던
"기다림을 강하게 만드는 이유"와
"기다림을 풀어도 되는 이유"를
독립 owner로 분리해, wait 레이어를 entry 수준으로 세밀하게 정리하는 것이었다.


## 2. W1 이전 상태

W1 이전의 `WaitEngine`은 이미 동작은 하고 있었지만,
중요한 해석 owner가 본문 안에 함께 들어 있었다.

즉 아래가 모두 엔진 안에 붙어 있었다.

- 상태 질감을 읽는 wait bias
- belief 강도를 읽는 wait bias
- 방향성 쌍이 풀렸는지를 읽는 wait bias
- probe 장면 특례를 읽는 scene owner

이 구조의 문제는 명확했다.

- 새 규칙을 넣을수록 `WaitEngine` 본문이 비대해진다
- 어떤 변화가 "state 때문"인지 "belief 때문"인지 구분이 흐려진다
- scene-specific 예외가 일반 wait 로직과 섞인다
- 테스트는 통과해도 ownership 경계가 계속 약하다

즉 W1 이전의 문제는 wait가 틀렸다는 것보다,
"왜 이런 wait가 나왔는가"를 설명하는 owner가 한 군데에 너무 많이 붙어 있었다는 점이다.


## 3. W1의 목표

W1의 목표는 간단했다.

> `WaitEngine`을 wait 해석을 직접 계산하는 엔진에서,
> wait 입력을 정리하고 policy/bias helper를 호출해 결과를 조합하는 엔진으로 바꾼다.

이 목표를 위해 W1은 네 개의 owner extraction을 수행했다.

1. 상태 기반 wait bias 분리
2. belief 기반 wait bias 분리
3. edge-pair 기반 directional wait bias 분리
4. probe temperament 기반 scene-specific wait 해석 분리


## 4. W1에서 실제로 분리된 owner

### 4-1. 상태 기반 wait bias

이 owner는 시장 상태의 질감을 읽는다.

- quality가 좋은가
- patience 쪽이 유리한가
- execution friction이 높은가
- event risk가 높은가

즉 "환경이 지금 기다림을 더 요구하는가, 아니면 confirm release를 조금 허용하는가"를 해석하는 owner다.

이제 이 책임은 `entry_wait_state_bias_policy.py`로 분리되었다.

### 4-2. belief 기반 wait bias

이 owner는 thesis 강도를 읽는다.

- 지배 방향이 분명한가
- spread가 아직 deadband 안에 있는가
- persistence가 충분히 쌓였는가
- 현재 진입 의도와 dominant side가 맞는가

즉 "이 기다림이 아직 좋은 기다림인가, 아니면 이제 너무 과보수한 기다림이 되었는가"를 해석하는 owner다.

이제 이 책임은 `entry_wait_belief_bias_policy.py`로 분리되었다.

### 4-3. edge-pair 기반 directional wait bias

이 owner는 방향성 경쟁이 실제로 풀렸는지 읽는다.

- 지금이 의미 있는 edge/middle 문맥인가
- winner가 분명한가
- 그 winner가 현재 진입 의도와 맞는가
- pair gap이 충분히 벌어졌는가

즉 "아직 directional pair가 안 풀렸으니 더 기다려야 하는가" 또는
"이제 방향 우위가 비교적 분명하니 기다림을 조금 완화해도 되는가"를 해석하는 owner다.

이제 이 책임은 `entry_wait_edge_pair_bias_policy.py`로 분리되었다.

### 4-4. probe temperament 기반 scene-specific wait 해석

이 owner는 일반 wait와 probe 장면을 구분한다.

- 지금 row가 probe 장면인가
- plan/candidate/observe 중 어디에서 그 흔적이 왔는가
- ready 상태까지 왔는가
- scene 특성상 일반 wait보다 enter 쪽 긴장을 더 높게 봐야 하는가

즉 "이 장면을 일반 center/noise wait처럼 뭉개면 안 되는가"를 해석하는 owner다.

이제 이 책임은 `entry_wait_probe_temperament_policy.py`로 분리되었다.


## 5. W1 이후 WaitEngine의 역할

W1 이후 `WaitEngine`의 역할은 훨씬 선명해졌다.

이제 entry wait 흐름에서 `WaitEngine`이 주로 하는 일은 아래다.

1. row/payload에서 wait 입력을 읽는다
2. state / belief / edge-pair / probe helper를 호출한다
3. 각 helper 결과를 합쳐 wait threshold와 utility 문맥을 만든다
4. wait state policy를 호출해 상태를 정한다
5. wait decision policy를 호출해 실제 wait 선택 여부를 정한다
6. trace와 metadata를 남긴다

즉 본문이 "해석 owner"에서 "조합기" 쪽으로 이동했다.


## 6. W1 이후 구조를 한 문장으로 요약하면

이제 wait 레이어는 아래 구조에 더 가까워졌다.

`입력 정리 -> bias/scene helper -> state policy -> decision policy -> trace 기록`

이 문장 하나가 W1의 핵심 결과다.


## 7. W1이 보호한 핵심 의미

W1은 owner를 옮겼지만,
기다림의 의미를 바꾸는 작업은 아니었다.

보존한 핵심 계약은 아래와 같다.

### 7-1. 좋은 환경에서는 wait를 조금 풀 수 있다

quality가 좋고 confirm 쪽 환경이 우세하면,
wait는 무조건적인 lock이 아니라 완화될 수 있다.

### 7-2. belief가 아직 약하면 기다림을 유지해야 한다

spread가 deadband 안에 있거나 persistence가 약하면,
지금 wait는 아직 의미가 있다.

### 7-3. directional pair가 안 풀렸으면 조심해야 한다

clear winner가 없고 pair gap이 작으면,
directional wait는 아직 유지되어야 한다.

### 7-4. probe 장면은 일반 wait와 다르게 읽어야 한다

특히 XAU second support probe와 upper sell probe는
일반적인 center/noise wait처럼 뭉개지면 안 된다.

즉 W1은 behavior redesign이 아니라
"이미 중요했던 의미를 독립 owner로 고정한 작업"이었다.


## 8. W1이 특별히 보호한 대표 장면

### 8-1. XAU second support probe

이 장면은 일반 대기 장면이 아니라,
관찰 중이지만 이미 진입 준비 긴장이 생긴 장면으로 보존돼야 한다.

W1 이후에도 이 장면은

- `ACTIVE`로 살아 있고
- general center/noise wait로 떨어지지 않으며
- decision이 무조건 wait 쪽으로 기울지 않도록

계약이 유지된다.

### 8-2. XAU upper sell probe

이 장면도 동일하게,
일반적인 위쪽 대기가 아니라 special probe 장면으로 남아야 한다.

W1 이후에도 이 scene-specific 해석이 유지된다.

### 8-3. BTC conservative lower probe

이 장면은 ready 이전과 이후가 다르게 읽혀야 한다.

- ready 전에는 아직 보수적 wait가 더 의미 있을 수 있다
- ready 이후에는 wait lock을 계속 유지하면 과보수해질 수 있다

W1은 이 progression 차이를 owner로 분리해 보존했다.


## 9. W1 이후 생성된 파일 구조

W1이 끝난 뒤 wait entry 쪽 핵심 파일 구조는 아래처럼 읽으면 된다.

### 조합기 / 엔진

- `backend/services/wait_engine.py`

### bias / scene owner

- `backend/services/entry_wait_state_bias_policy.py`
- `backend/services/entry_wait_belief_bias_policy.py`
- `backend/services/entry_wait_edge_pair_bias_policy.py`
- `backend/services/entry_wait_probe_temperament_policy.py`

### state / decision owner

- `backend/services/entry_wait_state_policy.py`
- `backend/services/entry_wait_decision_policy.py`

이 구조는 의미상으로도 자연스럽다.

- bias helper는 "왜 기다려야 하는가 / 왜 덜 기다려도 되는가"를 계산한다
- state policy는 "어떤 wait 상태인가"를 정한다
- decision policy는 "실제로 wait를 선택할 것인가"를 정한다


## 10. W1 이후 테스트 구조

W1이 끝난 뒤 테스트도 ownership 단위로 나뉘었다.

### direct helper 테스트

- `test_entry_wait_state_bias_policy.py`
- `test_entry_wait_belief_bias_policy.py`
- `test_entry_wait_edge_pair_bias_policy.py`
- `test_entry_wait_probe_temperament_policy.py`
- `test_entry_wait_state_policy.py`
- `test_entry_wait_decision_policy.py`

### 기존 통합 회귀

- `test_wait_engine.py`
- `test_entry_try_open_entry_policy.py`
- `test_entry_try_open_entry_probe.py`

이 구조의 장점은 명확하다.

- helper 자체 의미를 바로 고정할 수 있다
- caller만 바뀌었는지, 의미가 바뀐 건지 구분이 쉽다
- integration 회귀가 여전히 전체 생명주기를 보호한다


## 11. W1이 실제로 해결한 것

W1은 아래 문제를 실질적으로 줄였다.

### 11-1. WaitEngine 본문 비대화

가장 큰 정책 덩어리 네 개가 밖으로 빠지면서,
엔진 본문이 훨씬 덜 무거워졌다.

### 11-2. wait 해석 owner 혼재

예전에는 state, belief, directional pair, probe scene이 본문에 섞여 있었는데,
이제는 owner가 분리되어 "어느 층의 해석인지"가 명확해졌다.

### 11-3. scene-specific 특례의 불투명성

XAU/BTC/NAS probe 관련 wait 예외가
이제 일반 wait 본문 안의 숨은 if가 아니라,
scene owner를 통해 읽히는 구조에 가까워졌다.

### 11-4. wait tuning 변경 위험

나중에 threshold나 delta를 건드릴 때도,
어느 owner를 건드리는지 범위가 더 명확해졌다.


## 12. W1이 아직 해결하지 않은 것

W1이 끝났다고 해서 wait 전체가 끝난 것은 아니다.
아직 남은 것은 성격이 다르다.

### 12-1. wait context freeze

현재는 owner가 분리되었지만,
그 owner들이 읽는 입력 문맥을 더 명시적으로 frozen contract로 만들 여지는 남아 있다.

즉 "어떤 입력 묶음을 wait context라고 볼 것인가"를 더 고정할 수 있다.

### 12-2. runtime / observability에서의 wait 해석 요약 강화

이미 recent diagnostics는 많이 생겼지만,
wait state / decision / scene 흐름을 더 묶어서 읽는 표면은 앞으로 더 보강할 수 있다.

### 12-3. exit/manage와의 대칭

entry wait는 많이 정리됐지만,
trade lifecycle 전체를 닫으려면 exit/manage도 같은 수준의 ownership 정리가 필요하다.


## 13. W1 완료의 의미

W1 완료는 "wait가 이제 끝났다"는 뜻보다,
"wait를 더 깊게 만질 수 있는 구조가 생겼다"는 뜻에 가깝다.

이제부터는 wait를 고칠 때

- state를 고치는 것인지
- belief를 고치는 것인지
- directional pair를 고치는 것인지
- probe scene 특례를 고치는 것인지

를 더 분명하게 말할 수 있다.

이게 W1의 가장 중요한 성과다.


## 14. 다음 단계가 W2인 이유

W1이 owner extraction을 끝냈다면,
그 다음 자연스러운 단계는 `W2 wait context freeze`다.

이유는 간단하다.

- W1은 "누가 해석할 것인가"를 정리했다
- W2는 "무엇을 읽고 해석할 것인가"를 더 고정하는 단계가 된다

즉 W1이 ownership 정리라면,
W2는 입력 계약과 해석 표면을 더 단단하게 만드는 단계다.


## 15. 한 줄 결론

Phase W1은 wait 레이어의 네 핵심 해석 owner를 `WaitEngine` 밖으로 분리해,
기다림을 entry 수준의 policy 구조로 끌어올린 1차 구조 정리 단계였다.
