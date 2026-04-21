# Product Acceptance PA3 NAS Sell Adverse-Wait Timeout Boundary Narrowing Implementation Checklist

- [x] `must_hold 2` target family 고정
- [x] `exit_service.py` adverse wait 경계 읽기
- [x] first patch 방향을 `tf_confirm + weak peak cap`으로 고정
- [x] config knob 추가
- [x] `exit_service.py` timeout cap 로직 추가
- [x] direct unit test 추가
- [x] `pytest -q tests/unit/test_exit_service.py`
- [x] `pytest -q tests/unit/test_wait_engine.py`
- [x] `pytest -q tests/unit/test_loss_quality_wait_behavior.py`
- [x] runtime 재시작
- [x] PA0 baseline refreeze
- [ ] fresh closed trade 누적 후 PA0 재평가

## 이번 축에서 기대하는 것

- `weak peak timeout bad_wait` family는 더 빨리 종료
- `meaningful peak recovery wait` family는 보존
- 즉 adverse wait를 전부 없애는 게 아니라, `나쁜 timeout만 먼저 줄이는 것`
