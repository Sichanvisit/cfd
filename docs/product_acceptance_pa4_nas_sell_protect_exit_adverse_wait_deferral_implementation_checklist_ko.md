# Product Acceptance PA4 NAS Sell Protect Exit Adverse-Wait Deferral Implementation Checklist

- [x] `must_release / bad_exit` target family 고정
- [x] `exit_hard_guard_action_policy.py` owner 확인
- [x] first patch 방향을 `wait_adverse defer 우선`으로 고정
- [x] `adverse Protect Exit`보다 `wait_adverse`를 먼저 보도록 policy 순서 조정
- [x] direct unit test 추가
- [x] `pytest -q tests/unit/test_exit_hard_guard_action_policy.py`
- [x] `pytest -q tests/unit/test_exit_service.py`
- [ ] fresh closed trade 누적 후 PA0 재평가

## 이번 축에서 기대하는 것

- `NAS SELL adverse Protect Exit no_wait` family가 너무 빨리 닫히는 빈도를 줄인다
- `plus_to_minus` / `profit_giveback` hard guard는 그대로 유지한다
- PA3의 adverse-wait contract와 PA4의 final close action이 충돌하지 않게 만든다
