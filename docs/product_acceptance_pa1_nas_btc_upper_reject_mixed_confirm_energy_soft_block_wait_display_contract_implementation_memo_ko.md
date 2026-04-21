# Product Acceptance PA1 NAS/BTC Upper-Reject Mixed-Confirm Energy-Soft-Block Wait Display Contract Implementation Memo

작성일: 2026-04-01 (KST)

## 1. 구현 요약

이번 수정은 NAS/BTC SELL mixed-confirm energy residue에
mirror wait contract를 추가한 것이다.

반영 파일:

- [chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)
- [consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [product_acceptance_pa0_baseline_freeze.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/product_acceptance_pa0_baseline_freeze.py)

추가 reason:

- `nas_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`
- `btc_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

## 2. 테스트

실행 결과:

- `pytest -q tests/unit/test_consumer_check_state.py` -> `116 passed`
- `pytest -q tests/unit/test_chart_painter.py` -> `104 passed`
- `pytest -q tests/unit/test_product_acceptance_pa0_baseline_freeze.py` -> `47 passed`

## 3. representative build 확인

current build 기준으로 아래 state는 모두 wait contract로 resolve된다.

- `NAS100 + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
- `BTCUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`

확인 포인트:

- `check_display_ready = True`
- `check_stage = BLOCKED`
- `blocked_display_reason = energy_soft_block`
- `chart_event_kind_hint = WAIT`
- `chart_display_mode = wait_check_repeat`
- `chart_display_reason = nas_/btc_upper_reject_mixed_confirm_energy_soft_block_as_wait_checks`

## 4. live 해석

post-restart short watch 기준으로는
fresh exact NAS/BTC mixed energy row가 아직 다시 안 떴다.

그래서 이번 축은

- code / tests / representative build는 완료
- PA0 actual cleanup은 fresh exact recurrence 대기

상태로 보는 것이 맞다.

## 5. PA0 latest

latest baseline:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `2026-04-01T16:17:41`

latest queue 기준으로는 아직 아래 backlog가 남아 있다.

- `must_block`: `BTCUSD + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked` `8`
- `must_block`: `NAS100 + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked` `4`

즉 이번 턴에서 contract는 선반영됐지만, PA0 queue는 old blank backlog 때문에 아직 남아 있는 상태다.

## 6. 연결 문서

- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md)
