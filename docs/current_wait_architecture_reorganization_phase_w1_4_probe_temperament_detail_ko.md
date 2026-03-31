# 기다림 재정리 W1-4 Probe Temperament 상세 문서

부제: scene-specific probe 장면을 일반 wait와 구분해 해석하는 owner 분리 가이드

작성일: 2026-03-27 (KST)

## 진행 상태 (2026-03-27)

현재 이 슬라이스는 구현과 핵심 회귀 검증까지 완료된 상태다.

- `entry_wait_probe_temperament_policy.py` 추가
- `WaitEngine` probe temperament caller 치환 완료
- direct helper tests 추가
- `test_wait_engine.py` 통과
- `test_entry_try_open_entry_policy.py` 통과
- `test_entry_try_open_entry_probe.py` 통과

## 1. 문서 목적

이 문서는 `W1-4 probe temperament extraction`에 들어가기 전에,
현재 `WaitEngine` 안에 남아 있는 probe 장면 해석 로직이 실제로 무엇을 보호하고 있는지 고정하기 위한 상세 문서다.

이번 슬라이스는 단순히 scene id를 읽어오는 helper 분리가 아니다.
현재 owner는 아래 질문에 답하고 있다.

- 지금 이 row가 일반적인 wait 장면인가, 아니면 probe 장면인가
- probe 장면이라면 얼마나 성급하게 기다림을 고수하면 안 되는가
- 아직 ready가 아니어도 이 장면을 일반 center/noise wait처럼 취급하면 안 되는가
- ready가 된 뒤에는 wait보다 enter 쪽을 더 보도록 완화해야 하는가

즉 이 helper는 "probe 장면을 wait 해석 언어로 번역하는 owner"에 가깝다.


## 2. 현재 owner가 있는 위치

- 현재 owner: `backend/services/wait_engine.py`
- 현재 함수: `_entry_symbol_probe_temperament(...)`

이 함수는 `WaitEngine` 안에 있지만,
역할상으로는 조합기 본문이라기보다 scene-specific wait policy helper에 가깝다.


## 3. 이 owner가 현재 하는 일

현재 로직은 크게 다섯 단계로 움직인다.

### 3-1. probe 장면 관련 원천을 읽는다

먼저 현재 row 안에서 probe 관련 정보를 읽는다.

- 이미 만들어진 probe plan
- 아직 후보 단계에 있는 probe candidate
- observe-confirm metadata

이때 중요한 점은 source가 하나가 아니라는 것이다.
이미 plan으로 확정된 경우도 있고,
candidate/observe 쪽에만 흔적이 남아 있는 경우도 있다.

즉 이 helper는 단순히 scene id 하나만 읽는 것이 아니라,
"현재 probe 장면의 유효한 원천이 어디에 있는가"를 먼저 정리한다.

### 3-2. 이 row가 실제 probe 장면인지 판정한다

그다음에는 symbolic probe temperament payload가 실제로 있는지 본다.
없으면 일반 wait 흐름으로 돌리고,
있으면 probe 장면으로 취급한다.

이 단계의 의미는 아주 크다.

> 일반 wait와 probe wait를 같은 언어로 읽어버리면,
> 원래는 "기다림 중이지만 probe로 이미 진입 쪽 긴장이 생긴 장면"을
> 단순 소음 대기로 오해할 수 있다.

### 3-3. 장면의 준비 상태를 함께 읽는다

현재 owner는 scene id만 보지 않는다.
함께 읽는 핵심 상태는 아래와 같다.

- 현재 probe가 active인지
- 실제 ready_for_entry까지 왔는지
- 어느 trigger branch에서 왔는지

즉 "어떤 장면인가"와 "그 장면이 얼마나 진행됐는가"를 같이 읽는다.

### 3-4. 공용 scene map을 wait 해석으로 변환한다

scene id와 ready 상태가 정리되면,
shared symbol temperament map에서 wait용 temperament를 읽는다.

여기서 실제로 만들어지는 의미는 아래와 같다.

- enter 쪽 가치를 얼마나 올리거나 내릴지
- wait 쪽 가치를 얼마나 올리거나 내릴지
- confirm release를 선호하는지
- wait lock을 선호하는지

이 단계가 중요하다.
왜냐하면 probe 장면은 "기다림 자체를 없애는 것"이 아니라,
"일반 wait보다 enter 쪽 긴장을 더 높게 보는 것"인 경우가 많기 때문이다.

### 3-5. scene-specific 예외를 metadata로 남긴다

마지막으로 helper는 장면 설명용 metadata도 함께 남긴다.

- scene id
- promotion bias
- entry style hint
- note
- source map id

즉 이 owner는 단순히 delta만 계산하지 않고,
"왜 이 wait가 일반 wait와 다르게 해석됐는지"를 설명 가능한 형태로 남긴다.


## 4. 이 owner가 구조적으로 중요한 이유

probe temperament는 wait 레이어 안에서
"scene exception interpreter" 역할을 한다.

state bias는 환경의 질감을 읽고,
belief bias는 thesis 강도를 읽고,
edge-pair bias는 방향성 경쟁 해소 여부를 읽는다.

probe temperament는 그 위에,
"이 장면은 일반 wait처럼 다루면 안 되는 특수 진입 준비 장면인가"를 읽는다.

즉 probe temperament는 quality나 direction보다
"장면 문맥의 특례성"을 해석하는 owner다.


## 5. 현재 코드가 보호하고 있는 대표 장면

이번 슬라이스에서 가장 중요한 것은,
현재 로직이 보호하고 있는 장면을 잃지 않는 것이다.

### 5-1. XAU second support probe

이 장면은 일반적인 lower/mid 대기처럼 뭉개지면 안 된다.

현재 회귀가 보호하는 의미는 아래와 같다.

- wait state가 `CENTER`나 단순 noise 대기로 떨어지지 않아야 한다
- 장면은 `ACTIVE` 쪽으로 살아 있어야 한다
- decision 단계에서도 "그냥 wait 선호"로 바로 기울면 안 된다

즉 이 장면은
"아직 관찰 중이지만 진입 준비가 시작된 특수 lower rebound 장면"으로 해석되어야 한다.

### 5-2. XAU upper sell probe

이 장면도 위쪽 reject probe라는 특수성이 유지되어야 한다.

현재 회귀가 보호하는 의미는 아래와 같다.

- 일반 center/noise wait로 떨어지지 않아야 한다
- wait state는 `ACTIVE`로 살아 있어야 한다
- decision이 바로 wait 쪽으로 기울지 않아야 한다

즉 이 장면 역시
"관찰 상태이지만 directional probe가 이미 의미를 가진 장면"으로 보존되어야 한다.

### 5-3. BTC conservative lower probe

이 장면은 ready 상태에 따라 wait 성향이 바뀐다.

- ready 전에는 여전히 보수적 wait가 강할 수 있다
- ready 이후에는 wait lock을 유지하지 않고 중립 또는 완화 쪽으로 옮겨간다

즉 probe temperament는 scene id만 읽는 owner가 아니라,
scene progression까지 읽는 owner여야 한다.

### 5-4. NAS clean confirm probe

이 장면도 ready 여부에 따라
confirm release를 줄지 말지가 바뀐다.

그래서 helper는 "scene + ready 상태"의 조합을 책임져야 한다.


## 6. 왜 이 owner를 WaitEngine 밖으로 빼야 하나

### 6-1. 장면 특례는 본문보다 policy owner에 가까워서

probe temperament는 계산량이 많지는 않지만,
의미상으로는 `WaitEngine` 본문보다 policy map 해석에 가깝다.

이 로직이 엔진 본문 안에 남아 있으면,
나중에 장면이 하나 더 추가될 때마다 본문이 조금씩 scene switchboard처럼 변한다.

### 6-2. symbol temperament map과 ownership을 맞추기 위해서

이미 shared symbol temperament map은 따로 존재한다.
그렇다면 wait 쪽에서 그 map을 읽어 해석하는 owner도
독립 helper로 두는 편이 경계가 더 자연스럽다.

한쪽은 "scene definition",
다른 한쪽은 "wait interpretation"이 되면 구조가 깔끔해진다.

### 6-3. entry parity를 맞추기 위해서

entry 쪽은 scene-specific probe policy가 이미 밖으로 많이 빠졌다.
wait도 진입만큼 세밀하게 가려면,
scene-specific wait exception도 독립 owner가 되어야 한다.


## 7. 구현 시 유지해야 할 핵심 철학

이번 extraction의 목적은 behavior redesign이 아니다.
scene-specific wait 특례를 잃지 않고 owner만 분리하는 것이 목적이다.

특히 아래 원칙은 유지되어야 한다.

- XAU second support probe는 일반 center/noise wait로 뭉개지지 않는다
- XAU upper sell probe도 일반 noise wait로 뭉개지지 않는다
- ready 여부에 따라 scene-specific wait/enter delta가 달라지는 계약은 유지한다
- metadata에 남는 probe 설명 shape는 최대한 보존한다
- state policy가 읽는 `xau_second_support_probe`, `xau_upper_sell_probe` 성격은 깨지지 않아야 한다


## 8. 권장 새 owner 형태

### 권장 파일

- `backend/services/entry_wait_probe_temperament_policy.py`

### 권장 public 함수

- `resolve_entry_wait_probe_temperament_v1(...) -> dict`

이 helper는 scene id와 ready 상태를 받아
wait용 probe interpretation payload를 반환하는 owner가 되면 좋다.


## 9. 권장 입력 형태

새 helper는 아래 성격의 입력을 받는 것이 좋다.

- 원본 payload
- 이미 읽은 observe-confirm payload

이유는 scene 관련 정보가 아래 여러 위치에 흩어져 있기 때문이다.

- `entry_probe_plan_v1`
- `probe_candidate_v1`
- observe-confirm metadata

helper 안에서 해야 할 일은 다음 정도로 제한하는 것이 좋다.

1. probe plan / candidate / observe metadata를 정리한다
2. symbol probe temperament payload를 찾는다
3. active / ready / trigger branch를 읽는다
4. shared wait temperament map을 조회한다
5. wait용 interpretation payload를 반환한다


## 10. 권장 출력 형태

현재 downstream 호환성을 위해
출력은 아래 의미를 유지하는 편이 좋다.

- probe 장면이 실제로 있었는지
- scene id
- promotion bias
- active 여부
- ready_for_entry 여부
- trigger branch
- enter value delta
- wait value delta
- confirm release 선호 여부
- wait lock 선호 여부
- entry style hint
- note
- source map id

핵심은 단순 숫자보다
"이 row가 왜 probe 특례로 해석됐는지"를 설명할 수 있는 metadata를 계속 남기는 것이다.


## 11. shared symbol temperament map과의 관계

이번 helper는 shared symbol temperament map을 대체하는 것이 아니다.
역할은 아래처럼 나뉘는 편이 좋다.

- `symbol_temperament.py`
  - scene definition
  - scene별 wait temperament 기본값/ready override
- 새 wait helper
  - row 안의 probe 문맥을 읽는다
  - 어떤 scene가 실제로 활성화됐는지 정리한다
  - 그 scene를 wait 해석 payload로 번역한다

즉 map 자체와 map을 언제 어떻게 적용할지는 owner를 분리하는 편이 더 명확하다.


## 12. 기존 회귀와 직접 연결되는 포인트

이번 슬라이스는 아래 기존 회귀와 직접 연결된다.

- `tests/unit/test_wait_engine.py`
  - XAU second support probe가 `ACTIVE`로 남는지
  - XAU second support probe에서 decision이 바로 wait 선호로 기울지 않는지
  - XAU upper sell probe가 `ACTIVE`로 남는지
  - XAU upper sell probe에서 decision이 바로 wait 선호로 기울지 않는지

이 테스트들이 의미하는 것은 단순하다.

> probe 장면은 일반 wait와 같은 언어로 뭉개지면 안 된다.


## 13. direct helper 테스트에서 꼭 잡아야 할 장면

새 helper 전용 테스트는 최소한 아래 장면을 포함하는 것이 좋다.

### 13-1. probe 정보 자체가 없는 경우

기대 결과:

- neutral default
- present false

### 13-2. XAU second support probe relief 장면

기대 결과:

- scene id 유지
- active/ready 정보 보존
- enter 쪽 완화 의미 유지
- wait lock 선호 아님

### 13-3. XAU upper sell probe 장면

기대 결과:

- scene id 유지
- confirm release 또는 enter 쪽 완화 의미 유지
- 일반 noise wait 해석으로 떨어지지 않음

### 13-4. BTC conservative lower probe의 ready 전/후

기대 결과:

- ready 전에는 wait lock 쪽 의미가 남을 수 있음
- ready 후에는 wait lock이 완화됨

이 장면이 중요하다.
probe temperament가 단순 scene lookup이 아니라
"scene progression translator"라는 점을 가장 잘 보여주기 때문이다.


## 14. 이번 슬라이스에서 건드리면 안 되는 것

이번 W1-4에서는 아래를 같이 재설계하지 않는 편이 좋다.

- symbol temperament map 값 자체 변경
- probe scene 판정 규칙 자체 변경
- wait decision threshold 구조 변경
- state policy 철학 변경

이번 목적은 scene-specific probe wait owner extraction이지,
probe 시스템 자체를 다시 설계하는 것이 아니다.


## 15. 완료 선언 조건

W1-4는 아래가 만족되면 완료로 본다.

1. probe temperament owner가 `WaitEngine` 밖으로 이동했다
2. `WaitEngine`은 caller/조합기 역할만 남았다
3. direct helper 테스트가 추가됐다
4. XAU probe 회귀가 그대로 녹색이다
5. metadata shape가 downstream에서 깨지지 않는다


## 16. W1 완료 후 의미

W1-4까지 끝나면
`WaitEngine` 안에 남아 있던 큰 bias/scene owner 네 덩어리가 모두 밖으로 빠진다.

- state bias
- belief bias
- edge-pair bias
- probe temperament

그 시점부터 `WaitEngine`은
"wait 입력 정리 -> helper 호출 -> state policy 호출 -> decision policy 호출 -> trace 기록"
중심의 조합기로 훨씬 선명해진다.

즉 W1-4는 W1의 마감 슬라이스다.
