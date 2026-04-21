# State-Forecast to Product-Acceptance Handoff

## Docs Hub

문서가 많아졌으므로, 전체 네비게이션은 먼저
[product_acceptance_docs_hub_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_docs_hub_ko.md)
를 본다.

## Active PA3 Follow-Up

PA1/PA2 정리 뒤 현재 메인축은 `PA3 wait / hold acceptance`다.
첫 구현축은 아래 문서 체인으로 이어진다.

- [product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_detailed_reference_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_checklist_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_delta_ko.md)
- [product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_nas_sell_adverse_wait_timeout_boundary_narrowing_fresh_closed_trade_followup_ko.md)

## Active PA4 Follow-Up

현재 `PA4 exit acceptance` kickoff 문서 체인은 아래다.

- [product_acceptance_pa4_exit_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_exit_acceptance_implementation_memo_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_detailed_reference_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_checklist_ko.md)
- [product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa4_nas_sell_protect_exit_adverse_wait_deferral_implementation_memo_ko.md)

## Recent XAU Follow-Up

최근 XAU middle-anchor guard wait residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md)

작성일: 2026-03-31 (KST)

## 1. 이 문서의 목적

이 문서는 다른 스레드에서 바로 이어 받아도 이해할 수 있게,
아래 네 가지를 한 번에 고정하는 handoff 문서다.

1. 원래 이미 되어 있던 것
2. 무엇이 실제 문제였는지
3. 그 문제 때문에 지금까지 무엇을 했는지
4. 다음 메인축이 무엇인지

즉 이 문서는 아래 한 줄을 문서화한 것이다.

```text
문제는 state/forecast raw가 완전히 없는 것이 아니라,
이미 가공된 상위 입력이 chart / wait / entry / exit 체감으로 유효하게 반영되지 않는다는 점이었다.
```

## 2. 원래 이미 되어 있던 것

### 2-1. scene 중심 chart/entry 구조

기본 구조는 이미 있었다.

- `scene / box / bb / probe_scene`가 먼저 자리를 읽고
- `check_stage / display_score / repeat_count`가 체크 강도를 만든다
- painter는 그 결과를 화면에 그린다

핵심 owner:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

즉 원래부터 “차트에 뭔가를 띄우는 구조”는 있었다.

### 2-2. 상위 가공 입력도 이미 있었다

아래 입력도 이미 시스템 안에 있었다.

- `StateVector v2`
- `EvidenceVector`
- `BeliefState`
- `BarrierState`
- `TransitionForecast`
- `TradeManagementForecast`

핵심 source:

- [builder.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\builder.py)
- [advanced_inputs.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\state\advanced_inputs.py)
- [forecast_features.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_features.py)
- [forecast_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\forecast_engine.py)

즉 원래 문제는 “아무 데이터도 없어서 못 한다”가 아니었다.

## 3. 실제 문제는 무엇이었나

사용자 관찰 기준 문제는 아래였다.

- 체크가 떠야 할 곳에 안 뜬다
- 중요하지 않은 continuation에서 체크가 남발한다
- 시장 힘이 바뀌었는데도 체크 표기가 그 변화를 충분히 반영하지 못한다
- BUY/SSELL awareness가 청산/역방향 판단에 도움 되게 살아 있지 않다
- 더 심하게는 시장 방향 변화와 반대로 느껴지는 표기/판단도 생긴다

즉 핵심 문제는 아래였다.

```text
scene는 자리를 읽지만,
state / evidence / belief / barrier / forecast 가공값이
최종 chart / wait / entry / exit 체감에 충분히 유효하게 먹지 않는다.
```

### 3-1. 이 문제가 왜 중요했나

사용자가 원한 건 “체크를 많이 띄우는 것”이 아니라 아래였다.

- 하단 반전 시작은 강하게
- 중간 재상승은 적당히
- continuation은 약하게
- 혼잡 장세에서는 confetti 금지
- 그래도 청산/역방향 판단용 약한 awareness는 남기기

이 요구는 raw detector 하나로 해결되지 않는다.

즉 필요한 것은:

- `scene = 자리 의미 owner`
- `state / evidence / belief / barrier / forecast = 강도/억제/awareness modifier`

라는 공통 구조였다.

## 4. 그래서 왜 다시 State / Evidence / Belief / Barrier / Forecast를 점검했나

사용자가 아래 레이어를 다시 본 이유는 명확하다.

| 레이어 | 다시 점검한 이유 |
|---|---|
| `State` | 시장 변화와 장세 temperament가 실제 표기/대기/진입에 먹는지 확인 |
| `Evidence` | 지금 어느 방향 증거가 실제로 더 강한지 체크 강도에 반영되는지 확인 |
| `Belief` | 눌림/잡음 속에서도 thesis가 유지되는지 판단에 반영되는지 확인 |
| `Barrier` | 구조적으로 쉬운 자리/어려운 자리가 체크와 readiness에 먹는지 확인 |
| `Forecast` | act/wait/cut 시나리오 예측이 실제 표기와 관리 판단에 연결되는지 확인 |

즉 목적은 `raw를 무작정 더 넣기`보다
`이미 가공된 상위 입력이 진짜 유효하게 반영되는지 다시 검증`하는 것이었다.

## 5. 그래서 지금까지 무엇을 했나

## 5-1. SF0~SF6: state/forecast validation

먼저 `state가 부족한가 / activation이 약한가 / usage가 비는가 / value path가 약한가`를 분리해서 봤다.

기준 문서:

- [state_forecast_validation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_validation_detailed_reference_ko.md)
- [state_forecast_validation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_validation_execution_roadmap_ko.md)

공식 결론:

- broad raw add는 지금 1순위가 아님
- raw surface는 이미 넓음
- `order_book`만 targeted activation outlier
- 큰 병목은 `usage / value path / bridge`

특히 확인된 것:

- state/forecast surface는 대부분 존재
- tick/event는 살아 있음
- order_book은 거의 비활성
- `p_false_break`, `p_continue_favor`, `p_fail_now`는 separation이 약함

즉 “입력이 없다”보다 “가공된 의미가 실제 value path로 잘 안 먹는다”가 더 큰 문제였다.

## 5-2. BF1~BF7: bridge-first refinement

그 다음에는 raw를 더 넣지 않고,
이미 있는 상위 입력을 작은 bridge summary로 다시 묶었다.

기준 문서:

- [bridge_first_refinement_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_refinement_detailed_reference_ko.md)
- [bridge_first_refinement_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_refinement_execution_roadmap_ko.md)
- [bridge_first_bf7_close_out_handoff_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_bf7_close_out_handoff_detailed_reference_ko.md)

실제 구현된 bridge:

- BF1 `act_vs_wait_bias_v1`
- BF2 `management_hold_reward_hint_v1`
- BF3 `management_fast_cut_risk_v1`
- BF4 `trend_continuation_maturity_v1`
- BF5 `advanced_input_reliability_v1`
- BF6 `detail_to_csv_activation_projection_v1`
- BF7 close-out / handoff

가장 중요한 의미는 이거다.

```text
raw를 더 넣기 전에,
이미 있는 State / Evidence / Belief / Barrier / Forecast를
chart / wait / entry / hold / exit / forecast가 같이 읽을 수 있는 bridge로 재구성했다.
```

## 5-3. symbol별 product acceptance 조정도 병행했다

사용자 스크린샷을 기준으로 NAS/XAU/BTC 차트 체크를 조정했다.

관련 문서:

- [nas_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\nas_product_acceptance_casebook_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_confirm_forecast_wait_no_probe_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_confirm_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_confirm_forecast_wait_no_probe_hide_delta_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_forecast_wait_display_contract_delta_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_reject_probe_promotion_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_reject_probe_promotion_wait_display_contract_delta_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_forecast_wait_no_probe_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_break_fail_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_break_fail_forecast_wait_no_probe_hide_delta_ko.md)
- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_outer_band_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_outer_band_probe_guard_wait_display_contract_delta_ko.md)
- [xau_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_casebook_reference_ko.md)
- [btc_product_acceptance_casebook_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_casebook_reference_ko.md)

여기서 얻은 가장 중요한 결론은:

- 심볼별로 부분 튜닝은 가능하다
- 하지만 계속 심볼별 예외만 쌓으면 다시 얽힌다
- 이제는 공통 modifier 구조로 올려야 한다

## 6. 지금 공식적으로 고정된 판단

### 6-1. 하지 말아야 할 것

지금 바로 하면 안 되는 건 아래다.

- broad raw add
- broad secondary raw expansion
- broad collector rebuild
- threshold-only 튜닝 우선
- 심볼별 ad hoc 예외만 계속 추가

### 6-2. 현재까지 닫힌 것

- state/forecast validation은 SF6까지 close-out
- bridge-first refinement는 BF7까지 close-out

즉 지금 시점의 문제는 더 이상 “분석이 부족하다”가 아니다.

## 7. 다음에 할 것

다음 메인축은 아래다.

```text
product_acceptance_common_state_aware_display_modifier_v1
```

이게 다음인 이유는 명확하다.

- BF bridge가 이미 생겼다
- 이제 모든 심볼이 같은 공통 구조를 타야 한다
- `scene owner + bridge modifier` 구조를 실제 차트 acceptance에 연결해야 한다

### 7-1. 다음 단계에서 해야 할 것

1. 모든 심볼 공통 display modifier contract 정의
2. `scene`와 `modifier` owner 분리 고정
3. state/evidence/belief/barrier/forecast bridge를 chart acceptance에 공통 연결
4. 심볼별로는 threshold만 따로 둠
5. 그 다음에 entry/wait/exit acceptance를 다시 내려감

다음 active 문서 기준은 아래 순서로 고정한다.

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_detailed_reference_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_checklist_ko.md)
- [product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_structural_wait_visibility_boundary_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_structural_wait_visibility_boundary_delta_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_probe_guard_wait_check_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_probe_guard_wait_check_display_contract_delta_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_guard_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_guard_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_sell_outer_band_no_probe_wait_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_sell_outer_band_no_probe_wait_hide_delta_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_rebound_forecast_wait_no_probe_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_rebound_forecast_wait_no_probe_hide_delta_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_middle_anchor_upper_reclaim_no_probe_wait_hide_delta_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_structural_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_structural_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_promotion_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_probe_promotion_wait_display_contract_delta_ko.md)

즉 PA 쪽도 앞으로는
`상세 reference -> 구현 체크리스트 -> 구현 memo`
순서로 로그를 남긴다.

### 7-2. 병렬 follow-up

아래 두 가지는 병렬 follow-up이다.

- `fresh BF5/BF6 row`가 쌓인 뒤 SF3/SF4 rerun
- `order_book availability`가 계속 gap인지 좁게 확인

## 8. 다른 스레드에서 이어받을 때 한 줄 요약

다른 스레드에서는 아래 한 줄을 기준으로 시작하면 된다.

```text
문제는 state/forecast raw 부족이 아니라,
이미 가공된 상위 입력이 chart/product acceptance에 유효하게 반영되지 않는 것이었고,
그래서 SF로 검증하고 BF로 bridge를 만든 뒤,
이제 다음 메인축은 모든 심볼 공통 state-aware display modifier로 넘어간 상태다.
```
### Recent PA1 Follow-Up

최근 BTC outer-band repeated wait residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md)

### Recent XAU Outer-Band Follow-Up

최신 XAU outer-band probe energy-soft-block residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)

### Recent XAU Upper-Reject Confirm Follow-Up

최신 XAU upper-reject confirm energy-soft-block residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

### Recent XAU Upper-Break-Fail Follow-Up

최신 XAU upper-break-fail confirm energy-soft-block residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

### Recent XAU Upper-Reject Probe Forecast Follow-Up

최신 XAU upper-reject probe forecast residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_forecast_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md)

### Recent XAU Mixed Forecast Follow-Up

최신 XAU mixed confirm forecast wait residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_forecast_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_forecast_wait_visibility_relief_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_forecast_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent BTC Lower-Probe Guard Follow-Up

최근 BTC lower-rebound guarded probe residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_lower_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_lower_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_lower_probe_guard_wait_display_contract_delta_ko.md)

### Recent BTC Middle-Anchor Hidden Follow-Up

최근 BTC middle-anchor no-probe hidden residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_middle_anchor_wait_hide_without_probe_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_middle_anchor_wait_hide_without_probe_delta_ko.md)

### Recent XAU Mixed Energy Follow-Up

최근 XAU upper-reject mixed confirm energy-soft-block residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

### Recent XAU Upper-Reject Probe Promotion Follow-Up

XAU upper-reject probe promotion residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_probe_promotion_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_probe_promotion_wait_display_contract_turnover_followup_ko.md)

### Recent NAS Upper-Break-Fail Energy Follow-Up

NAS upper-break-fail energy-soft-block residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_delta_ko.md)

### Recent NAS Upper-Break-Fail Energy Second Follow-Up

- [product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_nas_upper_break_fail_confirm_energy_soft_block_wait_display_contract_second_followup_ko.md)

### Recent XAU Upper-Reject Confirm Forecast Follow-Up

- [product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_upper_reject_confirm_forecast_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_forecast_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_upper_reject_confirm_forecast_wait_display_contract_delta_ko.md)

### Recent BTC Upper-Reject Forecast / Preflight Follow-Up

- [product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_reject_forecast_and_preflight_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_reject_forecast_and_preflight_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_upper_reject_forecast_and_preflight_wait_display_contract_delta_ko.md)

### Recent BTC Upper-Sell Forecast / Preflight Follow-Up Extension

- [product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_upper_sell_forecast_preflight_wait_followup_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_sell_forecast_preflight_wait_followup_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_upper_sell_forecast_preflight_wait_followup_delta_ko.md)

### Recent XAU Outer-Band Probe Guard Wait Mirror

- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_outer_band_probe_guard_wait_display_contract_delta_ko.md)

### Recent XAU Lower-Probe Guard Wait Mirror

- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_lower_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_delta_ko.md)

### Recent BTC Upper-Sell Promotion / Energy Follow-Up

- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_sell_promotion_energy_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_sell_promotion_energy_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent XAU Lower-Probe Fresh Runtime Follow-Up

- [product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_lower_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent BTC Upper-Break-Fail Entry-Gate / Energy Follow-Up

- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_btc_upper_break_fail_entry_gate_energy_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_btc_upper_break_fail_entry_gate_energy_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent XAU Middle-Anchor Probe Guard Follow-Up

- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_middle_anchor_probe_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_middle_anchor_probe_guard_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent Entry-Decision Chart Surface Logging Fix

이번 묶음은 특정 symbol 축 하나가 아니라,
`consumer_check_state_v1`의 chart surface가 live `entry_decisions.csv` flat payload로
실제 기록되도록 만든 공통 logging fix이다.

- [product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_detailed_reference_ko.md)
- [product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_checklist_ko.md)
- [product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_entry_decision_hot_payload_chart_surface_logging_fix_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_entry_decision_hot_payload_chart_surface_logging_fix_fresh_runtime_followup_ko.md)

### Recent XAU Upper-Reclaim Hidden Suppression Follow-Up

- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_upper_reclaim_wait_hide_without_probe_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_upper_reclaim_wait_hide_without_probe_fresh_runtime_followup_ko.md)

### Recent XAU Outer-Band Probe Entry-Gate Wait Follow-Up

- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_xau_outer_band_probe_entry_gate_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_xau_outer_band_probe_entry_gate_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent NAS/BTC Upper-Reject Mixed Energy Follow-Up

이번 묶음은 active runtime에서 새로 드러난
`SELL + upper_reject_mixed_confirm + energy_soft_block + execution_soft_blocked`
mirror residue를 NAS/BTC에 공통 wait contract로 올린 기록이다.

- [product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_btc_upper_reject_mixed_confirm_energy_soft_block_wait_display_contract_fresh_runtime_followup_ko.md)

### Recent Sell Entry-Gate Wait Display Contract Follow-Up

이번 묶음은 `BTC/NAS upper_break_fail_confirm`와 `XAU upper_reject_mixed_confirm` entry-gate blocked family를
공통 `WAIT + wait_check_repeat` 계약으로 복구한 follow-up이다.

중요한 포인트는 두 단계였다.

- policy mirror만 먼저 올렸을 때 first fresh XAU row가 여전히 blank/hide로 찍혔고
- 그래서 hidden baseline에서도 modifier가 visibility를 restore하도록 follow-up을 한 번 더 넣었다

- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_detailed_reference_ko.md)
- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_checklist_ko.md)
- [product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_sell_entry_gate_wait_display_contract_followup_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_sell_entry_gate_wait_display_contract_followup_fresh_runtime_followup_ko.md)

### Recent NAS Balanced Conflict Hidden Suppression Final Cleanup

이번 묶음은 PA1에서 끝까지 남아 있던
`NAS100 + conflict_box_upper_bb20_lower_lower_dominant_observe + observe_state_wait`
family를 accepted hidden suppression으로 닫은 마지막 정리다.

- [product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_detailed_reference_ko.md)
- [product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_implementation_checklist_ko.md)
- [product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa1_nas_balanced_conflict_wait_hide_without_probe_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_balanced_conflict_wait_hide_without_probe_delta_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_balanced_conflict_wait_hide_without_probe_delta_ko.md)
- [product_acceptance_pa0_refreeze_after_nas_balanced_conflict_wait_hide_without_probe_fresh_runtime_followup_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa0_refreeze_after_nas_balanced_conflict_wait_hide_without_probe_fresh_runtime_followup_ko.md)

### PA3 Kickoff

PA1/PA2가 닫힌 현재 기준으로 다음 메인축은 `PA3 wait / hold acceptance`다.
kickoff 기준선과 first target family는 아래 문서에 고정했다.

- [product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_detailed_reference_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_checklist_ko.md)
- [product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_pa3_wait_hold_acceptance_implementation_memo_ko.md)
