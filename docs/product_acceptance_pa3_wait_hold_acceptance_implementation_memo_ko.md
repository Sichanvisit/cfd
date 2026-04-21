# Product Acceptance PA3 Wait / Hold Acceptance Implementation Memo

## 상태

이번 문서는 `구현 완료 memo`가 아니라 `PA3 kickoff memo`다.
즉 지금은 phase를 열고, baseline과 first target을 고정한 상태다.

## kickoff baseline

기준:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

현재 수치:

- `must_hold = 2`
- `must_release = 10`
- `bad_exit = 10`

PA1/PA2가 닫힌 뒤 처음 남은 acceptance queue가 모두 `exit / wait / hold` 계열이라는 점이 이번 kickoff의 핵심이다.

## first target family

현재 가장 먼저 건드려야 할 축은 아래다.

```text
NAS100 SELL
+ conservative profile
+ hard_guard=adverse
+ adverse_wait=timeout(...)
+ wait_quality_label=bad_wait
```

이 family가 `must_hold 2`를 전부 채우고 있고,
동시에 `must_release / bad_exit`에도 일부 겹친다.

즉 이 trade들은 “나가는 액션이 나빴다” 이전에,
“adverse 구간에서 기다림이 적절했는가”가 먼저 문제인 케이스로 본다.

## kickoff owner

primary owner:

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
- [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py)
- [exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_rewrite_policy.py)
- [exit_wait_state_surface_contract.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_surface_contract.py)

evidence / test owner:

- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)
- [test_wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_wait_engine.py)
- [test_exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_policy.py)
- [test_exit_wait_state_rewrite_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_rewrite_policy.py)
- [test_exit_wait_state_surface_contract.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_wait_state_surface_contract.py)
- [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py)

## Step 1 read 결과

이번 턴에서 실제로 읽고 고정한 흐름은 아래다.

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
  - `adverse_wait_state` ticket state를 직접 들고 있다
  - `warmup -> recovery -> timeout -> holding` 문자열 reason도 여기서 만든다
  - 그래서 `must_hold 2` first patch의 primary owner다
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
  - exit wait input -> policy -> rewrite -> surface를 orchestration 한다
  - hold 체감이 runtime surface에 어떻게 남는지 보는 핵심 레이어다
- [exit_wait_state_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_wait_state_policy.py)
  - `green_close_hold`, `recovery_to_small_profit`, `recovery_to_breakeven`, `adverse_loss_expand` state family를 결정한다
  - 즉 time gate보다는 hold-state family owner에 가깝다

정리하면 PA3-1 first implementation은
`exit_service.py adverse_wait timeout family`를 먼저 보고,
그 뒤 `wait_engine.py / exit_wait_state_policy.py` 에서 hold surface와 label alignment를 맞추는 순서가 적절하다.

## Step 2 casebook 결과

이번 턴에서 `PA3 Step 2`는 아래 문서로 고정했다.

- [product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_casebook_mini_set_ko.md)

핵심 결과:

- `bad_wait` 대표 row는 `NAS SELL adverse timeout` 2건이다
- `no_wait control`은 `NAS SELL protect adverse`와 `XAU BUY protect plus_to_minus`로 잡았다
- 현재 closed-trade label surface에는 `good_wait / unnecessary_wait`가 없어서,
  phase 초반 비교 구조는 `bad_wait vs no_wait control`이 적절하다

## Step 3 design 결과

이번 턴에서 정리한 설계 결론은 아래다.

- 이번 `must_hold 2`는 `warmup` 문제가 아니라 `timeout 상한` 문제다
- `recovery_need`를 바로 건드릴 근거는 아직 없다
- `hold bias rewrite`는 이번 family의 1차 owner가 아니라 `exit_service.py adverse_wait` 이후 layer다
- closed-trade `wait_quality_label`은 runtime wait-state surface보다 더 좁고, 현재는 `good_wait / unnecessary_wait`가 아예 비어 있다

즉 first patch 방향을 `tf_confirm + weak peak cap`으로 잡은 판단은 유지하는 것이 맞다.

## phase 해석

- `PA3`는 hold patience / adverse wait / recovery wait를 다루는 phase다
- `PA4`는 final close action quality를 다루는 phase다

이번 kickoff에서 이 경계를 먼저 고정한 이유는,
현재 `must_release / bad_exit` queue 중 상당수가 사실은 `PA3` 문제를 먼저 포함하고 있기 때문이다.

## 다음 구현 순서

1. `exit_service.py` 의 `adverse_wait_state` timeout family 추적
2. wait-state surface와 closed-trade label 정합성 확인
3. first patch
4. PA0 refreeze
5. 그다음 PA4 exit quality 축으로 이동

## active PA3-1 문서 체인

- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_detailed_reference_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_checklist_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md)

## 현재 상태

PA3-1 first patch는 이미 코드와 테스트까지 올라간 상태다.

- [backend/core/config.py](/C:/Users/bhs33/Desktop/project/cfd/backend/core/config.py) 에 adverse wait cap knob 추가
- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py) 에 `tf_confirm + weak peak cap` 경계 추가
- [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py) 로 direct unit test 고정

다만 이번 phase는 closed-trade artifact 기준으로 확인되므로,
현재는 `코드/테스트/런타임 반영 완료`, `fresh closed trade 재발 대기` 상태로 본다.

후속 fresh close 확인:

- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md)
- [product_acceptance_pa3_pa4_closed_history_runtime_path_correction_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_pa4_closed_history_runtime_path_correction_implementation_memo_ko.md)
- [product_acceptance_pa3_pa4_closed_trade_wait_label_and_release_seed_alignment_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_pa4_closed_trade_wait_label_and_release_seed_alignment_implementation_memo_ko.md)
