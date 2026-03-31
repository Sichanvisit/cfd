# R1 Stage E Micro Calibration Spec

## 1. 목적

이 문서는 [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)의 `R1. Stage E 미세조정`을 실제 구현 기준으로 고정하는 전용 spec이다.

R1의 목적은 아래 두 가지를 동시에 만족하는 것이다.

- 심볼별 체감 불균형을 줄인다.
- `probe -> confirm -> hold -> opposite edge exit` 흐름을 더 자연스럽게 만든다.

이 단계는 foundation을 다시 만드는 단계가 아니다. 이미 고정된 semantic, chart flow, execution contract 위에서 symbol temperament와 execution bias를 미세조정하는 단계다.

## 2. 기준 문서

- [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- [chart_flow_buy_wait_sell_guide_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\chart_flow_buy_wait_sell_guide_ko.md)
- [chart_flow_phase6_sequential_rollout_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\chart_flow_phase6_sequential_rollout_spec_ko.md)
- [chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\chart_flow_phase6_sequential_rollout_implementation_checklist_ko.md)
- [xau_btc_execution_tuning_short_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\xau_btc_execution_tuning_short_roadmap_ko.md)
- [ml_symbol_regime_calibration_proposal_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\ml_symbol_regime_calibration_proposal_ko.md)

## 3. 범위

### 3-1. 포함 범위

- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`
- `backend/services/entry_service.py`
- `backend/services/entry_engines.py`
- `backend/trading/chart_symbol_override_policy.py`
- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`

### 3-2. 비포함 범위

- `Position / Response / State / Evidence / Belief / Barrier` foundation 재정의
- chart flow vocabulary 변경
- semantic target/split 재설계
- promotion gate 확장
- API 안정성 자체 개선

## 4. 현재 기준선

2026-03-25 KST 기준 최신 [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)의 해석은 아래와 같다.

- `Stage A = advance`
- `Stage B = advance`
- `Stage C = advance`
- `Stage D = advance`
- `Stage E = advance`

현재 summary:

- `no immediate calibration target detected in latest window`
- `all rollout gates in the latest window are satisfied`

같은 시각 기준 최신 [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json) 요약:

| Symbol | Buy Presence | Sell Presence | Neutral | 최근 16캔들 핵심 |
| --- | ---: | ---: | ---: | --- |
| `BTCUSD` | `0.0625` | `0.3125` | `0.6250` | `BUY_PROBE 1`, `SELL_WAIT 5`, `WAIT 10`, `blocked_by = outer_band_guard 5 / energy_soft_block 3 / forecast_guard 1` |
| `NAS100` | `0.0625` | `0.1875` | `0.7500` | `BUY_WAIT 1`, `SELL_WAIT 1`, `SELL_PROBE 2`, `WAIT 12`, `nas_clean_confirm_probe = 14` |
| `XAUUSD` | `0.0625` | `0.2500` | `0.6875` | `BUY_WAIT 1`, `SELL_PROBE 1`, `SELL_READY 3`, `WAIT 11`, `xau_second_support_buy_probe = 3 / xau_upper_sell_probe = 2` |

추가 해석:

- `BTCUSD`는 latest window 기준으로 `BUY_PROBE`가 다시 살아났고, immediate calibration target에서는 해제됐다.
- `NAS100`은 second calibration 이후 `middle_sr_anchor_guard` 병목이 줄었고, Stage E advance 상태를 유지했다.
- `XAUUSD`는 `upper sell probe`와 `second support buy probe`가 모두 보이는 mixed window로 들어왔고, immediate calibration target에서는 해제됐다.

## 5. 현재 적용 상태

R1 전체는 아직 진행 중이지만, `Step 2`, `Step 3`, `Step 4`의 1차 조정은 반영된 상태다.

반영된 내용:

- XAU 1차
  - `backend/services/symbol_temperament.py`
    - `xau_upper_sell_probe` structural relief 문턱 완화
  - `backend/services/entry_service.py`
    - `xau_upper_sell_probe_energy_relief` 완화
    - `bb_state = UNKNOWN` 허용
    - candidate support 하한 완화
- BTC 1차
  - `backend/services/entry_engines.py`
    - duplicate lower buy suppression 강화
    - strong repeat quality일 때만 제한적으로 relief 허용
    - trace에 duplicate suppression 설명 필드 추가
  - `backend/services/wait_engine.py`
    - `btc_lower_hold_bias`, `btc_lower_mid_noise_hold_bias` 완화 및 hold delta 강화
  - `backend/services/exit_profile_router.py`
    - `range_lower_reversal_buy_btc_balanced` wait patience 상향
    - opposite belief / edge rotation에서는 다시 빠르게 보수화되도록 균형 조정
  - follow-up
    - 실거래 BTC auto lower reversal buy 검토에서 `support_hold_profile`가 setup-specific balanced recovery보다 먼저 적용되어 `btc_lower_hold_bias`가 실제 거래에 반영되지 않는 케이스를 확인
    - `BTCUSD + range_lower_reversal_buy` 조합에서는 `range_lower_reversal_buy_btc_balanced`가 recovery policy 우선권을 갖도록 좁게 수정
- NAS 1차
  - `backend/trading/chart_symbol_override_policy.py`
    - `clean_confirm` floor / advantage / tolerance 완화

현재 상태 해석:

- XAU는 `upper sell probe`가 완전히 중립으로 눌리던 단계는 벗어났다.
- BTC는 lower buy duplicate suppression과 hold patience owner가 더 명확해졌다.
- BTC는 follow-up으로 `support_hold_profile` 우선 적용 때문에 lower reversal buy hold bias가 죽던 문제까지 정리했다.
- NAS는 clean confirm이 과도하게 눌리던 baseline을 조금 완화한 상태다.
- latest 재관측과 `Stage E` 업데이트가 반영됐다.

## 6. 심볼별 조정 방향

### XAU

목표:

- `upper reject -> sell probe -> confirm` 흐름을 더 자연스럽게 만든다.
- `upper sell probe`가 soft block에 과하게 죽지 않게 한다.

현재 상태:

- Step 2 1차 적용 완료
- 재관측과 추가 confirm release 보정은 아직 남아 있다.

주요 관찰 항목:

- `xau_upper_sell_probe`
- `forecast_guard`
- `probe_not_promoted`
- `confirm_suppressed`

### BTC

목표:

- lower buy 중복 진입을 더 억제한다.
- lower buy hold patience를 높인다.
- middle noise만으로 너무 빨리 exit되지 않게 만든다.

주요 owner:

- `backend/services/entry_engines.py`
- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`

주요 관찰 항목:

- `btc_duplicate_edge_suppression`
- `range_lower_reversal_buy_btc_balanced`
- `btc_lower_hold_bias`
- `btc_lower_mid_noise_hold_bias`
- `support_hold_profile -> range_lower_reversal_buy_btc_balanced` 우선순위

### NAS

목표:

- `clean confirm / upper sell / neutral wait` 밸런스를 맞춘다.
- `WAIT`가 실제 neutral인지, clean confirm이 과하게 눌린 결과인지 분리한다.

주요 owner:

- `backend/trading/chart_symbol_override_policy.py`
- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`

주요 관찰 항목:

- `nas_clean_confirm_probe`
- `middle_sr_anchor_guard`
- `range_upper_reversal_sell_nas_balanced`
- `breakout_retest_nas_balanced`

## 7. 공통 조정 축

R1에서 공통으로 보는 축은 아래 네 가지다.

### 7-1. Probe Promotion

- `entry_probe_plan_v1.ready_for_entry`
- `probe_plan_reason`
- scene-specific relief
- forecast / pair gap / support readiness

### 7-2. Confirm Release

- layer mode suppression
- energy soft block
- confirm-to-observe suppression 완화 여부

### 7-3. Hold Patience

- `hold_bias`
- `prefer_hold_through_green`
- symbol edge hold bias
- mid-noise hold boost

### 7-4. Opposite Edge Exit

- `opposite_edge_exit_boost`
- tight hold penalty
- fast exit pressure
- profile-specific reverse gap tuning

## 8. 관측 기준

R1 조정은 아래 산출물을 항상 같이 본다.

- [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)
- [runtime_status.detail.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.detail.json)
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)

중요한 점:

- 차트 체감만으로 판단하지 않는다.
- event family 분포와 runtime reason을 같이 본다.
- `blocked_by`, `action_none_reason`, `probe_scene_id`, `hold/exit reason`을 분리해서 본다.

## 9. 완료 기준

아래가 모두 만족되면 R1을 완료로 본다.

- `Stage E` calibration target 수가 감소한다.
- 최근 분포에서 `XAU/BTC/NAS`의 편향이 덜 극단적이다.
- 차트 체감과 runtime reason이 서로 어긋나지 않는다.
- `probe -> confirm -> hold -> opposite edge exit` 흐름이 실제 관측상 더 자연스럽다.

## 10. 다음 handoff

R1이 끝나면 다음 단계는 `R2 저장 / export / replay 정합성`이다.

전체 흐름은 아래와 같다.

```text
R0 정합성 최소셋
-> R1 Stage E 미세조정
-> R2 저장 / export / replay 정합성
-> R3 Semantic ML Step 3~7 refinement
-> R4 Acceptance / promotion-ready
```
