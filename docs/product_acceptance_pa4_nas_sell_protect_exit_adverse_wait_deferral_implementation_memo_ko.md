# Product Acceptance PA4 NAS Sell Protect Exit Adverse-Wait Deferral Implementation Memo

## 구현 요약

이번 PA4-1 first patch는
[exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py)
에서 `adverse Protect Exit`보다 `wait_adverse defer`를 먼저 보게 순서를 조정한 것이다.

핵심 변화:

- 이전:
  - `tf_confirm + protect_now + profit<=target`이면 바로 `Protect Exit`
  - 그 뒤에야 `wait_adverse`를 봄
- 이후:
  - `wait_adverse=True`면 먼저 defer
  - wait contract가 꺼져 있을 때만 `adverse Protect Exit`

## 의도

의미는 단순하다.

- opposite 확인이 있고
- adverse-wait contract도 이미 기다림을 요청하는데
- final close hard guard가 먼저 닫아버리면
- `no_wait Protect Exit`가 과도하게 늘어난다

그래서 이번 patch는 `Protect Exit` 자체를 없애는 게 아니라,
`wait contract가 이미 살아 있는 경우`에만 먼저 defer를 태우게 만든 것이다.

## baseline 메모

이 축도 closed-trade 기반 queue에 반영되는 phase라서,
코드 적용 직후 `must_release / bad_exit` 수치가 바로 바뀌지 않을 수 있다.

## 검증

실행한 검증:

- `pytest -q tests/unit/test_exit_hard_guard_action_policy.py`
- `pytest -q tests/unit/test_exit_service.py`

결과:

- `test_exit_hard_guard_action_policy.py` -> `5 passed`
- `test_exit_service.py` -> `2 passed`

## 현재 상태

이번 축은 `코드/테스트`까지는 닫혔다.

- `wait_adverse=True`인 adverse context에서는 더 이상 `Protect Exit`가 먼저 short-circuit 되지 않는다
- 대신 actual `must_release / bad_exit` cleanup은 fresh closed trade가 더 쌓인 뒤 확인하는 것이 맞다
