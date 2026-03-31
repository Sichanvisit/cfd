# 기다림 레이어 W1-2 Belief Wait Bias 상세 문서

부제: 좋은 기다림 / 나쁜 기다림 판정 owner 분리 가이드

작성일: 2026-03-27 (KST)

## 진행 상태 (2026-03-27)

현재 이 슬라이스는 구현과 테스트 검증까지 완료된 상태다.

- `entry_wait_belief_bias_policy.py` 추가
- `WaitEngine` belief bias caller 치환 완료
- direct helper tests 추가
- 기존 `test_wait_engine.py`
- `test_entry_try_open_entry_policy.py`
- `test_entry_try_open_entry_probe.py`
  회귀 통과

## 1. 문서 목적

이 문서는 `W1-2 belief wait bias extraction`을 구현하기 전에,
이 owner가 실제로 무엇을 읽고 어떤 의미를 만드는지 고정하기 위한 상세 문서다.

이 슬라이스는 단순 multiplier extraction이 아니다.
현재 belief wait bias는 아래를 동시에 만든다.

- 지금 기다림을 유지해야 하는지
- 기다림을 풀어줘야 하는지
- enter 쪽 utility를 얼마나 올릴지
- wait 쪽 utility를 얼마나 올릴지
- state hard-wait 판정을 얼마나 강화/완화할지

즉 이 helper는
`belief가 좋은 기다림 / 나쁜 기다림을 어떻게 구분하는가`
를 실제 코드에 반영하는 owner에 가깝다.


## 2. 현재 실제 owner

현재 owner는 아래 함수다.

- `backend/services/wait_engine.py:508`
  - `_entry_belief_wait_bias(...)`

이 함수는 `WaitEngine` 내부에 있지만,
역할상으로는 엔진 core보다 독립 policy helper에 더 가깝다.


## 3. 이 owner가 현재 하는 일

### 3-1. belief 입력 읽기

현재 아래 belief 입력을 읽는다.

- dominant side
- dominant mode
- buy / sell persistence
- buy / sell streak
- belief spread
- dominance deadband

그리고 현재 진입하려는 방향과 연결되는 `acting side`를 따로 정한다.

### 3-2. active side 추론

현재 active side는 아래 우선순위로 정해진다.

1. 현재 action이 `BUY` 또는 `SELL`이면 그 방향
2. 아니면 preflight/core allowed action에서 required side 추론
3. 그것도 없으면 dominant side 사용

즉 belief bias는
“belief 자체만 보는 helper”라기보다
“현재 들어가려는 방향을 기준으로 belief가 그 방향을 얼마나 뒷받침하는지”
를 보는 helper다.

### 3-3. 좋은 기다림 / 나쁜 기다림 판정

현재 로직은 크게 두 갈래다.

#### 기다림을 풀어줘야 하는 경우

아래가 동시에 성립하면 `confirm release` 쪽으로 간다.

- dominant side가 현재 acting side와 맞는다
- persistence가 충분히 높다
- streak도 어느 정도 이어졌다
- spread가 deadband를 벗어나서 방향성이 충분히 선명하다

즉
`belief 방향성이 분명하고, 그 방향이 실제 entry 의도와 맞으면
계속 기다리게 하기보다 confirm 쪽으로 풀어준다`
는 의미다.

#### 기다림을 유지해야 하는 경우

아래 중 하나라도 강하면 `wait lock` 쪽으로 간다.

- spread가 아직 deadband 안에 있다
- dominant side가 entry 의도와 맞지 않는다
- persistence가 아직 낮다

즉
`belief가 아직 애매하거나, 반대 thesis가 강하거나, 아직 충분히 누적되지 않았으면
wait 유지가 맞다`
는 의미다.


## 4. 이 owner의 실제 철학

이 helper는 사실상 아래 한 문장으로 요약된다.

> belief가 아직 thesis를 충분히 말하지 못하면 기다림을 유지하고,
> belief가 방향을 충분히 말하기 시작하면 기다림을 완화한다.

그래서 이 helper는
“belief는 entry 방향을 밀어주는가”
뿐 아니라
“지금 wait가 아직 좋은 wait인가”
를 판정하는 역할도 가진다.

이 점이 중요하다.
즉 이 helper를 분리할 때는
단순한 score 조정기가 아니라
`wait quality interpreter`로 다루는 편이 맞다.


## 5. 현재 출력 shape

현재 결과에는 아래가 들어 있다.

- acting side
- dominant side
- dominant mode
- active persistence
- active streak
- spread abs
- dominance deadband
- spread clear
- spread deadband
- persistence low
- persistence high
- prefer confirm release
- prefer wait lock
- wait soft multiplier
- wait hard multiplier
- enter value delta
- wait value delta

즉 출력은 이미 충분히 rich하다.

이 단계에서 새 helper를 만들 때 중요한 원칙은
`shape를 더 화려하게 키우는 것보다 현재 shape를 그대로 유지하는 것`
이다.


## 6. 왜 이 owner를 따로 빼야 하나

### 6-1. wait tuning의 핵심 owner이기 때문

이 helper는 단순 state label helper가 아니다.
나중에 아래 질문과 바로 연결된다.

- 너무 자주 wait 되는가
- belief가 분명해졌는데도 wait가 과하게 유지되는가
- spread deadband가 너무 넓은가
- persistence 기준이 너무 빡센가

즉 tuning이 많아질수록
이 helper를 `WaitEngine` 내부 if 문으로 남겨두는 비용이 커진다.

### 6-2. “좋은 기다림 / 나쁜 기다림” 문맥과 직접 연결되기 때문

기존 문서들에서도 belief는
좋은 기다림과 나쁜 기다림을 가르는 쪽으로 확장해야 한다는 방향이 있었다.

현재 코드도 이미 그 방향을 일부 구현하고 있다.
다만 owner가 엔진 내부에 묻혀 있어서,
그 의미가 잘 드러나지 않는 상태다.

### 6-3. entry parity를 위해 필요하기 때문

entry 쪽은 이미
policy owner를 많이 바깥으로 뺐다.

wait도 parity를 맞추려면
belief가 wait에 주는 영향은 별도 owner로 빠져야 한다.


## 7. 권장 새 owner 형태

### 권장 파일

- `backend/services/entry_wait_belief_bias_policy.py`

### 권장 public 함수

- `resolve_entry_wait_belief_bias_v1(...) -> dict`

### 권장 보조 함수

- `resolve_entry_wait_acting_side_v1(...) -> str`

이 보조 함수는 선택사항이지만,
현재 `_resolve_belief_entry_side(...)`가
belief helper와 edge-pair helper 둘 다에 실질적으로 연결되므로,
재사용 utility로 빼두면 이후 `W1-3 edge pair` 때도 도움이 된다.


## 8. 권장 입력 shape

### 직접 belief 입력

- belief state payload
- belief metadata

### 문맥 입력

- action
- core allowed action
- preflight allowed action

### 주의점

이 helper는 belief만 보고 결론을 내리지 않는다.
반드시 “현재 entry 문맥”이 같이 들어가야 한다.

즉 이 helper의 입력은
`belief_state_v1` 하나로 끝나면 안 되고,
`entry context + belief state` 조합이어야 한다.


## 9. 권장 출력 shape

현재 metadata 호환성을 위해
아래 필드는 그대로 유지하는 편이 좋다.

- `present`
- `acting_side`
- `dominant_side`
- `dominant_mode`
- `buy_persistence`
- `sell_persistence`
- `active_persistence`
- `buy_streak`
- `sell_streak`
- `active_streak`
- `belief_spread`
- `spread_abs`
- `dominance_deadband`
- `spread_clear`
- `spread_deadband`
- `persistence_low`
- `persistence_high`
- `prefer_confirm_release`
- `prefer_wait_lock`
- `wait_soft_mult`
- `wait_hard_mult`
- `enter_value_delta`
- `wait_value_delta`


## 10. 구현 시 주의점

### 10-1. shape를 바꾸지 말 것

이 helper는 이미 downstream에서 metadata로 읽힌다.
특히 decision policy는
`prefer_confirm_release`, `prefer_wait_lock`,
`enter_value_delta`, `wait_value_delta`
를 직접 읽는다.

따라서 이번 슬라이스에서는
shape를 바꾸지 않고 owner만 이동하는 것이 맞다.

### 10-2. acting side 해석을 belief 내부에서만 굳히지 말 것

acting side는 belief helper만의 개념이 아니라
edge pair helper에서도 필요하다.

그래서 아래 둘 중 하나를 고르는 게 좋다.

1. belief helper 내부 로컬 함수로 두고, 다음 edge pair extraction 때 같이 정리한다.
2. 지금 바로 shared utility로 빼둔다.

내 추천은 `2`다.
왜냐하면 다음 `W1-3`가 바로 edge pair라서,
지금 utility로 빼두면 중복 제거가 잘 된다.

### 10-3. tuning은 지금 넣지 말 것

이번 슬라이스는 extraction이다.
deadband, persistence threshold, delta 숫자를 건드리는 건
owner가 분리된 다음에 하는 편이 안전하다.


## 11. 기존 회귀와 직접 연결되는 포인트

### Case A. low persistence + deadband

- `tests/unit/test_wait_engine.py:710`

의미:

- persistence 낮음
- spread deadband 안
- wait lock 유지

### Case B. streak가 있어도 spread deadband

- `tests/unit/test_wait_engine.py:757`

의미:

- streak만 있다고 충분하지 않음
- spread가 deadband 안이면 여전히 wait 유지

### Case C. belief release가 실제 wait를 줄여야 함

- `tests/unit/test_wait_engine.py:896`

의미:

- dominant side가 entry 의도와 맞고
- persistence가 높고
- spread가 clear하면
- enter value가 올라가고 wait value가 내려가야 함

이 세 케이스는 이번 extraction의 핵심 계약이다.


## 12. direct helper 테스트 권장안

권장 파일:

- `tests/unit/test_entry_wait_belief_bias_policy.py`

권장 테스트:

1. no belief state -> neutral defaults
2. low persistence + spread deadband -> prefer wait lock
3. high persistence + dominant match + spread clear -> prefer confirm release
4. dominant mismatch -> wait lock 유지
5. acting side fallback이 preflight/core/dominant 순으로 잘 해석되는지


## 13. 완료 기준

이번 `W1-2`가 끝났다고 보려면 아래를 만족해야 한다.

1. `WaitEngine`은 belief wait bias를 직접 계산하지 않는다.
2. 새 helper가 metadata shape를 그대로 반환한다.
3. direct helper test가 생긴다.
4. 기존 `test_wait_engine.py` belief 관련 회귀가 녹색이다.
5. `test_entry_try_open_entry_policy.py`
   `test_entry_try_open_entry_probe.py`
   가 그대로 녹색이다.


## 14. 추천 구현 순서

1. `entry_wait_belief_bias_policy.py` 추가
2. acting side resolver를 local 또는 shared utility로 정리
3. `WaitEngine` caller 치환
4. direct helper tests 추가
5. 기존 wait / orchestration 회귀 실행


## 15. 한 줄 정리

`W1-2 belief wait bias`는
belief가 지금 thesis를 충분히 말하고 있는지,
그래서 기다림을 유지해야 하는지 풀어야 하는지를 정하는 owner다.

이 owner를 밖으로 빼면
기다림 레이어에서 `좋은 기다림 / 나쁜 기다림`을
코드와 문서 양쪽에서 훨씬 선명하게 설명할 수 있게 된다.
