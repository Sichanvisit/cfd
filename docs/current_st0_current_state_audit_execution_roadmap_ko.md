# ST0 Current State Audit 실행 로드맵

## 목표

현재 runtime latest state contract의 빈칸을 field 단위로 분해하고,
다음 구현 단계(ST1 / ST2 / ST3 / ST6)를 실제 근거 위에서 시작할 수 있게 만든다.


## S0-1. Field Catalog Freeze

목표:
- ST0가 검사할 target field 목록을 고정

포함 group:
- `HTF`
- `PREVIOUS_BOX`
- `CONFLICT`
- `SHARE`
- `META`

완료 기준:
- field catalog에 `context_group / state_layer / target_field / source_refs / recommended_next_action`가 있다


## S0-2. Runtime Sample Inspection

목표:
- `runtime_status.detail.json`의 `latest_signal_by_symbol`를 기준으로
  direct field 존재 여부를 본다

완료 기준:
- field별 `runtime_direct_present_count`
- `runtime_direct_declared_count`
- symbol 예시가 계산된다


## S0-3. Source / Proxy Scan

목표:
- upstream source token과 runtime related proxy를 같이 본다

입력:
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)
- [mt5_snapshot_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\mt5_snapshot_service.py)
- [semantic_baseline_no_action_cluster_candidate.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\semantic_baseline_no_action_cluster_candidate.py)
- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)

완료 기준:
- field별 `matched_source_tokens`
- `matched_runtime_proxy_fields`
- proxy evidence level이 계산된다


## S0-4. Gap Classification

목표:
- field를 4단계로 분류

분류:
- `DIRECT_PRESENT`
- `DECLARED_BUT_EMPTY`
- `ALREADY_COMPUTED_BUT_NOT_PROMOTED`
- `NOT_COMPUTED_YET`

완료 기준:
- field_rows에 `audit_state`가 붙는다
- group summary가 계산된다


## S0-5. Artifact Write

목표:
- JSON / Markdown artifact를 남긴다

출력:
- [state_first_context_contract_gap_audit_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\state_first_context_contract_gap_audit_latest.json)
- [state_first_context_contract_gap_audit_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\shadow_auto\state_first_context_contract_gap_audit_latest.md)

완료 기준:
- summary에 `recommended_next_step`이 있다
- `already_computed_but_not_promoted`와 `not_computed_yet`를 분리해 볼 수 있다


## 구현 순서

1. `state_first_context_contract_gap_audit.py`
2. `test_state_first_context_contract_gap_audit.py`
3. artifact generation
4. main roadmap와 연결 확인


## ST0가 끝난 뒤 바로 이어질 것

- `recommended_next_step = start_ST1_htf_cache_first`
  - HTF 먼저
- 그 다음
  - `ST2 previous_box_calculator`
  - `ST3 context_state_builder`
  - `ST6 share state`

즉 ST0는 단독 기능이 아니라,
**state-first 구현 순서를 실제 evidence로 고정하는 기준 단계**다.
