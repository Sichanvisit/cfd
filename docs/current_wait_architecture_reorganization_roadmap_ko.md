# 기다림 레이어 상세 재정렬 로드맵

이 문서는 현재 `WaitEngine`과 entry wait 경로를
`진입 레이어와 비슷한 수준의 세밀함`으로 재정렬하기 위한 상세 로드맵이다.

핵심 목적은 3가지다.

1. 기다림의 의미를 `한 군데에서 설명 가능한 구조`로 만든다.
2. 왜 기다림이 선택됐는지를 `row/runtime/detail`에서 바로 읽을 수 있게 만든다.
3. 나중에 wait rule, semantic tuning, exit/manage를 붙일 때 같은 종류의 truth drift가 다시 생기지 않게 한다.


## 1. 왜 이제 기다림을 더 깊게 들어가야 하는가

지금 구조는 entry 쪽을 먼저 정리하면서 아래까지 이미 확보했다.

- consumer check state single owner
- blocked 의미 보존
- runtime recent diagnostics
- energy truth logging
- entry policy extraction

반면 기다림은 그에 비해 절반 정도만 정리된 상태다.

현재는 이미 다음이 되어 있다.

- `entry wait state` 본문 규칙 분리
- `entry wait decision` 본문 규칙 분리
- wait energy trace state/decision 기록
- runtime recent diagnostics에서 wait energy trace summary 노출
- entry orchestration에서 wait row/runtime payload 전달

하지만 아직 다음은 남아 있다.

- 기다림 bias 계산 owner 분리
- 기다림 context contract 고정
- wait 전용 recent summary 강화
- `consumer -> wait -> row/runtime -> chart` 연결 테스트 강화
- exit/manage와의 boundary 설계

즉 지금 기다림은
`결론을 내리는 핵심 규칙은 빠졌지만,
그 결론에 쓰이는 계산 재료와 운영 해석 표면은 아직 덜 고정된 상태`
라고 보는 것이 정확하다.


## 2. 현재 코드 상태 요약

### 2-1. 이미 분리된 것

- entry wait state policy
  - `backend/services/entry_wait_state_policy.py`
- entry wait decision policy
  - `backend/services/entry_wait_decision_policy.py`

이 둘은 이미 `WaitEngine` 밖으로 빠졌다.
즉 현재 `WaitEngine`은 예전보다 덜 비대하고,
상태 분류와 decision 선택의 핵심 본문은 shared owner를 가진다.

### 2-2. 아직 `WaitEngine` 내부에 남아 있는 것

- edge pair 기반 wait bias 계산
- belief 기반 wait bias 계산
- state 기반 wait bias 계산
- probe temperament 기반 wait bias 계산

실제로는 이 4개가 아직 `WaitEngine` 안에서
기다림의 hard/soft 성격, enter/wait utility delta, confirm release / wait lock을 만든다.

즉 지금 `WaitEngine` 안에는 여전히
`왜 기다림이 강해졌는가`의 재료 계산기가 남아 있다.

### 2-3. orchestration / runtime 연결 상태

`entry_try_open_entry.py`는 이미 다음을 하고 있다.

- wait state 계산
- wait decision 계산
- row에 `entry_wait_state`, `entry_wait_decision`, `entry_wait_value` 저장
- `entry_wait_energy_usage_trace_v1`
- `entry_wait_decision_energy_usage_trace_v1`

`trading_application.py`는 이미 다음을 하고 있다.

- recent window 기준 wait energy trace summary 재집계
- detail/slim runtime status에 요약 노출

즉 기다림은 이미 배관은 많이 깔려 있다.
문제는 배관 위에 올라가는 의미 owner가 아직 완전히 정리되지 않았다는 점이다.


## 3. 지금 기다림이 아직 entry parity가 아닌 이유

### 3-1. bias owner가 엔진 내부에 남아 있다

entry는 최근 Phase 4에서
probe plan, default side gate, energy relief, handoff fallback 같은 정책 덩어리를 밖으로 뺐다.

기다림은 아직

- state wait bias
- belief wait bias
- edge pair wait bias
- probe temperament

이 네 덩어리가 엔진 내부 helper로 남아 있다.

이 상태가 오래 가면 생기는 문제는 명확하다.

- 새 wait rule을 넣을 때 수정 위치가 다시 `WaitEngine` 내부 조건문으로 몰린다.
- 나중에 belief/state/edge-pair 튜닝이 커질수록 함수가 비대해진다.
- 테스트는 통과해도 owner boundary가 약해서 handoff 품질이 떨어진다.

### 3-2. wait context 자체가 아직 고정 contract가 아니다

현재는 row/payload를 읽어 `WaitEngine`이 내부적으로 필요한 값들을 재구성한다.
이 방식은 당장은 동작하지만,
나중에 wait meaning을 더 세밀하게 설명하려면
`기다림 판단에 실제로 투입된 입력 묶음`이 별도 contract로 남는 편이 더 좋다.

예를 들면 다음 같은 묶음이다.

- 현재 액션/방향 문맥
- observe reason / blocked reason / action none reason
- core/preflight allowed action
- setup status / trigger 상태
- wait score / conflict / noise / penalty
- energy helper hints
- belief/state/edge-pair/probe bias 결과

지금은 이 값들이 metadata와 local variables에 흩어져 있다.

### 3-3. recent diagnostics는 energy에는 강하지만 wait semantic에는 아직 약하다

지금 runtime detail에서는
wait energy trace summary를 꽤 잘 볼 수 있다.

하지만 아직 아래 질문에는 바로 답하기 어렵다.

- 최근 wait state 분포는 어떤가
- 어떤 wait state가 hard wait로 잠겼는가
- 어떤 bias owner가 wait lock을 많이 만들었는가
- helper wait보다 belief wait lock이 늘었는가
- policy block wait와 structural wait가 어떻게 섞였는가

즉 energy trace summary는 생겼지만,
`wait meaning summary`는 아직 약하다.

### 3-4. end-to-end 계약 테스트가 더 필요하다

현재 테스트는 꽤 좋아졌다.

- helper 직접 테스트
- `WaitEngine` unit tests
- entry orchestration 일부 회귀

하지만 entry parity를 말하려면 더 필요한 계약이 있다.

- 특정 consumer/blocked 상황이 특정 wait state로 가는가
- 그 wait state가 특정 wait decision으로 이어지는가
- 그 결과가 row/runtime에 같은 의미로 남는가
- recent aggregation에서 그 의미가 제대로 집계되는가


## 4. 기다림을 entry parity로 본다는 것은 무엇을 뜻하는가

이 문서에서 말하는 `entry parity`는 기능 숫자가 같다는 뜻이 아니다.
아래 7개 조건을 만족하는 상태를 뜻한다.

1. 기다림 상태 본문 owner가 한 군데다.
2. 기다림 선택 본문 owner가 한 군데다.
3. 기다림 bias owner도 분리돼 있다.
4. row/runtime/detail에서 기다림의 원인을 바로 읽을 수 있다.
5. 최근 window 기준 wait semantic 요약이 있다.
6. entry orchestration과 wait meaning이 같은 계약으로 연결된다.
7. exit/manage 확장 시 재사용 가능한 boundary가 있다.


## 5. 목표 구조

목표 구조는 아래처럼 보는 것이 좋다.

### 5-1. 입력 정리층

entry row/payload에서
기다림 판단에 필요한 입력을 표준화한다.

예:

- action context
- wait score family
- observe / block / none 이유
- energy helper hints
- consumer/layer mode 결과
- belief/state/edge-pair/probe 보정

### 5-2. bias 계산층

각 owner가 wait에 얼마나 영향을 주는지 독립 계산한다.

- state owner
- belief owner
- edge pair owner
- probe temperament owner

### 5-3. wait state policy 층

현재가 `CENTER`, `CONFLICT`, `EDGE_APPROACH`, `HELPER_SOFT_BLOCK`, `POLICY_BLOCK` 같은
어떤 기다림 상태인지 정한다.

### 5-4. wait decision policy 층

이 상태에서 실제로 enter보다 wait가 더 낫다고 볼지 정한다.

### 5-5. 운영 표면층

row/runtime/detail/handoff에서
사람이 읽을 수 있는 형태로 요약한다.


## 6. 단계별 로드맵

아래 순서가 가장 안전하다.

---

## Phase W1. Bias Owner Extraction

### 목표

현재 `WaitEngine` 내부에 남아 있는 4개 bias 계산기를 shared owner로 뺀다.

### 대상

- state wait bias
- belief wait bias
- edge pair wait bias
- probe temperament

### 권장 파일 구조

- `backend/services/entry_wait_state_bias_policy.py`
- `backend/services/entry_wait_belief_bias_policy.py`
- `backend/services/entry_wait_edge_pair_bias_policy.py`
- `backend/services/entry_wait_probe_temperament_policy.py`

### 완료 기준

- `WaitEngine`은 bias 계산을 직접 하지 않고 helper 결과를 받아 쓴다.
- helper 직접 unit test가 생긴다.
- 기존 `test_wait_engine.py` 회귀가 그대로 녹색이다.

### 기대 효과

- 기다림의 재료 계산과 본문 판단이 분리된다.
- belief/state tuning이 wait 본문과 섞이지 않는다.
- 이후 semantic tuning과 직접 연결하기 쉬워진다.

---

## Phase W2. Wait Context Contract Freeze

### 목표

기다림 판단에 실제로 들어간 입력 묶음을 하나의 contract로 고정한다.

### 권장 이름

- `entry_wait_context_v1`

### 이 contract에 담을 것

- directional/action context
- observe/block/action-none reason split
- wait score family
- energy helper hints
- policy/layer mode wait hints
- bias outputs

### 완료 기준

- `build_entry_wait_state_from_row()`가 내부 로컬 변수보다 context contract를 중심으로 읽는다.
- metadata에 최소한 compact version이 남는다.
- 나중에 row replay나 diagnostics에서 같은 묶음을 재사용할 수 있다.

### 기대 효과

- “왜 이 wait였는가”를 재현하기 쉬워진다.
- 입력과 해석이 분리돼 handoff가 쉬워진다.

---

## Phase W3. Wait Runtime Observability 강화

### 목표

energy trace 요약을 넘어
`wait semantic 자체의 recent summary`를 추가한다.

### 추가 후보

- 최근 window별 `wait_state_counts`
- `hard_wait_state_counts`
- `wait_decision_counts`
- `wait_policy_hint_counts`
- `wait_bias_lock_counts`
- `wait_release_counts`
- symbol별 wait semantic summary

### 특히 가치가 큰 항목

- `belief_prefer_wait_lock`가 최근 얼마나 많았는가
- `state_prefer_confirm_release`가 실제 hard wait를 얼마나 풀었는가
- `policy block`이 wait selected로 이어진 비중
- `helper soft block`이 state에서만 끝났는지 decision까지 갔는지

### 완료 기준

- `runtime_status.detail.json`만 봐도 최근 wait 성향을 설명할 수 있다.
- CSV를 직접 뒤지는 빈도가 줄어든다.

---

## Phase W4. Wait End-to-End Contract Test 확장

### 목표

`consumer -> wait state -> wait decision -> row/runtime` 연속 계약을 테스트로 잠근다.

### 필요 테스트 형태

1. blocked/observe row 입력
2. 특정 bias owner 활성화
3. 예상 wait state
4. 예상 wait decision
5. row/runtime에 동일 값 저장

### 완료 기준

- helper 단위 테스트뿐 아니라 orchestration 연속 테스트가 생긴다.
- 새로운 wait rule 추가 시 회귀 리스크가 줄어든다.

---

## Phase W5. Wait Surface/Handoff 마감

### 목표

새 스레드나 운영자가
wait meaning을 CSV 없이 바로 읽을 수 있게 문서와 표면을 맞춘다.

### 포함할 것

- wait states 읽는 법
- hard wait / soft wait 차이
- bias owner별 해석 가이드
- recent diagnostics 해석 예시
- “과보수 wait” 판단 루틴

### 완료 기준

- handoff 문서에서 wait를 별도 절로 설명할 수 있다.
- 새 스레드에서 “지금 왜 wait가 많은가”를 5분 안에 판단할 수 있다.

---

## Phase W6. Exit/Manage 연결 준비

### 목표

entry wait와 exit wait/hold가 같은 언어로 이어지도록 준비한다.

여기서 바로 exit 전체를 다 고치자는 뜻은 아니다.
대신 다음을 정리해 두는 단계다.

- entry wait와 exit wait의 공통 개념
- 기다림 quality 판단을 어디까지 공유할지
- hold / wait_exit / reverse와 어떤 contract를 공유할지

### 완료 기준

- exit/manage를 시작할 때 재사용할 owner 경계가 정의돼 있다.


## 7. 가장 추천하는 실제 실행 순서

지금부터 바로 실행한다면 이 순서를 추천한다.

1. `W1-1` state wait bias extraction
2. `W1-2` belief wait bias extraction
3. `W1-3` edge pair wait bias extraction
4. `W1-4` probe temperament extraction
5. `W2` wait context contract freeze
6. `W3` recent wait semantic summary 추가
7. `W4` end-to-end contract tests
8. `W5` handoff/runtime 읽기 가이드 마감
9. `W6` exit/manage 연결 설계

이 순서가 좋은 이유는
지금 막 분리한 wait state/decision owner 위에
남은 bias owner를 먼저 정리해야
그 다음 observability와 tests가 안정되기 때문이다.


## 8. 무엇을 지금 건드리지 말아야 하나

### 8-1. exit utility decision 전체를 같이 뜯지 말 것

entry wait 정리와 exit utility 정리를 한 번에 섞으면 범위가 너무 커진다.
이번 wait roadmap의 1차 목적은
`entry wait`를 entry parity 수준으로 끌어올리는 것이다.

### 8-2. chart 의미까지 동시에 재설계하지 말 것

chart에는 이미 directional wait, neutral wait, blocked/ready/probe 번역 규칙이 있다.
wait 내부 semantic owner를 고정하기 전에 chart 의미까지 같이 흔들면 확인 비용이 급격히 커진다.

### 8-3. ML calibration과 구조 extraction을 섞지 말 것

지금은 구조 정리 단계다.
weight tuning, threshold tuning, semantic calibration은
owner가 정리된 뒤에 하는 편이 훨씬 안전하다.


## 9. 이 작업을 하지 않으면 어떻게 되나

기능은 당장 돌아간다.
문제는 이후 비용이다.

- wait rule이 늘수록 `WaitEngine` 내부가 다시 비대해진다.
- tuning이 많아질수록 왜 wait가 늘었는지 추적 비용이 커진다.
- semantic/belief/state가 wait에 준 영향을 설명하기 어려워진다.
- entry는 투명한데 wait는 덜 투명한 비대칭 상태가 오래간다.
- 결국 exit/manage를 붙일 때 다시 boundary confusion이 생긴다.

즉 지금의 핵심 리스크는
“기다림이 틀렸다”가 아니라
“기다림이 앞으로 커질수록 설명 가능한 구조로 남아 있지 않을 수 있다”는 점이다.


## 10. 현재 기준 객관적 평가

### 이미 꽤 잘 된 부분

- wait energy truth logging
- state/decision owner 1차 분리
- orchestration 연결
- runtime recent energy trace summary
- helper 직접 테스트 + `WaitEngine` 회귀

### 아직 덜 구축된 부분

- bias owner extraction
- wait context freeze
- recent wait semantic summary
- end-to-end contract tests
- wait 전용 운영 가이드

### 종합 판단

지금 기다림은
`대충 붙어 있는 상태`는 이미 지나갔다.
하지만 아직 `진입만큼 구조가 고정된 상태`도 아니다.

따라서 다음 단계는 튜닝보다
`남은 owner를 세밀하게 분리하고, 의미 표면을 고정하는 작업`
이 우선이다.


## 11. 바로 다음 액션

가장 바로 들어가기 좋은 것은 `Phase W1-1`이다.

즉:

- `state wait bias`를 helper owner로 추출
- direct unit test 추가
- `WaitEngine` 연결
- 기존 wait 회귀 확인

이걸 시작점으로 잡으면
이후 `belief -> edge pair -> probe temperament` 순으로 같은 패턴을 반복할 수 있다.
