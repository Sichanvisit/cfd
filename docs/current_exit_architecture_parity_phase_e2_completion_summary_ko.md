# 청산 구조 정렬 Phase E2 완료 요약

작성일: 2026-03-29 (KST)
현재 상태: E2 구현 완료, 다음 단계는 E3 exit utility decision policy 분리

## 1. 이 문서의 목적

이 문서는 Phase E2가 실제로 어디까지 닫혔는지 한 장으로 정리하는 완료 문서다.

핵심 질문은 하나다.

`청산 wait state가 이제 entry / wait 쪽처럼 입력 계약, base state, rewrite, surface contract로 나뉘어 있는가?`


## 2. 결론

결론은 `예`에 가깝다.

E2를 통해 청산 wait state 축은 다음 4층으로 분리되었다.

1. 입력 계약
2. base state policy
3. rewrite policy
4. surface / metadata contract

즉 `WaitEngine.build_exit_wait_state(...)`는 더 이상 모든 의미를 한 함수 안에서 직접 만들지 않고,
분리된 owner 결과를 조합하는 구조로 한 단계 올라왔다.


## 3. 이번 단계에서 실제로 생긴 것

### 3-1. 입력 계약이 얼었다

청산 wait state가 읽는 입력은 이제 canonical input contract를 통해 정리된다.

이 계약 안에는 아래가 들어간다.

- symbol, entry direction, entry setup
- regime / box / bb 위치
- profit, peak profit, giveback, duration
- adverse risk, tf confirm, score gap
- recovery policy resolved values
- state / belief / symbol edge bias 입력
- exit/manage canonical context compact surface

이제 청산 wait state가 무엇을 읽고 있는지 먼저 계약으로 고정한 뒤,
그 계약을 policy layer가 소비하는 순서가 만들어졌다.


### 3-2. base state policy가 분리됐다

이전에는 `WaitEngine` 본문이 직접

- reversal confirm
- active observe
- recovery TP1
- recovery BE
- reverse ready
- cut immediate
- green close
- none

를 고르고 있었다.

지금은 이 선택이 별도 owner에서 이루어진다.

즉 `어떤 장면이면 기본적으로 어떤 청산 wait state가 먼저 잡히는가`
라는 질문이 독립 policy로 분리됐다.


### 3-3. rewrite policy가 분리됐다

기본 state가 잡힌 뒤,

- green close를 hold bias로 active로 바꾸는지
- belief hold extension이 active hold로 넘기는지
- symbol edge hold bias가 opposite edge까지 들고 가는지
- recovery / none 상태를 fast-cut bias가 cut-immediate로 바꾸는지

를 결정하는 rewrite가 따로 빠졌다.

그래서 이제 `처음 잡힌 상태`와 `나중에 bias 때문에 바뀐 상태`를 구분해서 읽을 수 있다.


### 3-4. surface / metadata contract가 분리됐다

청산 wait state는 이제 단순히 `state, reason`만 남기지 않는다.

별도 surface contract가 아래를 함께 묶어준다.

- 최종 state / reason / hard wait
- base state / base reason / base matched rule
- rewrite applied 여부 / rewrite rule
- score / penalty
- recovery policy id
- allow wait BE / TP1 / prefer reverse
- regime / box / bb / profit / giveback / duration
- 핵심 bias flags

즉 이제 `왜 이 wait state가 보였는가`를 한 계약으로 읽을 수 있다.


## 4. runtime 표면에서는 무엇이 달라졌나

이번 단계는 내부 구조만 정리한 것이 아니라,
runtime 표면에도 바로 읽히는 shape를 같이 붙였다.

이제 compact runtime row에서는 아래가 직접 보인다.

- `exit_wait_state_surface_v1`
- `exit_wait_base_state`
- `exit_wait_base_reason`
- `exit_wait_rewrite_applied`
- `exit_wait_rewrite_rule`
- `exit_wait_score`
- `exit_wait_penalty`
- `exit_wait_recovery_policy_id`

즉 새 스레드나 운영 점검에서
청산 wait state를 볼 때도 이제
`최종 상태만 보고 추정`하지 않고
`base -> rewrite -> surface` 순으로 읽을 수 있다.


## 5. E2가 해결한 것

E2가 해결한 핵심은 세 가지다.

### 5-1. 청산 wait state의 의미가 층으로 분리됐다

이전에는 입력 해석, base state, rewrite, metadata가 한 함수 안에 섞여 있었고,
scene이 늘수록 `WaitEngine` exit path가 다시 비대해질 위험이 컸다.

지금은 적어도 청산 wait state 축에서는
`입력 -> base state -> rewrite -> surface` 흐름이 분리되어 있다.


### 5-2. base truth와 rewritten truth를 구분할 수 있게 됐다

이전에는 최종 상태만 남고,
그게 처음부터 그 상태였는지 아니면 bias 때문에 바뀐 상태인지가 숨기 쉬웠다.

지금은 `base_state`, `rewrite_applied`, `rewrite_rule`이 같이 남기 때문에
이 구분이 가능하다.


### 5-3. downstream read path가 더 안정적이 되었다

compact/runtime surface가 contract를 직접 읽게 되면서,
앞으로 recent summary나 handoff 문서가 이 표면을 기준으로 읽기 쉬워졌다.

즉 E2는 단순 리팩터링이 아니라
다음 단계 E3 / E4 / E5가 붙을 수 있는 안정된 바닥을 만든 단계다.


## 6. 아직 E2가 하지 않은 것

E2는 청산 wait state 축을 닫은 단계이지,
청산 decision 전체를 끝낸 단계는 아니다.

아직 남은 것은 아래다.

- utility 계산 본체 분리
- recovery utility / symbol bias / reverse eligibility owner 분리
- final winner / reason / taxonomy builder 분리
- manage execution seam slimming
- end-to-end contract close-out 문서와 가이드

즉 E2는 `청산 state engine 정리`,
E3는 `청산 decision engine 정리`,
E4는 `manage execution seam 정리`로 보는 것이 맞다.


## 7. 완료 선언 조건 점검

E2는 아래 조건을 충족하므로 완료로 봐도 된다.

1. 청산 wait 입력 계약이 분리되어 있다.
2. base state policy가 분리되어 있다.
3. rewrite policy가 분리되어 있다.
4. surface / metadata contract가 분리되어 있다.
5. runtime compact surface가 새 contract를 읽는다.
6. direct helper 테스트와 `WaitEngine` 회귀가 통과했다.


## 8. 다음 단계

이제 가장 자연스러운 다음 단계는 E3다.

즉 `WaitEngine.evaluate_exit_utility_decision(...)` 안에 남아 있는

- base exit utility 계산
- recovery utility 계산
- symbol / setup special bias
- reverse eligibility 판단
- final winner / reason / taxonomy 연결

을 분리하는 작업이다.

한 줄로 정리하면 이렇다.

`E2로 청산 wait state는 entry / wait급 구조의 바닥을 확보했고, 다음은 청산 utility decision을 같은 수준으로 분리하는 단계다.`
