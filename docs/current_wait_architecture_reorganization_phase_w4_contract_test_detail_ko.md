# 기다림 정리 Phase W4 상세 문서

부제: wait end-to-end contract tests를 왜, 어디까지, 어떤 형태로 잠가야 하는가

작성일: 2026-03-29 (KST)
현재 상태: 2026-03-29 대표 scene 연속 계약 테스트 1차 반영

## 1. 문서 목적

이 문서는
`Phase W4. Wait End-to-End Contract Test 확장`
을 실제 코드 상태에 맞게 상세히 설명하기 위한 문서다.

W4의 핵심은
새로운 wait rule을 더 만드는 것이 아니다.

오히려 지금까지 W1, W2, W3에서 분리하고 고정하고 관측 가능하게 만든 wait 계약이
실제로 끝까지 같은 의미로 이어지는지를
테스트로 잠그는 단계다.


## 2. 왜 W4가 지금 필요한가

지금 wait 레이어는 이미 많이 정리됐다.

- bias owner가 분리됐다
- wait context contract가 생겼다
- wait state policy input도 따로 얼었다
- recent diagnostics에서 wait semantic summary도 읽힌다

즉 이제는
`구조가 아직 안 나와서 테스트를 못 하는 상태`
가 아니다.

반대로 지금 같은 시점이
테스트를 가장 강하게 넣기 좋은 타이밍이다.

이유는 간단하다.

- owner 경계가 이제야 안정됐다
- runtime surface 이름도 고정됐다
- row에 남는 필드도 고정되기 시작했다

이 상태에서 W4를 안 하면,
다음 tuning이나 새 rule 추가 때
`중간 단계 의미가 조용히 어긋나는 문제`
를 다시 사람이 뒤늦게 CSV로 잡게 된다.


## 3. W4가 잠가야 하는 실제 연속 계약

roadmap에 적힌 한 줄은
`consumer -> wait state -> wait decision -> row/runtime`
지만,
현재 코드 상태에 맞게 풀면 아래 6단으로 보는 편이 정확하다.

### 3-1. consumer에서 내려온 pre-entry row truth

wait는 완전히 독립된 엔진이 아니라,
consumer와 entry 경로가 정리한 row truth를 바탕으로 움직인다.

즉 W4의 시작점은
“차트 이벤트”가 아니라
이미 consumer와 entry가 정리해서 만든 pre-entry row다.

여기에는 보통 아래 의미가 들어 있다.

- blocked/observe 이유
- action none reason
- core / preflight allowed action
- wait score family
- symbol-specific scene 단서

### 3-2. wait context와 bias bundle

이 row truth는 wait context로 묶이고,
그 위에서 state / belief / edge-pair / probe bias가 합쳐진다.

즉 W4는
wait state 본문만 보는 테스트가 아니라,
그 state를 만들 때 쓰인 context와 bias도
같은 장면 안에서 함께 보는 테스트여야 한다.

### 3-3. wait state 결정

이 단계에서는
현재 장면을 어떤 기다림 상태로 읽을지 정한다.

예를 들면

- helper soft block 성격의 wait
- probe candidate 성격의 wait
- center 성격의 중립 wait
- wait 아님에 가까운 none 상태

같은 식으로 갈린다.

W4는 여기서
상태 이름만 맞는지 보는 테스트로 끝나면 안 된다.

### 3-4. wait decision 결정

state가 잡혔다고 해서
항상 실제 wait가 선택되는 것은 아니다.

decision 단계에서는

- 실제 wait를 선택할지
- skip으로 풀릴지
- 어떤 wait decision 이름으로 남을지

가 갈린다.

W4는 바로 이 지점을 강하게 잠가야 한다.

왜냐하면 실제 운영에서 체감되는 것은
대개 state보다 decision이기 때문이다.

### 3-5. row/runtime 표면 저장

wait meaning이 engine 내부에서만 맞고
row/runtime로 내려오면서 바뀌면 의미가 없다.

따라서 W4는
state와 decision이 실제 저장 표면에서도 같은 이름으로 남는지,
compact runtime row에서도 같은 의미가 읽히는지까지 봐야 한다.

### 3-6. recent summary 재집계

W3에서 만든 wait semantic summary는
개별 row의 truth를 최근 window로 재집계한 결과다.

따라서 W4의 마지막 단계는
개별 장면들이 recent diagnostics 집계에 들어갔을 때도
같은 의미로 묶이는지 확인하는 것이다.


## 4. 지금 이미 있는 테스트와 아직 비는 부분

### 4-1. 이미 강한 부분

현재는 아래 테스트가 이미 강하다.

- bias owner 직접 테스트
- wait state policy 직접 테스트
- wait decision policy 직접 테스트
- `WaitEngine` unit tests
- runtime status recent summary 테스트

즉 개별 owner와 개별 집계는 많이 잠겨 있다.

### 4-2. 아직 비는 부분

반면 아래는 아직 얇다.

- 한 장면이 state와 decision을 동시에 맞게 통과하는지
- 그 결과가 row/runtime payload까지 같은 이름으로 남는지
- 그 장면이 recent summary에 들어갔을 때도 같은 의미로 집계되는지
- symbol summary와 slim top-level이 detail과 같은 truth를 가리키는지

즉 지금의 공백은
`helper 단위 정확성`이 아니라
`단계 사이 연속성`이다.


## 5. W4가 잡아야 하는 대표 실패 유형

W4는 단순히 테스트 숫자를 늘리는 단계가 아니다.
아래 종류의 회귀를 잡기 위해 존재한다.

### 5-1. state는 맞는데 decision이 미묘하게 바뀌는 경우

예를 들어
helper soft block 장면이 여전히 같은 wait state로 읽히지만,
decision 단계에서 예전처럼 wait를 선택하지 않게 변할 수 있다.

이 경우 helper/unit test만 보면 놓치기 쉽다.

### 5-2. engine 내부는 맞는데 row 저장 이름이 바뀌는 경우

state/decision이 engine에서는 맞더라도,
`entry_try_open_entry`나 compact row 저장 경로에서
필드명이 누락되거나 다른 값으로 바뀔 수 있다.

이 경우 운영에서는 다시 “왜 wait가 많았는지” 읽기 어려워진다.

### 5-3. detail summary는 맞는데 slim surface가 다르게 보이는 경우

detail runtime diagnostics와 slim runtime status는
둘 다 운영 표면이다.

이 둘이 서로 다른 truth를 보여주면
새 스레드에서 다시 혼란이 생긴다.

### 5-4. symbol summary가 window summary와 어긋나는 경우

window summary 전체 counts는 맞는데,
심볼별 집계가 일부 필드를 놓칠 수 있다.

이 경우 결국 운영자는 다시 CSV를 뒤지게 된다.


## 6. W4를 어떻게 나누는 것이 좋은가

W4는 W1/W2처럼 많은 구조 공사를 하는 단계는 아니다.
하지만 한 번에 크게 넣으면 실패 지점이 흐려진다.

따라서 아래 4단으로 가는 것이 좋다.

### W4-1. Scenario Fixture Freeze

먼저 end-to-end 장면을 몇 개로 고정한다.

권장 시작 장면:

1. helper soft block 장면
2. probe candidate 장면
3. center wait but skip 장면
4. none/clean ready control 장면

핵심은
“scene 이름을 많이 늘리는 것”이 아니라
`서로 다른 wait 의미를 대표하는 기준 장면`
을 고정하는 것이다.

### W4-2. Orchestration Continuity Test

이 단계에서는
한 장면이 state와 decision을 거쳐
row/runtime payload까지 같은 의미로 저장되는지 잠근다.

즉 `WaitEngine` 테스트를 넘어
orchestration 경계까지 같이 본다.

### W4-3. Runtime Aggregation Continuity Test

이 단계에서는
같은 장면 세트를 recent diagnostics에 넣었을 때
window summary, symbol summary, slim top-level summary가
같은 truth를 가리키는지 본다.

W3에서 만든 summary들이 진짜로 end-to-end contract가 되는지
여기서 닫힌다.

### W4-4. Regression Matrix Close-Out

마지막으로
새 wait rule이 붙어도 깨지지 않게
대표 scene matrix를 남기고,
어느 테스트 파일이 어떤 의미를 잠그는지 분명히 한다.


## 7. 권장 테스트 구조

### 7-1. helper/unit tests는 그대로 둔다

기존

- bias owner 테스트
- state policy 테스트
- decision policy 테스트
- `WaitEngine` unit tests

는 그대로 유지한다.

W4는 이것들을 대체하는 단계가 아니라,
그 위에 연속 계약 테스트를 얹는 단계다.

### 7-2. 새 end-to-end 전용 테스트 파일을 두는 편이 좋다

권장 파일:

- `tests/unit/test_entry_wait_end_to_end_contract.py`

이 파일의 역할은
새 owner를 개별 검증하는 것이 아니라,
한 장면이 끝까지 같은 의미를 유지하는지를 잠그는 것이다.

### 7-3. runtime status 테스트는 집계 관점만 강화한다

`tests/unit/test_trading_application_runtime_status.py`는
이미 summary를 잘 보고 있으므로,
W4에서는 장면별 bridge parity와 symbol/slim parity를 더 명확히 고정하는 식이 좋다.


## 8. 이번 단계에서 건드리지 말아야 할 것

W4는 test-contract 단계다.
따라서 아래는 이번에 같이 섞지 않는 편이 좋다.

- wait rule 자체 수정
- chart 의미 재설계
- exit/manage 로직 구현
- alerting 대시보드 구현

이 네 가지를 W4와 같이 섞으면
테스트가 구조 회귀를 잡는 것인지,
새 rule 동작을 설명하는 것인지 경계가 흐려진다.


## 9. W4 완료 기준

W4는 아래 상태가 되면 완료로 본다.

- 대표 wait 장면 fixture가 고정돼 있다
- orchestration 연속 테스트가 생겨 있다
- runtime aggregation 연속 테스트가 생겨 있다
- symbol/detail/slim parity가 테스트로 잠겨 있다
- 새 wait rule 추가 시 어느 테스트를 먼저 봐야 하는지 분명하다


## 10. W4가 끝나면 무엇이 좋아지나

W4가 끝나면
wait는 이제 “구조는 좋아졌지만 단계 사이가 약한 레이어”가 아니라,
`중간 의미와 운영 표면이 테스트로 연결된 레이어`
가 된다.

그러면 이후에는

- wait tuning
- semantic refinement
- scene 추가
- exit/manage 연결

을 할 때도
어디서 truth drift가 생겼는지를 훨씬 빨리 잡을 수 있다.
