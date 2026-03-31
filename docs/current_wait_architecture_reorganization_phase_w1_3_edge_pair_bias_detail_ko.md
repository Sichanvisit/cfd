# 기다림 재정리 W1-3 Edge Pair Wait Bias 상세 문서

부제: 방향성 우위와 미해결 쌍을 기다림 정책으로 번역하는 owner 분리 가이드

작성일: 2026-03-27 (KST)

## 1. 문서 목적

이 문서는 `W1-3 edge pair wait bias extraction`을 구현하기 전에,
현재 `WaitEngine` 안에 들어 있는 edge-pair 해석 로직이 실제로 무슨 의미를 맡고 있는지 고정하기 위한 상세 문서다.

이번 슬라이스는 단순히 숫자 몇 개를 helper로 옮기는 작업이 아니다.
이 owner는 현재 wait 레이어 안에서 아래 질문에 답하고 있다.

- 지금 방향성 우위가 실제로 분명한가
- 그 우위가 내가 진입하려는 방향과 같은가
- 그렇다면 기다림을 조금 풀어도 되는가
- 반대로 아직 쌍이 안 풀렸다면 기다림을 유지해야 하는가

즉 이 helper는 "edge 구조를 wait 성향으로 번역하는 통역기"에 가깝다.


## 2. 현재 owner가 있는 위치

- 현재 owner: `backend/services/wait_engine.py`
- 현재 함수: `_entry_edge_pair_wait_bias(...)`

이 함수는 `WaitEngine` 내부에 있지만,
역할상으로는 wait 조합기 본문보다 정책 helper에 더 가깝다.


## 3. 이 owner가 현재 하는 일

현재 로직은 대략 네 단계로 움직인다.

### 3-1. 방향성 쌍 정보를 읽는다

먼저 관찰/확인 단계에서 만들어진 edge-pair 결과를 읽는다.
여기서 읽는 핵심 의미는 아래와 같다.

- 지금이 어느 구간인지
  - 아래쪽 가장자리인지
  - 위쪽 가장자리인지
  - 중간 구간인지
- 현재 어느 방향이 우세한지
  - 매수 우세인지
  - 매도 우세인지
  - 아직 균형인지
- 그 우세가 충분히 분명한지
- 두 방향 간 간격이 얼마나 벌어져 있는지

이 단계의 역할은 "지금 구조가 방향성을 말할 준비가 되었는가"를 읽는 것이다.

### 3-2. 실제 진입 의도 방향을 정한다

그 다음에는 "나는 지금 어느 방향으로 들어가려는가"를 정한다.

우선순위는 현재 action, preflight/core에서 요구한 방향, 마지막 fallback 방향 순으로 흘러간다.
이 부분이 중요한 이유는 edge-pair가 아무리 선명해도,
그 선명함이 내가 실제로 들어가려는 방향과 맞지 않으면 confirm release로 쓰면 안 되기 때문이다.

즉 이 helper는 구조 그 자체만 보는 것이 아니라,
"구조의 우세"와 "실제 진입 방향"의 합치 여부를 함께 본다.

### 3-3. 좋은 directional release인지 판단한다

다음 경우는 기다림을 약간 풀어주는 쪽으로 번역된다.

- 의미 있는 가장자리/중간 문맥 안에 있고
- 승자가 분명하고
- 그 승자가 매수나 매도처럼 실제 방향을 가지고 있고
- 그 방향이 내가 들어가려는 방향과 맞는 경우

이 경우의 의미는 단순하다.

> 기다리던 이유 중 하나가 "방향이 아직 안 풀렸기 때문"이었는데,
> 이제 방향이 비교적 분명하게 풀렸고,
> 그 방향도 현재 진입 의도와 맞으니,
> wait를 조금 더 완화할 수 있다.

그래서 현재 로직은 이런 경우
wait threshold를 약간 완화하고,
enter 쪽 가치를 올리고,
wait 쪽 가치를 내린다.

### 3-4. 아직 쌍이 미해결인지 판단한다

반대로 아래 경우는 기다림을 유지하거나 강화하는 쪽으로 번역된다.

- 문맥상 edge/middle처럼 구조 판단이 의미 있는 구간인데
- 승자가 아직 분명하지 않거나
- 승자가 방향성을 갖지 못했거나
- 간격이 너무 작아서 사실상 아직 균형에 가까운 경우

이 경우의 의미도 단순하다.

> 아직 쌍이 안 풀렸는데 성급하게 기다림을 풀면,
> "애매한 directional signal"을 "실행 가능한 방향 확신"으로 오독할 수 있다.

그래서 현재 로직은 이런 경우
wait soft/hard 성향을 강화하고,
enter 쪽 가치를 낮추고,
wait 쪽 가치를 올린다.


## 4. 이 owner의 구조적 의미

이 helper는 wait 레이어 안에서
"directional confidence translator" 역할을 맡고 있다.

state bias가 시장 상태의 질감을 읽고,
belief bias가 thesis 강도를 읽는다면,
edge-pair bias는 방향성 우위가 실제로 풀렸는지를 읽는다.

즉 성격이 다르다.

- state bias: 환경이 거칠거나 부드러운가
- belief bias: 신념이 아직 약한가, 이미 분명한가
- edge-pair bias: 방향성 경쟁이 실제로 해소됐는가

그래서 이 owner를 밖으로 빼면 wait 레이어의 의미 분리가 훨씬 선명해진다.


## 5. 왜 지금 분리해야 하나

### 5-1. directional wait는 별도 owner가 있어야 한다

기다림은 단순히 "점수가 낮으면 기다림"이 아니다.
특히 edge 구간에서는
"아직 방향 쌍이 안 풀려서 기다리는 것"과
"방향이 풀렸는데도 다른 이유로 기다리는 것"을 구분해야 한다.

이 구분을 계속 `WaitEngine` 안의 내부 함수로만 두면,
나중에 pair gap 기준이나 clear winner 기준을 조정할 때
wait 본문과 directional 문맥이 뒤섞이기 쉽다.

### 5-2. 차트 해석과도 간접적으로 이어진다

directional wait는 나중에 차트에서
`BUY_WAIT`, `SELL_WAIT`, 일반 `WAIT`를 읽는 감각과도 닿아 있다.

지금 helper가 직접 차트 이벤트를 만들지는 않지만,
"방향이 풀렸는지 안 풀렸는지"를 해석하는 기준을 가진 owner이므로
이 의미가 엔진 내부에서 독립돼 있는 편이 전체 구조상 더 건강하다.

### 5-3. entry parity를 맞추기 위해 필요하다

entry 쪽은 이미 scene-specific policy owner를 많이 밖으로 뺐다.
wait 쪽도 같은 수준으로 가려면,
directional release/lock을 만드는 logic을 독립 owner로 분리해야 한다.


## 6. 구현 시 유지해야 할 핵심 철학

이번 extraction에서 가장 중요한 것은
"출력 shape를 새로 디자인하는 것"이 아니라
"현재 의미를 그대로 보존한 채 owner만 이동하는 것"이다.

특히 아래 원칙을 지켜야 한다.

- clear directional winner는 wait 완화 쪽 의미를 유지한다
- unresolved pair는 wait lock 쪽 의미를 유지한다
- acting side가 없는 경우의 fallback 방식은 유지한다
- pair gap의 최소 기준은 의미가 바뀌지 않게 유지한다
- metadata에 남는 해석 결과 shape는 최대한 그대로 보존한다

이번 슬라이스의 목적은 behavior redesign이 아니다.
owner extraction과 해석 경계 고정이 목적이다.


## 7. 권장 새 owner 형태

### 권장 파일

- `backend/services/entry_wait_edge_pair_bias_policy.py`

### 권장 public 함수

- `resolve_entry_wait_edge_pair_bias_v1(...) -> dict`

### 권장 보조 함수

- `resolve_entry_wait_acting_side_v1(...)`

가능하면 `W1-2 belief wait bias`에서 이미 분리한 acting-side resolver를 재사용하는 편이 좋다.
이유는 edge-pair도 결국 "현재 실제 진입 방향"을 알아야 해석이 가능하기 때문이다.

즉 새로운 helper가 directionality를 계산하되,
acting side의 정의는 중복 소유하지 않는 편이 더 안전하다.


## 8. 권장 입력 형태

새 helper는 아래 성격의 입력을 받는 것이 좋다.

- 원본 payload
- 현재 action
- core/preflight에서 허용한 방향 정보

payload를 직접 받는 이유는,
edge-pair 정보가 row 상단에 있을 수도 있고
observe-confirm metadata 안에 숨어 있을 수도 있기 때문이다.

다만 helper 내부에서 하는 일은 단순해야 한다.

1. edge-pair 구조를 읽는다
2. acting side를 정한다
3. clear release인지 unresolved lock인지 판정한다
4. wait/enter delta와 multiplier를 계산한다


## 9. 권장 출력 형태

현재 metadata 호환성을 위해 출력은 가능한 한 아래 의미를 유지하는 편이 좋다.

- edge-pair 정보가 실제로 있었는지
- 현재 문맥이 의미 있는 edge/middle인지
- 누가 승자인지
- 승자가 충분히 분명한지
- gap이 얼마나 되는지
- 실제 진입 의도 방향이 무엇인지
- confirm release를 선호하는지
- wait lock을 선호하는지
- wait soft/hard 강도를 얼마나 조정하는지
- enter/wait 가치 차이를 얼마나 조정하는지

여기서 핵심은
"진단 가능한 결과를 남기는 것"이다.
나중에 row를 읽을 때
"왜 이 wait가 풀렸는지" 혹은 "왜 계속 잠겼는지"를 설명할 수 있어야 한다.


## 10. 기존 회귀와 직접 연결되는 포인트

이번 슬라이스는 아래 기존 회귀와 직접 연결된다.

- `tests/unit/test_wait_engine.py`
  - clear winner가 있을 때 wait가 완화되는지 검증하는 케이스
  - unresolved pair일 때 hard wait가 유지되는지 검증하는 케이스

이 테스트들이 의미하는 바는 명확하다.

- 분명한 승자가 현재 진입 방향과 맞으면 confirm release
- 승자가 없거나 gap이 너무 작으면 wait lock

새 helper를 뺀 뒤에도 이 계약은 그대로 살아 있어야 한다.


## 11. 구현 순서 권장안

이번 슬라이스는 아래 순서로 가는 것이 안전하다.

1. 새 policy 파일 생성
2. acting-side resolver 재사용 여부 정리
3. 기존 `_entry_edge_pair_wait_bias(...)` 본문을 helper로 이동
4. `WaitEngine` caller를 새 helper 호출로 치환
5. direct helper unit test 추가
6. 기존 `test_wait_engine.py` 회귀 재실행
7. `entry_try_open_entry` 관련 wait 회귀 재실행

이 순서를 지키면
"의미를 바꿔서 녹색이 된 것인지"
"owner만 옮겼는데 그대로 녹색인 것인지"
를 구분하기 쉽다.


## 12. direct helper 테스트에서 반드시 잡아야 할 장면

새 helper 전용 테스트는 최소한 아래 장면을 포함하는 것이 좋다.

### 12-1. 분명한 매수 승자 + 매수 진입 의도

- 아래쪽 가장자리 문맥
- 승자 분명
- gap 충분
- 현재 진입 의도와 방향 일치

기대 결과:

- confirm release 선호
- wait lock 아님
- enter 가치 증가
- wait 가치 감소

### 12-2. 승자 미확정 + gap 작음

- 가장자리 문맥
- 승자 불분명 또는 균형
- gap 작음

기대 결과:

- wait lock 선호
- confirm release 아님
- enter 가치 감소
- wait 가치 증가

### 12-3. 방향은 분명하지만 진입 의도와 반대

- 승자는 분명하지만
- 현재 진입 의도 방향과 맞지 않음

기대 결과:

- confirm release로 취급하지 않음

### 12-4. edge-pair 정보 자체가 없음

기대 결과:

- neutral 기본값
- present false


## 13. 이번 슬라이스에서 건드리면 안 되는 것

이번 W1-3에서는 아래를 같이 건드리지 않는 편이 좋다.

- pair-gap 기준 자체 재설계
- chart event 의미 변경
- wait decision threshold 구조 변경
- belief/state bias 철학 수정

이 슬라이스의 목적은
directional edge-pair bias owner를 밖으로 빼는 것이지,
wait 시스템 전체 의미를 다시 설계하는 것이 아니다.


## 14. 완료 선언 조건

W1-3은 아래가 만족되면 완료로 본다.

1. edge-pair bias 계산 owner가 `WaitEngine` 밖으로 이동했다
2. `WaitEngine`은 caller/조합기 역할만 남았다
3. direct helper 테스트가 추가됐다
4. clear winner / unresolved pair 회귀가 그대로 녹색이다
5. metadata shape가 downstream에서 깨지지 않는다


## 15. 다음 연결 지점

W1-3이 끝나면 남는 큰 bias owner는 두 개다.

- probe temperament
- wait context 전체를 더 얇게 만드는 후속 정리

즉 다음 자연스러운 단계는 `W1-4 probe temperament extraction`이다.
W1-3까지 끝나면 directional wait 해석 owner가 밖으로 빠지므로,
그 다음부터는 scene-specific temperament 정리가 훨씬 선명해진다.
