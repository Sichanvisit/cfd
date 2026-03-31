# 기다림 레이어 재정렬 Phase W1 구현 분해 문서

부제: Wait Bias Owner Extraction 실제 구현 가이드

작성일: 2026-03-27 (KST)

## 업데이트 상태 (2026-03-27)

현재 `W1-1 ~ W1-4`까지 구현과 핵심 회귀 검증이 완료된 상태다.

- `entry_wait_state_bias_policy.py` 추가
- `entry_wait_belief_bias_policy.py` 추가
- `entry_wait_edge_pair_bias_policy.py` 추가
- `entry_wait_probe_temperament_policy.py` 추가
- `WaitEngine` caller 치환 완료
- direct helper tests 추가
- `test_wait_engine.py` 통과
- `test_entry_try_open_entry_policy.py` 통과
- `test_entry_try_open_entry_probe.py` 통과

즉 W1의 네 bias/scene owner extraction은 현재 시점 기준으로 마감된 상태다.

## 진행 상태 (2026-03-27)

현재 `W1-1 state wait bias extraction`과
`W1-2 belief wait bias extraction`은 구현과 테스트 검증까지 완료된 상태다.

- `entry_wait_state_bias_policy.py` 추가
- `entry_wait_belief_bias_policy.py` 추가
- `WaitEngine` state bias caller 치환 완료
- `WaitEngine` belief bias caller 치환 완료
- direct helper test 추가
- 기존 `test_wait_engine.py`
- `test_entry_try_open_entry_policy.py`
- `test_entry_try_open_entry_probe.py`
  회귀 통과

즉 다음으로 이어갈 자연스러운 슬라이스는 `W1-3 edge pair wait bias extraction`이다.

## 1. 문서 목적

이 문서는 기다림 로드맵의 첫 구현 묶음인 `W1. Bias Owner Extraction`을
실제로 손댈 수 있는 작업 단위로 쪼개기 위한 문서다.

현재는 이미 아래 두 owner가 밖으로 빠진 상태다.

- `entry wait state policy`
  - `backend/services/entry_wait_state_policy.py`
- `entry wait decision policy`
  - `backend/services/entry_wait_decision_policy.py`

즉 이번 W1의 목적은
`기다림의 결론을 정하는 본문`이 아니라
`그 결론에 들어가는 bias 재료 계산기`를 정리하는 것이다.


## 2. W1이 필요한 이유

현재 `WaitEngine`은 예전보다 훨씬 얇아졌지만,
아직 아래 네 덩어리는 엔진 내부에 남아 있다.

- edge pair 기반 wait bias
  - `backend/services/wait_engine.py:409`
- belief 기반 wait bias
  - `backend/services/wait_engine.py:508`
- state 기반 wait bias
  - `backend/services/wait_engine.py:635`
- probe temperament 기반 wait bias
  - `backend/services/wait_engine.py:723`

그리고 이 네 덩어리는 결국

- wait threshold를 얼마나 느슨/엄격하게 볼지
- confirm release를 줄지
- wait lock을 줄지
- enter/wait utility delta를 얼마나 줄지

를 만든다.

즉 지금 `WaitEngine` 안에는 아직도
`왜 기다림이 강해졌는가`를 설명하는 계산 owner가 남아 있는 상태다.


## 3. W1의 목표 상태

W1이 끝났다고 말하려면 아래 상태가 되어야 한다.

1. 네 bias 계산기가 `WaitEngine` 밖 shared helper owner로 분리된다.
2. `WaitEngine`은 payload를 읽고 helper를 호출해 결과를 조합만 한다.
3. 각 bias owner에 direct unit test가 생긴다.
4. 기존 `test_wait_engine.py` 회귀가 그대로 녹색이다.
5. metadata에 남는 bias 결과 shape가 흔들리지 않는다.


## 4. 현재 실제 진입 함수

W1에서 직접 영향을 받는 핵심 함수는 세 군데다.

### 4-1. bias 계산 함수들

- `backend/services/wait_engine.py:409`
  - `_entry_edge_pair_wait_bias(...)`
- `backend/services/wait_engine.py:508`
  - `_entry_belief_wait_bias(...)`
- `backend/services/wait_engine.py:635`
  - `_entry_state_wait_bias(...)`
- `backend/services/wait_engine.py:723`
  - `_entry_symbol_probe_temperament(...)`

### 4-2. state builder

- `backend/services/wait_engine.py:874`
  - `build_entry_wait_state_from_row(...)`

이 함수는 bias 계산기들을 호출하고,
threshold를 조정한 뒤,
최종 wait state policy helper로 넘긴다.

### 4-3. decision chooser

- `backend/services/wait_engine.py:1256`
  - `evaluate_entry_wait_decision(...)`

이 함수는 state metadata 안에 들어 있는 bias 결과를 읽고
wait/enter utility를 비교한다.


## 5. W1 전체 전략

W1은 한 번에 하지 말고 아래 순서로 가는 것이 가장 안전하다.

1. `W1-1` state wait bias extraction
2. `W1-2` belief wait bias extraction
3. `W1-3` edge pair wait bias extraction
4. `W1-4` probe temperament extraction

이 순서가 좋은 이유는 다음과 같다.

- state bias는 다른 helper보다 의존성이 적다.
- belief bias는 영향력이 크지만 입력이 비교적 명확하다.
- edge pair는 directional side resolution과 맞물리므로 그 다음이 좋다.
- probe temperament는 scene-specific 색이 강해서 마지막에 빼는 편이 안전하다.


## 6. W1-1. State Wait Bias Extraction

### 현재 owner

- `backend/services/wait_engine.py:635`

### 이 블록이 하는 일

- state vector에서 confirm/wait gain을 읽는다
- quality/patience/execution friction/event risk/session regime를 읽는다
- wait soft / hard multiplier를 만든다
- confirm release / wait lock 성향을 만든다

### 권장 새 파일

- `backend/services/entry_wait_state_bias_policy.py`

### 권장 public 함수

- `resolve_entry_wait_state_bias_v1(...) -> dict`

### 입력 후보

- `state_vector_v2`
- `state_vector_metadata`

### 출력 후보

- `wait_soft_mult`
- `wait_hard_mult`
- `prefer_confirm_release`
- `prefer_wait_lock`
- `topdown_state_label`
- `quality_state_label`
- `patience_state_label`
- `execution_friction_state`
- `event_risk_state`

### 완료 기준

- `WaitEngine`은 더 이상 state bias를 직접 계산하지 않는다.
- helper direct test가 생긴다.
- 기존 wait state/decision 테스트가 그대로 통과한다.

### 우선 고정할 테스트 포인트

- high quality + confirm favor -> confirm release
- high friction / high event risk -> wait lock
- wait gain 상승 -> wait multiplier 완화
- confirm gain 상승 -> wait multiplier 강화


## 7. W1-2. Belief Wait Bias Extraction

### 현재 owner

- `backend/services/wait_engine.py:508`

### 이 블록이 하는 일

- belief persistence, streak, spread, dominance deadband를 읽는다
- 현재 진입 방향과 dominant side가 맞는지 본다
- 좋은 wait인지, 풀어줘야 할 wait인지 판정한다
- utility delta와 threshold multiplier를 만든다

### 권장 새 파일

- `backend/services/entry_wait_belief_bias_policy.py`

### 권장 public 함수

- `resolve_entry_wait_belief_bias_v1(...) -> dict`

### 주의점

belief bias는 단순 multiplier가 아니라
`wait 유지`, `confirm release`, `enter/wait utility delta`를 동시에 만든다.
그래서 이 helper는 나중에 wait tuning과 가장 자주 맞닿을 가능성이 높다.

### 기존 회귀에서 직접 연결되는 포인트

- `tests/unit/test_wait_engine.py:710`
  - low persistence + spread deadband -> wait lock 유지
- `tests/unit/test_wait_engine.py:757`
  - streak가 있어도 spread deadband면 wait lock 유지
- `tests/unit/test_wait_engine.py:896`
  - belief release가 enter value를 올리고 wait를 풀어줌

### 완료 기준

- belief bias shape가 metadata에서 그대로 유지된다.
- belief 관련 기존 wait tests가 모두 녹색이다.


## 8. W1-3. Edge Pair Wait Bias Extraction

### 현재 owner

- `backend/services/wait_engine.py:409`

### 이 블록이 하는 일

- edge pair law에서 winner side / pair gap / clear winner를 읽는다
- acting side를 정한다
- clear directional dominance면 confirm release를 만든다
- unresolved pair면 wait lock을 만든다

### 권장 새 파일

- `backend/services/entry_wait_edge_pair_bias_policy.py`

### 권장 public 함수

- `resolve_entry_wait_edge_pair_bias_v1(...) -> dict`

### 주의점

이 helper는 directional wait와 관련된 의미가 강하다.
나중에 chart 쪽 `BUY_WAIT / SELL_WAIT / WAIT` 해석과도 간접 연결되므로
출력 shape를 괜히 너무 화려하게 만들기보다
현재 metadata와 호환되게 유지하는 것이 좋다.

### 완료 기준

- acting side resolution과 pair gap logic이 helper로 이동한다.
- `WaitEngine`에는 caller 조합만 남는다.


## 9. W1-4. Probe Temperament Extraction

### 현재 owner

- `backend/services/wait_engine.py:723`

### 이 블록이 하는 일

- probe plan / probe candidate / scene temperament를 읽는다
- wait용 probe temperament map을 불러온다
- scene별 enter/wait delta와 confirm release / wait lock을 만든다

### 권장 새 파일

- `backend/services/entry_wait_probe_temperament_policy.py`

### 권장 public 함수

- `resolve_entry_wait_probe_temperament_v1(...) -> dict`

### 기존 회귀에서 직접 연결되는 포인트

- `tests/unit/test_wait_engine.py:92`
  - xau second support probe는 center/noise로 묻히지 않아야 함
- `tests/unit/test_wait_engine.py:128`
  - second support probe는 실제 wait selected로 가지 않아야 함
- `tests/unit/test_wait_engine.py:162`
  - xau upper sell probe도 active 유지
- `tests/unit/test_wait_engine.py:198`
  - upper sell probe는 바로 wait selected가 되지 않아야 함

### 완료 기준

- scene-specific wait temperament owner가 `WaitEngine` 밖으로 이동한다.
- XAU probe류 기존 회귀가 그대로 통과한다.


## 10. 파일별 최종 목표 역할

### `backend/services/wait_engine.py`

최종 역할:

- wait 입력 정리
- bias helper 호출
- state policy helper 호출
- decision policy helper 호출
- trace 기록
- exit utility orchestration

하지 않아야 할 역할:

- belief/state/edge pair/probe bias 본문 계산

### `backend/services/entry_wait_state_policy.py`

최종 역할:

- bias 결과와 wait 입력을 바탕으로 wait state/hard wait를 결정

### `backend/services/entry_wait_decision_policy.py`

최종 역할:

- wait state metadata와 utility context를 바탕으로 실제 wait 선택 여부를 결정

### 새 bias helper 파일들

최종 역할:

- 각 owner가 wait에 미치는 영향만 계산


## 11. 권장 구현 순서

### Step 1. W1-1 state bias helper 추가

- 새 파일 생성
- direct test 추가
- `WaitEngine` caller 치환
- 기존 wait 회귀 확인

### Step 2. W1-2 belief bias helper 추가

- 새 파일 생성
- low persistence / deadband / confirm release 케이스 direct test 추가
- 기존 belief 관련 wait 회귀 확인

### Step 3. W1-3 edge pair helper 추가

- 새 파일 생성
- directional clear winner / unresolved pair 케이스 direct test 추가
- 기존 wait 회귀 확인

### Step 4. W1-4 probe temperament helper 추가

- 새 파일 생성
- XAU probe류 direct test 추가
- 기존 probe wait 회귀 확인

### Step 5. W1 마감 정리

- `WaitEngine` 안에 남은 bias owner가 없는지 확인
- metadata shape 유지 확인
- 필요 시 handoff/roadmap 문서 반영


## 12. 테스트 전략

W1에서는 두 층 테스트가 필요하다.

### direct helper tests

각 bias owner별 pure helper 테스트를 만든다.

권장 파일:

- `tests/unit/test_entry_wait_state_bias_policy.py`
- `tests/unit/test_entry_wait_belief_bias_policy.py`
- `tests/unit/test_entry_wait_edge_pair_bias_policy.py`
- `tests/unit/test_entry_wait_probe_temperament_policy.py`

### 기존 회귀 유지

반드시 같이 돌릴 테스트:

- `tests/unit/test_wait_engine.py`
- `tests/unit/test_entry_try_open_entry_policy.py`
- `tests/unit/test_entry_try_open_entry_probe.py`

이유:

- wait helper extraction이 orchestration payload를 흔들지 않는지 같이 봐야 한다.


## 13. 이번 W1에서 아직 하지 않을 것

- `entry_wait_context_v1` contract freeze
- wait recent semantic summary 추가
- handoff wait section 대폭 확장
- exit/manage utility 본문 extraction

이것들은 W2 이후 단계의 일이다.
W1에서는 bias owner 분리까지만 하는 게 범위상 맞다.


## 14. W1 완료 선언 조건

아래를 만족하면 W1 완료로 봐도 된다.

1. 네 bias helper가 모두 `WaitEngine` 밖으로 빠져 있다.
2. `WaitEngine`은 bias를 계산하지 않고 조합만 한다.
3. helper direct tests가 생겼다.
4. `test_wait_engine.py`가 녹색이다.
5. `entry_try_open_entry` wait 연동 회귀가 녹색이다.
6. metadata shape가 이전 의미를 유지한다.


## 15. 가장 먼저 시작할 실제 작업

가장 먼저 시작할 것은 `W1-1 state wait bias extraction`이다.

이유는 간단하다.

- 다른 bias보다 의존성이 약하다.
- state label 기반 입력이 비교적 명확하다.
- wait lock / confirm release 의미가 분명하다.
- 이후 belief/edge-pair/probe extraction의 패턴 템플릿이 된다.

즉 W1의 첫 삽은
`state wait bias helper 파일 추가 -> WaitEngine caller 치환 -> direct tests -> 기존 wait 회귀`
이 순서로 가는 것이 가장 좋다.
