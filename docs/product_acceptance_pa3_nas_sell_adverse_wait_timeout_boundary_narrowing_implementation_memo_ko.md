# Product Acceptance PA3 NAS Sell Adverse-Wait Timeout Boundary Narrowing Implementation Memo

## 구현 요약

이번 PA3-1 first patch는 [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)의
`_should_delay_adverse_exit(...)` 경계를 직접 좁힌 것이다.

핵심 변화:

- `tf_confirm=True`면 adverse wait max를 더 짧게 본다
- 그중 `peak_profit`이 약한 trade는 더 짧은 weak-peak cap을 적용한다

추가 config:

- `ADVERSE_WAIT_TF_CONFIRM_MAX_SECONDS`
- `ADVERSE_WAIT_TF_CONFIRM_WEAK_PEAK_USD`
- `ADVERSE_WAIT_TF_CONFIRM_WEAK_PEAK_MAX_SECONDS`

## 의도

의미는 아주 단순하다.

- opposite 확인이 이미 붙었고
- 기존 trade가 meaningful green room도 못 만들었으면
- `better exit`를 기다리는 시간을 짧게 하자

반대로:

- peak가 충분히 있었던 trade는 기존 recovery wait를 더 유지한다

## 검증 포인트

- weak peak + tf_confirm는 `60s` 시점에 timeout 되도록 잠근다
- meaningful peak + tf_confirm는 같은 시점에 아직 `holding`이 유지되도록 잠근다

## baseline 메모

이 축은 closed-trade 기반 queue에 반영되는 phase라서,
코드 적용 직후 PA0 수치가 바로 바뀌지 않을 수 있다.
즉 `must_hold / must_release / bad_exit` 변화는 새 close row가 쌓인 뒤 확인하는 것이 맞다.

## 검증 및 런타임

실행한 검증:

- `pytest -q tests/unit/test_exit_service.py`
- `pytest -q tests/unit/test_wait_engine.py`
- `pytest -q tests/unit/test_loss_quality_wait_behavior.py`

현재 묶음 결과:

- 세 테스트를 함께 다시 돌렸을 때 `49 passed`
- `main.py`는 [cfd_main_restart_20260401_185946.out.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_185946.out.log), [cfd_main_restart_20260401_185946.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_185946.err.log) 기준으로 재시작됐다
- 현재 관측 PID는 `24384` (`main.py`) / `27504` (`backend/main.py`)다

## PA0 refreeze 메모

이번 턴에서 [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)
를 다시 얼렸고 결과는 아래 문서에 정리했다.

- [product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md)

이번 refreeze 해석:

- `must_hold 2`는 그대로였다
- 대상 family도 여전히 `NAS100 SELL + hard_guard=adverse + adverse_wait=timeout + bad_wait` 2건이다
- 대신 이건 구현 실패가 아니라, 새 close row 없이 기존 closed-trade artifact를 다시 읽은 결과로 보는 것이 맞다

후속 fresh close 확인은 아래 문서에 남긴다.

- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md)
