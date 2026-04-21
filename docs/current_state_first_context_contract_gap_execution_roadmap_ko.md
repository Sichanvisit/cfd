# State-First Context Contract Gap 실행 로드맵

## 목표

HTF / previous box / share를 detector가 직접 억지 계산하지 않게 하고,
먼저 runtime latest state contract에 올린 뒤 detector / notifier / propose가 공통으로 읽게 만든다.


## ST0. Current State Audit

목표:
- 지금 계산은 되는데 latest state에 안 실리는 필드를 확정

확인 대상:
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)
- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)
- [mt5_snapshot_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\mt5_snapshot_service.py)
- [runtime_status.detail.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.detail.json)

완료 기준:
- `already_computed_but_not_promoted`
- `not_computed_yet`
를 분리한 audit 표 확보


## ST1. HTF Cache / HTF State v1

목표:
- 1H / 4H / 1D context를 hot path 바깥에서 안정적으로 계산하고 cache한다

상태:
- 완료

상세:
- [current_st1_htf_cache_htf_state_v1_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st1_htf_cache_htf_state_v1_detailed_plan_ko.md)
- [current_st1_htf_cache_htf_state_v1_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st1_htf_cache_htf_state_v1_execution_roadmap_ko.md)

대상 파일:
- `backend/services/htf_trend_cache.py`
- [mt5_snapshot_service.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\mt5_snapshot_service.py)

계산 원칙:
- MT5 snapshot 수집 흐름에 얹어서 fetch
- symbol / timeframe별 cache
- freshness 메타 유지
- v1은 EMA 기반 direction + simple strength
- `trend_*_strength_score` raw 값도 같이 저장
- `trend_quality`는 schema 자리만 먼저 열고 계산은 v2

완료 기준:
- `1H / 4H / 1D`를 매 tick 재계산하지 않고 읽을 수 있음
- cache freshness 기준이 문서화됨


## ST2. Previous Box Calculator v1

목표:
- 직전 박스 후보를 upstream에서 계산하고 mode / confidence / consolidation 여부를 함께 만든다

상태:
- 완료

상세:
- [current_st2_previous_box_state_v1_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st2_previous_box_state_v1_detailed_plan_ko.md)
- [current_st2_previous_box_state_v1_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st2_previous_box_state_v1_execution_roadmap_ko.md)

대상 파일:
- `backend/services/previous_box_calculator.py`
- [context_classifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\context_classifier.py)

v1 필드:
- `previous_box_high`
- `previous_box_low`
- `previous_box_mid`
- `previous_box_mode`
- `previous_box_confidence`
- `previous_box_lifecycle`
- `previous_box_is_consolidation`
- `previous_box_relation`
- `previous_box_break_state`
- `distance_from_previous_box_high_pct`
- `distance_from_previous_box_low_pct`

계산 원칙:
- shifted range + swing hybrid
- `MECHANICAL`과 `STRUCTURAL`을 구분
- 실제 박스성이 약하면 `previous_box_is_consolidation = false`
- `previous_box_lifecycle`는 최소 rule부터 먼저 두고, 정교한 구조 lifecycle은 후반 도입
- 진짜 consolidation detector는 v2

완료 기준:
- detector가 previous box를 억지 계산하지 않고 읽을 수 있음
- weak box / strong box를 구분할 수 있음


## ST3. Context State Builder v1.2

목표:
- HTF / previous box / share를 raw + interpreted context state로 조립한다

상태:
- 완료

상세:
- [current_st3_context_state_builder_v12_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st3_context_state_builder_v12_detailed_plan_ko.md)
- [current_st3_context_state_builder_v12_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st3_context_state_builder_v12_execution_roadmap_ko.md)

대상 파일:
- `backend/services/context_state_builder.py`

출력 구조:
- raw context
  - `trend_*`, `previous_box_*`, `cluster_share_*`
- interpreted context
  - `htf_alignment_state`
  - `htf_alignment_detail`
  - `htf_against_severity`
  - `context_conflict_state`
  - `context_conflict_flags`
  - `context_conflict_intensity`
  - `context_conflict_score`
  - `context_conflict_label_ko`
  - `late_chase_risk_state`
  - `late_chase_reason`
  - `late_chase_confidence`
  - `late_chase_trigger_count`
- meta
  - `context_state_version`
  - `htf_context_version`
  - `previous_box_context_version`
  - `conflict_context_version`
  - `context_state_built_at`
  - per-field `updated_at`, `age_seconds`

완료 기준:
- detector / notifier / propose가 같은 context state 묶음을 읽을 수 있음
- raw와 interpreted 상태가 분리되어 downstream 해석이 중복되지 않음
- `context_conflict_state`의 primary 우선순위 규칙이 문서화됨
- `context_conflict_intensity`가 함께 제공됨


## ST4. Runtime Payload 합류

목표:
- context_state_builder 결과를 latest runtime state contract에 합류시킨다

상태:
- 완료

상세:
- [current_st4_runtime_payload_context_merge_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st4_runtime_payload_context_merge_detailed_plan_ko.md)
- [current_st4_runtime_payload_context_merge_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st4_runtime_payload_context_merge_execution_roadmap_ko.md)

대상 파일:
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

완료 기준:
- latest runtime row에서 HTF 필드가 직접 보임
- latest runtime row에서 previous box / context conflict / late chase 필드도 직접 보임
- `context_state_version`이 함께 보임


## ST5. 15M Trend State v1

목표:
- alignment 계산을 완성하기 위해 15M trend를 HTF와 같은 방식으로 state에 맞춘다

대상 파일:
- `backend/services/htf_trend_cache.py`
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

완료 기준:
- `trend_15m_direction`
- `trend_15m_strength`
- freshness 메타가 HTF와 같은 방식으로 보임


## ST6. Share State v1

목표:
- semantic cluster 쪽 share를 runtime/latest contract에서도 공통 필드로 읽을 수 있게 함

v1 필드:
- `cluster_share_global`
- `cluster_share_symbol`
- `cluster_share_symbol_band`
- `share_context_label_ko`

완료 기준:
- detector/propose가 share를 별도 fallback 없이 읽을 수 있음


## ST7. Detector Bridge

목표:
- 새 state 필드를 detector가 evidence로 읽게 연결

대상 파일:
- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)

완료 기준:
- `상위 추세 역행`
- `직전 박스 상단 위 유지`
- `맥락 충돌`
- `늦은 추격 경계`
- `상승 지속 누락`
같은 문장이 detector evidence에 붙음
- detector가 계산기라기보다 얇은 context bundle reader / bundler 역할로 유지됨


## ST8. Notifier Bridge

목표:
- DM에서 강한 mismatch일 때만 새 context 1줄 노출

대상 파일:
- [notifier.py](C:\Users\bhs33\Desktop\project\cfd\backend\integrations\notifier.py)

완료 기준:
- DM이 너무 길어지지 않으면서
- 큰 그림 경고가 전달됨
- `맥락: <HTF> | <직전박스> | <추격위험>` 형태의 1줄 템플릿 정착

?곹깭:
- ?꾨즺

?곸꽭:
- [current_st8_notifier_bridge_context_line_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st8_notifier_bridge_context_line_detailed_plan_ko.md)
- [current_st8_notifier_bridge_context_line_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st8_notifier_bridge_context_line_execution_roadmap_ko.md)

## ST9. Proposal / Hindsight Bridge

?곹깭:
- ?꾨즺

?怨멸쉭:
- [current_st9_proposal_hindsight_bridge_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st9_proposal_hindsight_bridge_detailed_plan_ko.md)
- [current_st9_proposal_hindsight_bridge_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_st9_proposal_hindsight_bridge_execution_roadmap_ko.md)

목표:
- 새 state-derived context가 propose와 hindsight review에도 이어지게 함

대상 파일:
- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)

완료 기준:
- review backlog에서 HTF / previous box / share 기반 패턴을 읽을 수 있음


## 추천 구현 순서

1. `ST0 current state audit`
2. `ST1 HTF cache / HTF state v1`
3. `ST2 previous box calculator v1`
4. `ST3 context_state_builder v1.2`
5. `ST4 runtime payload 합류`
6. `ST5 15M trend state v1`
7. `ST7 detector bridge (HTF only)`
8. `ST8 notifier bridge (HTF warning only)`
9. `ST7 detector bridge (previous box / conflict / late chase 추가)`
10. `ST6 share state v1`
11. `ST9 proposal / hindsight bridge`


## 우선순위 요약

- 1순위: `HTF`
- 2순위: `previous box`
- 3순위: `share`

즉 detector를 먼저 넓히는 게 아니라,
**HTF cache -> previous box calculator -> context_state_builder -> runtime payload** 순으로
state contract를 HTF-first로 넓히는 것이 현재 가장 안전하고 효과적인 순서다.


## v1.2 보강 포인트

- `context_conflict_state`는 단일 primary 값 + 우선순위 규칙으로 먼저 시작
- `context_conflict_flags`로 복합 conflict 해석 여지를 남긴다
- `context_conflict_intensity`로 약한 충돌과 강한 충돌을 분리
- `trend_*_strength_score`는 raw tuning용으로 같이 저장한다
- `trend_quality`는 schema를 먼저 열고 계산은 후반 도입
- `previous_box_lifecycle`는 최소 rule부터 먼저 둔다
- `late_chase_confidence`, `late_chase_trigger_count`를 함께 남긴다
- component별 context version을 hindsight meta로 유지한다
- `context_state_version`은 hindsight 비교를 위한 필수 meta로 유지
