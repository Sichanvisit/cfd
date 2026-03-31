# Product Acceptance Reorientation Execution Roadmap

## Recent XAU Follow-Up

최근 XAU middle-anchor guard wait residue 정리는 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_middle_anchor_guard_wait_display_contract_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_middle_anchor_guard_wait_display_contract_delta_ko.md)

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 현재 우선순위를
`제품 acceptance 재정렬`
로 다시 잡았을 때,
실제 실행 순서를 단계별로 쪼개기 위한 로드맵이다.

상세 기준은 아래 문서를 함께 본다.

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [state_forecast_product_acceptance_handoff_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_product_acceptance_handoff_ko.md)

## 2. 전체 흐름

```text
PA0. baseline freeze and target capture
-> PA1. chart acceptance
-> PA2. entry acceptance
-> PA3. wait / hold acceptance
-> PA4. exit acceptance
-> PA5. product-level integration review
-> PA6. profit sanity and return to P7
```

## 3. PA0. Baseline Freeze and Target Capture

### 목표

지금 시스템이 어떻게 보이고 어떻게 들어가고 어떻게 청산하는지 기준선을 먼저 고정한다.

### 해야 할 일

1. 최근 chart snapshot / entry rows / exit rows를 모은다
2. 사용자가 보기에
   - 마음에 드는 장면
   - 마음에 안 드는 장면
   을 각각 묶는다
3. 아래 네 분류 casebook을 만든다
   - must-show / must-hide
   - must-enter / must-block
   - must-hold / must-release
   - good-exit / bad-exit

### 주 대상 자료

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [runtime_status.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [chart_flow_distribution_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)

### 완료 기준

- “좋은 예 / 나쁜 예”가 추상 불만이 아니라 casebook으로 고정된다

### active 기준 문서

- [product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md)
- [product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md)
- [product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_memo_ko.md)

### 이번 축의 로그 원칙

PA 축도 아래 순서로 진행한다.

```text
상세 reference
-> 구현 체크리스트
-> 구현 memo
```

현재 PA1 chart acceptance의 첫 구현 anchor 문서는 아래다.

- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_checklist_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md)

현재 PA1에서 이어진 하위축 문서는 아래다.

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

## 4. PA1. Chart Acceptance

### 목표

차트 표기가 내가 보고 싶은 방식과 최대한 일치하도록 다시 맞춘다.

### 건드릴 owner

- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py)
- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py)
- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py)

### 해야 할 일

1. must-show / must-hide casebook 확정
2. visually-similar scene alignment 재검토
3. `display_score` ladder 재조정
4. symbol별 과표시 / 과억제 balance tuning
5. chart acceptance snapshot 재검토

### 핵심 질문

- 왜 이 장면은 뜨고 왜 이 장면은 안 뜨는가
- 이 표기가 실제 의미보다 세거나 약하지 않은가

### 완료 기준

- 사용자 기준 “여긴 떠야 한다 / 여긴 뜨면 안 된다”가 크게 줄어든다

## 5. PA2. Entry Acceptance

### 목표

자동 진입이 실제로 내가 동의하는 자리에서만 열리도록 다시 맞춘다.

### 건드릴 owner

- [observe_confirm_router.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\core\observe_confirm_router.py)
- [entry_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [entry_probe_plan_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_probe_plan_policy.py)
- [entry_default_side_gate_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_default_side_gate_policy.py)

### 해야 할 일

1. recent adverse entry forensic 재수집
2. must-enter / must-block casebook 고정
3. late guard 중 일부를 early gate로 당길지 검토
4. probe promotion / confirm readiness / conflict suppression 재조정
5. entry acceptance review

### 핵심 질문

- 이 진입을 내가 승인할 수 있는가
- immediate adverse move를 맞는 family가 무엇인가

### 완료 기준

- “들어가자마자 반대로 가는” 가족이 줄고, 진입 설명이 더 납득 가능해진다

## 6. PA3. Wait / Hold Acceptance

### 목표

참아야 할 자리와 빨리 접어야 할 자리를 더 자연스럽게 구분하게 만든다.

### 건드릴 owner

- [wait_engine.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\wait_engine.py)
- [entry_wait_state_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_state_policy.py)
- [entry_wait_decision_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_decision_policy.py)
- [entry_wait_state_bias_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_state_bias_policy.py)
- [entry_wait_edge_pair_bias_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_edge_pair_bias_policy.py)
- [entry_wait_probe_temperament_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_wait_probe_temperament_policy.py)

### 해야 할 일

1. good patience / bad patience casebook 작성
2. directional wait vs neutral wait를 다시 조정
3. hold patience / noise tolerance / probe patience 재조정
4. hold acceptance review

### 핵심 질문

- 너무 성급하게 놓치고 있지 않은가
- 의미 없이 오래 버티고 있지 않은가

### 완료 기준

- 기다림 체감이 더 자연스러워지고, 사용자 기준 “여긴 좀 더 봐야지”가 살아난다

## 7. PA4. Exit Acceptance

### 목표

청산을 “너무 이르거나 너무 늦은” 체감에서 벗어나게 다시 맞춘다.

### 건드릴 owner

- [exit_profile_router.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_profile_router.py)
- [exit_manage_positions.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_manage_positions.py)
- [exit_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_service.py)
- [exit_wait_state_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_wait_state_policy.py)
- [exit_reverse_action_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_reverse_action_policy.py)
- [exit_recovery_temperament_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_recovery_temperament_policy.py)
- [exit_stop_up_action_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\exit_stop_up_action_policy.py)

### 해야 할 일

1. good-exit / premature-exit / late-exit casebook 작성
2. reverse / recovery / partial / stop-up 경계 재조정
3. hold -> exit stage 전이 재조정
4. exit acceptance review

### 핵심 질문

- 여기서 나오는 게 맞았는가
- 더 들고 갔어야 했나
- reverse/recovery가 어색하게 섞이지 않는가

### 완료 기준

- 청산이 체감상 덜 어색해지고, 사용자가 납득 가능한 정리 흐름이 늘어난다

## 8. PA5. Product-Level Integration Review

### 목표

차트 / 진입 / 기다림 / 청산을 따로 고친 뒤 다시 한 체인으로 본다.

### 해야 할 일

1. 동일 scene를 chart -> entry -> wait -> exit 순으로 재검토
2. continuity / runtime summary / casebook 재확인
3. “차트는 좋아졌는데 entry가 깨진다” 같은 교차 부작용 점검

### 완료 기준

- 네 축을 따로가 아니라 같이 봤을 때도 방향이 맞다고 느껴진다

## 9. PA6. Profit Sanity and Return to P7

### 목표

제품 acceptance 재조정이 끝난 뒤, 수익/운영 surface를 다시 본다.

### 해야 할 일

1. P1 lifecycle 재검토
2. P2 expectancy 재검토
3. P3 anomaly 재검토
4. P4 compare 재검토
5. 필요하면 그 다음에만 P7 guarded overlay로 복귀

### 핵심 질문

- acceptance 개선이 실제 expectancy를 깨지 않았는가
- alert pressure가 더 나빠지지 않았는가

### 완료 기준

- 제품 체감과 수익 sanity가 동시에 유지된다

## 10. 지금 당장 가장 먼저 할 것

현재 가장 먼저 해야 하는 것은 아래 한 줄이다.

```text
PA0 baseline freeze + casebook capture를 먼저 하고,
그 다음 chart acceptance부터 다시 잡는다.
```

그리고 chart acceptance의 첫 구현은
`product_acceptance_common_state_aware_display_modifier_v1`
를 기준으로 시작한다.

즉 지금은 P7 apply를 더 미는 것보다,
`내가 원하는 차트/진입/기다림/청산` 기준을 먼저 고정하는 게 맞다.

## 11. 결론

이 로드맵의 핵심은 아래 한 줄이다.

```text
지금부터의 메인축은 운영 최적화가 아니라 제품 acceptance 재조정이며,
차트 -> 진입 -> 기다림 -> 청산 -> profit sanity 순으로 다시 맞추는 것이다.
```
## 12. Recent PA1 Follow-Up

가장 최근에 닫은 BTC chart acceptance 하위축은 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_btc_outer_band_probe_guard_wait_repeat_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_btc_outer_band_probe_guard_wait_repeat_visibility_relief_delta_ko.md)

## 13. Recent XAU Outer-Band Follow-Up

최신 XAU outer-band probe energy-soft-block follow-up은 아래 문서 체인으로 이어진다.

- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_detailed_reference_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_checklist_ko.md)
- [product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa1_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_implementation_memo_ko.md)
- [product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_refreeze_after_xau_outer_band_probe_energy_soft_block_wait_visibility_relief_delta_ko.md)
