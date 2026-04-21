# Product Acceptance PA4 Exit Acceptance Implementation Memo

## 상태

이번 문서는 `구현 완료 memo`가 아니라 `PA4 kickoff memo`다.
즉 지금은 phase를 열고, baseline과 first target을 고정한 상태다.

## kickoff baseline

기준:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

현재 수치:

- `must_release = 10`
- `bad_exit = 10`

현재는 `PA3 must_hold 2`가 아직 남아 있지만,
동시에 `final close action quality`도 이미 별도 축으로 분리해서 볼 수 있는 상태다.

## first target family

현재 가장 먼저 건드려야 할 축은 아래다.

```text
NAS100 SELL
+ conservative profile
+ wait_quality_label=no_wait
+ Protect Exit
+ Flow: BB 20/2 mid 돌파지지 (+80점)
+ TopDown 1M: bullish (+20점)
+ hard_guard=adverse
```

이 family가 `must_release / bad_exit`에 가장 두껍게 겹친다.

즉 이 trade들은 “더 버텼어야 했나”보다
“Protect Exit라는 final close action이 너무 빨랐나”를 먼저 봐야 하는 케이스로 본다.

## kickoff owner

primary owner:

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
- [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)

evidence / label owner:

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/trade_closed_history.csv)

## Step 1 read 결과

이번 턴에서 실제로 읽고 고정한 흐름은 아래다.

- [exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_service.py)
  - reason normalize와 stage mapping을 가진다
  - `Protect Exit`, `Lock Exit`, `Adverse Stop`를 어느 stage로 읽을지 결정한다
- [exit_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_engines.py)
  - `ExitStageRouter`가 execution plan을 만든다
  - `ExitActionExecutor`가 실제 `close_position(...)`를 호출한다
- [wait_engine.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/wait_engine.py)
  - exit utility winner와 wait-selected shadow bundle을 만든다
- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
  - `wait_quality_label`과 `loss_quality_label`을 closed-trade artifact에 기록한다

정리하면 PA4-1 first patch는
`exit_service.py / exit_engines.py`의 final close action quality를 먼저 보고,
그 다음 `trade_csv_schema.py` label과의 정합성을 맞추는 순서가 적절하다.

## active PA4 문서 체인

- [product_acceptance_pa4_exit_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_detailed_reference_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_checklist_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_memo_ko.md)

## 현재 상태

PA4-1 first patch는 이미 코드와 테스트까지 올라간 상태다.

- [exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/exit_hard_guard_action_policy.py) 에서 `wait_adverse defer` 우선순위 반영
- [test_exit_hard_guard_action_policy.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_hard_guard_action_policy.py) 로 direct unit test 고정
- [test_exit_service.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_exit_service.py) 로 연결 회귀 확인

다만 이번 phase도 closed-trade artifact 기준으로 확인되므로,
현재는 `코드/테스트 반영 완료`, `fresh closed trade 재발 대기` 상태로 본다.
closed source correction:

- [product_acceptance_pa3_pa4_closed_history_runtime_path_correction_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_pa4_closed_history_runtime_path_correction_implementation_memo_ko.md)
- [product_acceptance_pa3_pa4_closed_trade_wait_label_and_release_seed_alignment_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_pa4_closed_trade_wait_label_and_release_seed_alignment_implementation_memo_ko.md)

## active PA4-2 chain

- [product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_detailed_reference_ko.md)
- [product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_implementation_checklist_ko.md)
- [product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_context_meaningful_giveback_early_exit_bias_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_exit_context_meaningful_giveback_early_exit_bias_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_exit_context_meaningful_giveback_early_exit_bias_delta_ko.md)

## active PA4-3 chain

- [product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_detailed_reference_ko.md)
- [product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_implementation_checklist_ko.md)
- [product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_adverse_bad_loss_weak_peak_fast_protect_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_adverse_bad_loss_weak_peak_fast_protect_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_adverse_bad_loss_weak_peak_fast_protect_delta_ko.md)

## active PA4-4 chain

- [product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_detailed_reference_ko.md)
- [product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_implementation_checklist_ko.md)
- [product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_topdown_exit_context_fast_exit_bias_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_countertrend_topdown_exit_context_fast_exit_bias_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_countertrend_topdown_exit_context_fast_exit_bias_delta_ko.md)

## active PA4-5 chain

- [product_acceptance_pa4_countertrend_no_green_fast_cut_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_no_green_fast_cut_detailed_reference_ko.md)
- [product_acceptance_pa4_countertrend_no_green_fast_cut_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_no_green_fast_cut_implementation_checklist_ko.md)
- [product_acceptance_pa4_countertrend_no_green_fast_cut_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_no_green_fast_cut_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_countertrend_no_green_fast_cut_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_countertrend_no_green_fast_cut_delta_ko.md)

## active PA4-6 chain

- [product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_detailed_reference_ko.md)
- [product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_implementation_checklist_ko.md)
- [product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_bad_exit_exit_context_exit_now_best_teacher_label_narrowing_delta_ko.md)

## active PA4-7 chain

- [product_acceptance_pa4_countertrend_continuation_release_pressure_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_continuation_release_pressure_detailed_reference_ko.md)
- [product_acceptance_pa4_countertrend_continuation_release_pressure_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_continuation_release_pressure_implementation_checklist_ko.md)
- [product_acceptance_pa4_countertrend_continuation_release_pressure_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_countertrend_continuation_release_pressure_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa4_countertrend_continuation_release_pressure_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa4_countertrend_continuation_release_pressure_delta_ko.md)
