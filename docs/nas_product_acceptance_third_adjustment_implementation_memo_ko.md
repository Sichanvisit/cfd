# NAS Product Acceptance Third Adjustment Implementation Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이 메모는 NAS product acceptance 3차 조정의 핵심을 기록한다.

이번 조정의 목표는 단순히 체크를 더 띄우는 것이 아니라,
"왜 이 자리에서 체크가 살아야 하는지"를 이후 조정이 겹쳐도 잃지 않게 만드는 것이다.

즉 앞으로 NAS display 조정이 더 들어오더라도,

- 이 자리가 `하단 회복 시작`인지
- `구조 반등`인지
- `상단 continuation`인지
- `breakout reclaim confirm`인지

를 구분해서 각각 다른 규칙으로 다룰 수 있게 만든다.

## 2. 이번 조정 전 문제

NAS 2차 조정까지는 상단 continuation 남발을 줄이기 위해
`nas_upper_continuation_soft_cap`을 넣은 상태였다.

이 방향 자체는 맞았지만,
상단 문맥에서 나오는 장면 중에는
그냥 continuation이 아니라
"중요한 breakout reclaim confirm" 성격인 자리도 있었다.

즉 이전 상태에서는

- 상단 continuation도 눌러야 하고
- 상단 breakout reclaim confirm은 살려야 하는데

둘 다 단순히 `upper context`로만 읽히면
좋은 자리까지 같이 죽을 수 있었다.

## 3. 이번 조정의 핵심

이번 3차 조정에서는
`display importance source`와
`display importance adjustment`를 분리해서 기록하도록 바꿨다.

### 3-1. 새 source reason 추가

`consumer_check_state_v1`에 아래 필드를 추가했다.

- `display_importance_source_reason`

이 값은 "이 체크가 왜 강해졌는가"를 기록한다.

현재 NAS에서는 아래 source reason이 들어간다.

- `nas_lower_recovery_start`
- `nas_structural_rebound`
- `nas_breakout_reclaim_confirm`

### 3-2. NAS breakout reclaim 예외 처리

`lower_rebound_confirm + nas_clean_confirm_probe + upper_context + bb_state=UPPER_EDGE`
조합은 단순 continuation이 아니라
`nas_breakout_reclaim_confirm`으로 읽도록 했다.

이렇게 하면 이후 상단 continuation soft-cap이 걸리더라도,
정말 살려야 하는 breakout reclaim confirm은 예외 처리할 수 있다.

### 3-3. adjustment reason 분리 유지

기존처럼 `display_importance_adjustment_reason`은 따로 유지한다.

즉 이후에는

- source reason = 왜 살렸는가
- adjustment reason = 왜 눌렀는가

를 별개로 읽을 수 있다.

이 구조가 있어야 이후 조정이 겹쳐도
"왜 여기 체크가 떴고 왜 저긴 죽었는지"를 잃지 않는다.

## 4. 실제 코드 변경 요지

대상 파일:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

핵심 변경:

1. `_display_importance_source_reason_v1(...)` 추가
2. build 단계에서 `display_importance_source_reason`를 state에 기록
3. resolve 단계에서 `nas_upper_continuation_soft_cap`이
   `nas_breakout_reclaim_confirm` source는 누르지 않도록 예외 처리

## 5. 왜 이게 중요한가

이번 조정의 진짜 의미는 NAS를 한 번 더 살렸다는 것보다,
앞으로 조정이 겹쳐도 reason chain을 보존할 수 있게 됐다는 데 있다.

즉 이후 NAS에서 또 조정이 들어오더라도
아래처럼 읽을 수 있다.

- 이 자리는 `하단 회복 시작`이라 살렸다
- 이 자리는 `구조 반등`이라 2개 체크다
- 이 자리는 `상단 continuation`이라 soft-cap으로 눌렀다
- 이 자리는 `breakout reclaim confirm`이라 upper soft-cap 예외다

이 구분이 없으면 later tuning이 겹칠수록
체크가 왜 떴는지 설명이 안 되는 상태로 돌아간다.

## 6. 테스트

관련 테스트는 아래를 기준으로 잠갔다.

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)

특히 아래 성격이 확인돼야 한다.

- NAS lower recovery start는 `3개 체크`
- NAS structural rebound는 `2개 체크`
- NAS upper continuation은 과장되지 않음
- NAS breakout reclaim confirm은 상단 문맥에서도 `2개 체크`로 살아남음

## 7. 현재 해석

이번 3차 조정으로 NAS는 단순히 "더 보이게" 된 게 아니라,
체크가 살아나는 이유와 눌리는 이유를 다음 조정에서도 추적 가능한 상태가 됐다.

한 줄로 정리하면 아래와 같다.

```text
NAS 3차 조정의 본질은 체크를 더 띄우는 것이 아니라,
좋은 체크와 눌러야 할 체크를 reason 단위로 구분해
이후 조정이 겹쳐도 설명 가능한 상태를 만든 것이다.
```
