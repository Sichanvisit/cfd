# R1 Stage E Micro Calibration Implementation Checklist

## 1. 목적

이 문서는 [refinement_r1_stagee_micro_calibration_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_spec_ko.md)을 실제 구현 순서로 내린 체크리스트다.

R1의 목적은 foundation을 다시 건드리지 않고, 이미 고정된 semantic / chart flow / execution contract 위에서 symbol별 temperament와 execution bias를 미세조정하는 것이다.

## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- current baseline snapshot 고정
- XAU / BTC / NAS의 개별 조정축 구현
- hold / exit 공통축 정리
- distribution / rollout 재관측

### 하지 않을 것

- foundation 의미 변경
- chart flow vocabulary 변경
- semantic target/split 재설계
- promotion gate 확장

## 3. 입력 기준

- 마스터 계획: [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- R1 spec: [refinement_r1_stagee_micro_calibration_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r1_stagee_micro_calibration_spec_ko.md)
- 분포 리포트: [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- rollout 상태: [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)

## 4. 구현 순서

### Step 1. Baseline Snapshot 고정

목표:

- 현재 `BTCUSD / NAS100 / XAUUSD`의 최근 분포를 문서 기준선으로 고정한다.
- `Stage E = advance`와 calibration target 해제 상태를 문서와 리포트 기준으로 일치시킨다.

현재 상태:

- 완료
- `Stage E = advance`
- calibration target = 없음
- NAS second calibration 이후 target 해제 반영 완료
- XAU / BTC second calibration 이후 target 해제 반영 완료

### Step 2. XAU Upper Sell Probe 조정

목표:

- `upper sell probe`가 과하게 늦거나 soft block에 과하게 죽지 않게 조정한다.

대상:

- `backend/services/symbol_temperament.py`
- `backend/services/entry_service.py`
- 필요 시 `backend/services/wait_engine.py`
- 필요 시 `backend/trading/chart_symbol_override_policy.py`

현재 상태:

- 2차 적용 완료
- structural relief 완화
- energy relief 완화
- `bb_state = UNKNOWN` 허용
- balanced live-like upper reject row 기준 probe promotion / energy release 보정

후속 관찰 항목:

- `xau_upper_sell_probe`
- `forecast_guard`
- `probe_not_promoted`
- `confirm_suppressed`

### Step 3. BTC Lower Hold / Duplicate Suppression 조정

목표:

- lower buy 중복 진입을 더 억제한다.
- lower buy hold patience를 높인다.
- middle noise에서 과도한 조기 exit를 줄인다.

대상:

- `backend/services/entry_engines.py`
- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`
- 필요 시 `backend/services/entry_service.py`

완료 기준:

- `btc_duplicate_edge_suppression` trace가 더 설명 가능해진다.
- `btc_lower_hold_bias`, `btc_lower_mid_noise_hold_bias`가 의도한 케이스에서 더 자연스럽게 작동한다.
- `range_lower_reversal_buy_btc_balanced`가 lower reversal hold 의도를 더 잘 반영한다.

현재 상태:

- 1차 + follow-up 적용 완료
- duplicate suppression은 더 강해졌고, strong repeat quality만 제한적으로 relief를 허용한다.
- lower hold bias와 mid-noise hold bias가 더 오래 유지되도록 조정됐다.
- exit profile은 기본 patience를 늘리되 opposite belief / edge rotation에서는 다시 빠르게 보수화되도록 맞췄다.
- 실거래 BTC auto lower reversal buy 리뷰에서 `support_hold_profile`가 `range_lower_reversal_buy_btc_balanced`보다 먼저 적용되어 hold bias가 비활성화되던 케이스를 확인했고, `BTCUSD + range_lower_reversal_buy`에 한해 setup-specific balanced recovery가 우선되도록 좁게 수정했다.

### Step 4. NAS Clean Confirm Balance 조정

목표:

- `clean confirm / upper sell / neutral wait` 밸런스를 맞춘다.
- `middle_sr_anchor_guard`에 눌린 directional wait와 true neutral wait를 더 구분 가능하게 만든다.

대상:

- `backend/trading/chart_symbol_override_policy.py`
- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`

완료 기준:

- `nas_clean_confirm_probe` 계열이 과도하게 눌리는 비중이 줄어든다.
- `SELL_WAIT` 일변도에서 조금 더 균형 있는 분포로 이동한다.

현재 상태:

- 2차 재관측 기준 반영 완료
- `clean_confirm` override의 `floor_mult`, `advantage_mult`, `support_tolerance`를 완화했다.
- `middle_sr_anchor_guard` relief가 추가됐고, latest distribution 기준으로 NAS는 Stage E calibration target에서 빠졌다.
- latest rollout 기준으로 NAS는 `Stage E = advance` 윈도우 안에 포함된다.

### Step 5. Hold / Opposite Edge Exit 공통축 정리

목표:

- 좋은 entry가 middle noise만으로 바로 끊기지 않게 한다.
- 반대로 adverse risk 상태에서는 hold bias가 과하지 않게 한다.

대상:

- `backend/services/wait_engine.py`
- `backend/services/exit_profile_router.py`

완료 기준:

- `hold_bias`, `prefer_hold_through_green`, `opposite_edge_exit_boost`의 상호작용이 더 자연스럽다.

현재 상태:

- 2차 반영 완료
- BTC exit routing에서 patience 상향 후, `opposite belief rising`과 `edge rotation reverse`를 더 보수적으로 되돌리는 균형 조정을 넣었다.
- Step 6 재관측 기준으로 immediate calibration target은 모두 해제됐다.

### Step 6. Distribution / Rollout 재관측

목표:

- 조정 전후 분포를 다시 비교한다.

확인 항목:

- `Stage E`
- presence ratio
- zone별 event
- `blocked_by / action_none_reason` 변화
- probe scene 변화

완료 기준:

- calibration target이 사라지거나, 남더라도 이유가 분명하게 설명 가능하다.

현재 상태:

- 2차 재관측 완료
- latest rollout 기준 `Stage E = advance`, calibration target = 없음
- BTC는 `BUY_PROBE 1 / SELL_WAIT 5 / WAIT 10`, NAS는 `BUY_WAIT 1 / SELL_WAIT 1 / SELL_PROBE 2 / WAIT 12`, XAU는 `BUY_WAIT 1 / SELL_PROBE 1 / SELL_READY 3 / WAIT 11`로 latest window가 갱신됐다.
- `manage_cfd.bat verify` 기준 `/health`, `/trades/summary`, `/trades/closed_recent` 모두 정상 응답했다.

### Step 7. 테스트와 회귀 확인

권장 테스트:

- `pytest tests/unit/test_entry_engines.py`
- `pytest tests/unit/test_wait_engine.py`
- `pytest tests/unit/test_exit_profile_router.py`
- `pytest tests/unit/test_entry_service_guards.py`
- `pytest tests/unit/test_chart_flow_distribution.py`
- `pytest tests/unit/test_chart_flow_rollout_status.py`

상황별 추가:

- `pytest tests/unit/test_chart_painter.py`
- `pytest tests/unit/test_entry_try_open_entry_probe.py`

완료 기준:

- R1 조정이 기존 contract를 깨지 않는다.

현재 상태:

- 완료
- `pytest tests/unit/test_entry_engines.py tests/unit/test_wait_engine.py tests/unit/test_exit_profile_router.py tests/unit/test_observe_confirm_router_v2.py`
  - `122 passed`
- `pytest tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py tests/unit/test_entry_service_guards.py -k "xau_upper_sell_probe or nas_clean_confirm_probe or distribution or rollout or btc_lower_hold_bias or btc_duplicate_edge_suppression"`
  - `16 passed`
- `pytest tests/unit/test_symbol_temperament.py tests/unit/test_entry_service_guards.py -k "xau_upper_sell_probe or xau_upper_sell or stagee_recalibration"`
  - `8 passed`
- `pytest tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_check_semantic_canary_rollout.py tests/unit/test_storage_compaction.py tests/unit/test_wait_engine.py tests/unit/test_exit_profile_router.py`
  - `87 passed`
- `pytest tests/unit/test_observe_confirm_router_v2.py tests/unit/test_chart_flow_distribution.py tests/unit/test_chart_flow_rollout_status.py tests/unit/test_chart_painter.py`
  - `107 passed`
- `pytest tests/unit/test_entry_service_guards.py -k "xau_upper_sell_probe or nas_clean_confirm_probe or btc_duplicate_edge_suppression or btc_lower_hold_bias"`
  - `5 passed`
- `pytest tests/unit/test_exit_profile_router.py -k "btc_range_lower_reversal_buy"`
  - `4 passed`
- `pytest tests/unit/test_wait_engine.py -k "btc_lower_hold_bias or keeps_btc_lower_reversal_buy_active_after_partial_giveback or tight_protect_positive_profit"`
  - `2 passed`

### Step 8. 문서 동기화

목표:

- spec과 checklist를 현재 구현 상태에 맞춘다.
- R1이 어디까지 끝났고 어디가 남았는지 문서만 읽어도 보이게 만든다.

완료 기준:

- R1 문서만 읽어도 현재 구현 상태와 다음 남은 단계가 해석된다.

## 5. Done Definition

아래가 모두 만족되면 R1 구현 단계를 완료로 본다.

- XAU / BTC / NAS별 조정축이 코드에 반영됐다.
- 조정 전후 분포 비교가 가능하다.
- `Stage E`가 `advance`로 닫히고 calibration target이 최신 윈도우에서 사라진다.
- 차트 체감과 runtime reason 설명이 서로 어긋나지 않는다.

## 6. 다음 단계

R1이 끝나면 다음은 `R2 저장 / export / replay 정합성`이다.
