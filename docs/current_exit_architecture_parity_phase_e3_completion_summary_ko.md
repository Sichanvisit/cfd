# 청산 구조 정렬 Phase E3 완료 요약

작성일: 2026-03-29 (KST)
현재 상태: E3 구현 완료, 다음 큰 축은 E4 manage execution seam 정리

## 1. 이 문서의 목적

이 문서는 Phase E3가 실제로 어디까지 닫혔는지 한 장으로 정리하는 완료 문서다.

핵심 질문은 하나다.

`청산 utility decision이 이제 entry / wait 때처럼 입력 계약, 후보 bundle, 장면 bias, 최종 decision owner로 나뉘어 있는가?`


## 2. 결론

결론은 `예`에 가깝다.

E3를 통해 청산 utility decision 축은 아래 5층으로 분리되었다.

1. utility input contract
2. base utility bundle
3. recovery utility / reverse eligibility
4. scene bias bundle
5. final winner / decision policy

즉 `WaitEngine.evaluate_exit_utility_decision(...)`는 더 이상
청산 decision의 거의 모든 의미를 본문 안에서 직접 만들지 않고,
분리된 owner 결과를 조합하는 구조로 올라왔다.


## 3. 이번 단계에서 실제로 생긴 것

### 3-1. utility input contract가 생겼다

청산 utility가 읽는 입력은 이제 먼저 contract로 정리된다.

여기에는 아래 층이 담긴다.

- symbol / state / exit profile / entry direction / entry setup
- profit / peak profit / giveback / duration / adverse risk / score gap
- regime / box / bb 위치
- allow wait / prefer reverse / recovery policy / reverse threshold
- state execution bias
- compact exit wait state surface

이 변화의 의미는 크다.
이제 `청산 decision이 무엇을 입력으로 보고 있는가`를
먼저 계약으로 고정한 뒤,
그 입력을 각 owner가 순차적으로 소비하는 구조가 됐다.


### 3-2. base utility bundle이 분리됐다

이전에는 `WaitEngine` 본문이 직접

- exit now utility
- hold utility
- reverse utility
- wait-exit utility

를 계산하고 있었다.

지금은 이 1차 후보가 별도 bundle로 분리된다.

여기서 함께 고정되는 값은 대략 아래와 같다.

- locked profit
- upside
- giveback cost
- reverse edge
- wait improvement
- wait miss cost
- wait extra penalty

즉 이제 `기본 점수판이 어떻게 만들어졌는가`를
하나의 owner로 읽을 수 있다.


### 3-3. recovery utility와 reverse eligibility가 분리됐다

이전에는 recovery wait 후보와 reverse 가능 여부가
scene bias와 final decision 사이에 섞여 있었다.

지금은 아래가 별도 owner에서 만들어진다.

- cut-now utility
- wait-BE utility
- wait-TP1 utility
- reverse candidate utility
- allow wait BE / TP1의 effective 상태
- tight-protect green peak disable
- reverse eligibility
- reverse가 왜 막혔는지의 이유

그래서 이제 `recovery 후보가 왜 생겼는가`,
`reverse가 왜 비활성화됐는가`를 helper 결과로 직접 읽을 수 있다.


### 3-4. scene / symbol / setup bias가 bundle로 분리됐다

이전에는 청산 utility의 장면 특례가 본문 곳곳에 흩어져 있었다.

지금은 아래 장면이 하나의 bundle로 묶인다.

- range middle hold bias
- opposite edge completion bias
- lower reversal hold bias
- XAU lower edge-to-edge hold bias
- BTC upper tight / support bounce bias
- BTC lower hold bias
- BTC lower mid-noise hold bias
- NAS upper hold bias

즉 `왜 특정 symbol / scene에서 exit-now가 강화되거나 hold가 완화됐는가`
를 scene bundle 하나로 볼 수 있게 됐다.


### 3-5. 최종 winner / reason / wait-selected가 별도 policy로 분리됐다

마지막으로 최종 winner 선택도 별도 owner로 분리됐다.

이 policy는 아래를 담당한다.

- recovery path winner 선택
- profit / green path winner 선택
- priority 규칙 적용
- decision reason 부여
- wait selected / wait decision 판단
- taxonomy 입력 shaping

즉 이제 `최종적으로 왜 wait_be가 이겼는가`,
`왜 exit_now_support_bounce가 됐는가`를
최종 decision owner 기준으로 읽을 수 있다.


## 4. runtime 표면에서는 무엇이 달라졌나

이번 단계는 내부 구조만 나눈 것이 아니다.
runtime payload에도 새 contract가 같이 실리기 시작했다.

이제 청산 utility 결과에는 아래가 함께 남는다.

- `exit_utility_input_v1`
- `exit_utility_base_bundle_v1`
- `exit_recovery_utility_bundle_v1`
- `exit_reverse_eligibility_v1`
- `exit_utility_scene_bias_bundle_v1`
- `exit_utility_decision_policy_v1`

즉 새 스레드나 디버깅에서는
이제 최종 winner만 보는 것이 아니라,

`input -> base -> recovery -> scene -> final decision`

흐름을 따라가며 읽을 수 있다.


## 5. E3가 해결한 것

E3가 해결한 핵심은 세 가지다.

### 5-1. 청산 decision의 owner 경계가 선명해졌다

이전에는 청산 utility decision이
상태 해석 이후 다시 큰 함수 중심으로 뭉쳐 있었다.

지금은 적어도 청산 decision 축에서는
입력, base 후보, recovery 후보, scene bias, final decision이
서로 다른 owner를 갖는다.


### 5-2. 최근 summary와 내부 owner가 더 잘 연결되기 시작했다

이전에는 recent exit summary는 읽히더라도,
내부에서 왜 그런 분포가 나왔는지는 다시 큰 함수 안으로 내려가야 했다.

지금은

- recovery wait 증가
- reverse 차단
- scene-specific exit_now 강화

같은 현상을 owner별 helper surface로 직접 추적할 수 있다.


### 5-3. 청산도 entry / wait와 비슷한 구조 밀도를 갖기 시작했다

이전에는 청산 observability는 빠르게 좋아졌지만,
core policy owner 분리는 entry / wait보다 뒤처져 있었다.

E3를 통해 청산도
`input -> policy/bundle -> final surface`
형태를 갖추기 시작했다.


## 6. 아직 E3가 하지 않은 것

E3는 청산 decision engine을 정리한 단계이지,
청산 lifecycle 전체를 마감한 단계는 아니다.

아직 남은 것은 아래다.

- manage execution seam 정리
- execution loop의 input / policy surface / action branch 분리
- trade logger / live metrics / runtime sink 정리
- recovery reverse execution과 concrete action path 분리
- close-out 문서와 read path 마감

즉 E3는 `청산 decision engine 정리`,
E4는 `청산 manage execution seam 정리`로 보는 것이 맞다.


## 7. 완료 선언 조건 점검

E3는 아래 조건을 충족하므로 완료로 봐도 된다.

1. utility input contract가 분리되어 있다.
2. base utility bundle이 분리되어 있다.
3. recovery utility와 reverse eligibility가 분리되어 있다.
4. scene bias bundle이 분리되어 있다.
5. final winner / reason / wait-selected policy가 분리되어 있다.
6. direct helper 테스트와 `WaitEngine` 회귀가 통과했다.


## 8. 다음 큰 축

이제 가장 자연스러운 다음 단계는 E4다.

즉 `exit_manage_positions.py` 안에 남아 있는

- runtime / logger / live metric 조립
- recovery execution branch
- hard guard branch
- partial close / stop-up / protect / lock / reverse action

를 execution seam 기준으로 나누는 작업이다.

한 줄로 정리하면 이렇다.

`E3로 청산 decision engine은 entry / wait급 구조 밀도에 가까워졌고, 다음은 manage loop를 execution seam 기준으로 얇게 만드는 단계다.`
