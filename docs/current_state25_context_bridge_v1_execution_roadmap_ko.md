# State25 Context Bridge v1.2 구현 로드맵

## 목표

state-first context를 state25의 `weight / threshold / size` 손잡이에 bounded하게 번역하는 bridge를 만들고,
먼저 `log_only`로 검증한 뒤 좁게 rollout할 수 있는 준비를 갖춘다.


## BC0. Contract Freeze

목표:
- bridge를 새 decision core가 아니라 bounded translator로 고정

결정:
- `weight / threshold / size`만 조정
- hard veto 금지
- share는 booster만
- `interpreted 80 / raw 20`
- v1 threshold는 `HARDEN` only
- `LATE_CHASE_RISK`는 threshold / size 우선
- decision counterfactual 우선, outcome counterfactual은 후반

산출물:
- [current_state25_context_bridge_v1_detailed_plan_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\current_state25_context_bridge_v1_detailed_plan_ko.md)


## BC1. Bridge Skeleton

목표:
- 공용 bridge 서비스 파일 생성

대상 파일:
- `backend/services/state25_context_bridge.py`

구현 항목:
- intake
- freshness / gating
- component activation
- component activation reasons
- translator hooks
- cap / decay / stacking scaffolding
- overlap guard scaffolding
- trace builder
- `build_state25_candidate_context_bridge_v1(...)`

완료 기준:
- 빈 context에서도 안정적으로 contract 반환
- trace skeleton 존재
- failure / guard mode 기본 틀 존재


## BC2. Weight-Only Translator v1

목표:
- 가장 안전한 첫 연결로 `weight`만 실제 번역

대상 파일:
- `backend/services/state25_context_bridge.py`
- [learning_parameter_registry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\learning_parameter_registry.py)

입력:
- `htf_alignment_state`
- `previous_box_break_state`
- `context_conflict_state`
- raw strength / freshness 보조값

구현 원칙:
- context당 핵심 weight 2개까지만 조정
- requested / effective / suppressed 분리
- `context_bias_side`, `context_bias_side_confidence`, `context_bias_side_source_keys` 기록
- late chase는 v1 weight 주 입력에서 제외

완료 기준:
- actual state25 weight key 기준으로 requested/effective가 나옴
- freshness / cap / suppression이 trace로 보임


## BC3. Runtime Trace Export

목표:
- bridge 결과를 runtime/export row에서 보이게 함

대상 파일:
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [trading_application.py](C:\Users\bhs33\Desktop\project\cfd\backend\app\trading_application.py)

구현 항목:
- `state25_candidate_context_bridge_v1`
- flat trace fields
- detail nested payload
- `trace_reason_codes`
- explicit linkage keys
  - `bridge_decision_id`
  - `hindsight_link_key`
  - `proposal_link_key`
- decision counterfactual 자리 확보
- outcome counterfactual은 schema 자리만 확보
- `override_scope`, `override_scope_detail`

완료 기준:
- runtime row에서 bridge 결과 확인 가능
- entry trace에서 knob별 조정과 suppression 확인 가능


## BC4. Weight-Only Log-Only Review Lane

목표:
- detector / propose와 연결되는 bounded review lane 생성

대상 파일:
- [improvement_log_only_detector.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\improvement_log_only_detector.py)
- [trade_feedback_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\trade_feedback_runtime.py)
- [state25_weight_patch_review.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\state25_weight_patch_review.py)

구현 항목:
- bridge가 제안한 weight 조정 후보를 review packet으로 올림
- context / freshness / suppression / failure / guard mode를 evidence snapshot에 포함

완료 기준:
- `/propose`에서 bridge 기반 state25 weight review 후보 확인 가능


## BC5. Weight-Only Bounded Live

목표:
- 첫 실제 bounded live는 weight-only로 시작

원칙:
- 아주 작은 cap
- review 가능한 trace 유지
- rollback 단순성 유지

관찰 지표:
- reversal precision
- continuation false positive
- skip 증가율
- PnL 개선 유무

rollback trigger 예:
- reversal precision 급락
- continuation false positive 증가
- late chase 개선 없음
- skip 증가만 있고 PnL 개선 없음

완료 기준:
- log-only와 bounded live 비교가 가능
- weight-only가 행동 품질을 망치지 않는지 관찰 가능


## BC6. Threshold Contract Patch

목표:
- threshold를 signed contract로 정리

대상 파일:
- [teacher_pattern_active_candidate_runtime.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_active_candidate_runtime.py)
- [teacher_pattern_execution_policy_log_only_binding.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\teacher_pattern_execution_policy_log_only_binding.py)

도입 항목:
- `state25_threshold_log_only_delta_points`
- `threshold_delta_direction`
- `threshold_delta_reason_keys`
- stage별 threshold cap 자리

완료 기준:
- schema는 완화/보수화 둘 다 표현 가능
- v1 활성 모드는 `HARDEN` only
- 기존 abs-only 계약과의 호환 규칙 명시


## BC7. Threshold-Only Log-Only

목표:
- threshold translator를 log-only로 먼저 검증

대상 파일:
- `backend/services/state25_context_bridge.py`
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

구현 항목:
- `AGAINST_HTF`
- `AGAINST_PREV_BOX_AND_HTF`
- `late_chase_risk`
기반 threshold delta 산출
- `entry_stage` multiplier log-only trace
- stage별 cap trace
- requested / effective / suppressed / decision counterfactual 기록

완료 기준:
- live 값과 candidate threshold 값 차이가 trace로 보임
- bridge가 실제 판단을 바꾸는지 decision counterfactual로 볼 수 있음


## BC8. Weight + Threshold Joint Log-Only

목표:
- weight와 threshold가 동시에 붙을 때 double counting이 없는지 검증

대상 파일:
- `backend/services/state25_context_bridge.py`
- 관련 audit 문서/서비스

구현 항목:
- overlap guard
- `overlap_class`
- stacking limit
- cap 적용 로그
- `trace_reason_codes`

완료 기준:
- 같은 불편함을 두 번 세지 않음
- trace에서 왜 threshold/weight가 동시에 조정됐는지 설명 가능


## BC9. Threshold Bounded Live

목표:
- threshold를 좁게 bounded live로 올림

전제:
- signed threshold contract 정리 완료
- log-only에서 decision counterfactual 성능 확인 완료

완료 기준:
- threshold 보정이 실제 판단을 바꾼 케이스만 따로 평가 가능


## BC10. Size Translator v1

목표:
- 가장 마지막으로 size 보수화 번역 추가

대상 파일:
- `backend/services/state25_context_bridge.py`
- [entry_try_open_entry.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

구현 항목:
- `late_chase_risk`
- `context_conflict_intensity`
- `previous_box_confidence`
기반 size 축소 후보
- `size_floor_protected`
- `size_floor_reason`
- `size_adjustment_state`

완료 기준:
- size는 보수화 방향으로만 먼저 작동
- floor 보호가 trace로 보임


## BC11. Size Log-Only / Bounded Live

목표:
- size를 마지막에 log-only 후 bounded live로 올림

원칙:
- size는 숨어 있는 veto처럼 동작하면 안 됨
- floor guard와 suppression trace가 반드시 보여야 함

완료 기준:
- size가 실제로 얼마나 행동 강도를 줄였는지 평가 가능


## BC12. Audit / Trace Dashboard

목표:
- bridge가 실제로 무엇을 했는지 운영 관점에서 볼 수 있는 audit 추가

대상 파일:
- `backend/services/state25_context_bridge_audit.py`
- `tests/unit/test_state25_context_bridge_audit.py`

최소 지표:
- bridge triggered row count
- freshness skip count
- component activation distribution
- component activation reasons distribution
- weight-only rows
- threshold-only rows
- size-only rows
- overlap-guard rows
- cap-applied rows
- suppression reason distribution
- failure mode distribution
- guard mode distribution
- `bridge_changed_decision = true` 비율
- outcome counterfactual은 후반 audit에서 추가


## BC13. 추천 rollout 순서

1. `weight-only log_only`
2. `weight-only bounded_live`
3. `threshold-only log_only`
4. `weight + threshold log_only`
5. `threshold bounded_live`
6. `size log_only`
7. `size bounded_live`

원칙:
- 첫 실제 live는 weight-only
- threshold는 signed contract 먼저
- size는 마지막
- rollback trigger를 먼저 정의하고 live를 연다


## 구현 우선순위 요약

1. `BC1 Bridge Skeleton`
2. `BC2 Weight-Only Translator`
3. `BC3 Runtime Trace Export`
4. `BC4 Weight-Only Log-Only Review Lane`
5. `BC5 Weight-Only Bounded Live`
6. `BC6 Threshold Contract Patch`
7. `BC7 Threshold-Only Log-Only`
8. `BC8 Weight + Threshold Joint Log-Only`
9. `BC9 Threshold Bounded Live`
10. `BC10 Size Translator`
11. `BC11 Size Log-Only / Bounded Live`
12. `BC12 Audit / Trace Dashboard`


## 현재 가장 자연스러운 다음 단계

지금 당장 구현으로 들어갈 첫 시작점은 아래다.

1. `BC1 state25_context_bridge.py skeleton`
2. `BC2 weight-only translator v1`
3. `BC3 runtime trace export`

즉 **weight부터 시작하는 bridge 골격 구현**이 첫 실제 코드 단계다.
