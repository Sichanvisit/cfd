# BC6 State25 Threshold Log-Only Translator 구현 로드맵
## 목표

state25 context bridge에 threshold harden log-only translator를 추가하고, runtime trace와 decision counterfactual까지 안정적으로 노출한다.

## BC6-1. Translator Contract 정리

대상 파일:

- `backend/services/state25_context_bridge.py`

작업:

- threshold requested/effective/suppressed contract 확장
- `threshold_delta_direction`
- `threshold_delta_reason_keys`
- `threshold_stage_multiplier`
- `threshold_stage_cap_points`
- `threshold_source_field`

완료 기준:

- threshold translator가 weight와 분리된 독립 contract를 가진다.

## BC6-2. HARDEN Only Mapping 구현

대상 파일:

- `backend/services/state25_context_bridge.py`

작업:

- `AGAINST_HTF`
- `AGAINST_PREV_BOX_AND_HTF`
- `late_chase_risk_state = HIGH`

를 threshold harden 요청으로 번역

원칙:

- `HARDEN only`
- late chase는 v1에서 threshold/size 우선
- share는 booster만

완료 기준:

- threshold requested 값이 context에 따라 생성된다.

## BC6-3. Stage Multiplier / Cap / Guard

대상 파일:

- `backend/services/state25_context_bridge.py`

작업:

- aggressive / balanced / conservative multiplier
- stage별 cap
- overlap guard / stale suppression / cap hit trace

완료 기준:

- threshold effective 값이 freshness와 cap을 거친 뒤 계산된다.

## BC6-4. Decision Counterfactual

대상 파일:

- `backend/services/state25_context_bridge.py`

작업:

- `without_bridge_decision`
- `with_bridge_decision`
- `bridge_changed_decision`
- score/threshold reference export

완료 기준:

- bridge threshold가 실제 판단을 바꾸는지 log-only로 볼 수 있다.

## BC6-5. Runtime Export 검증

대상 파일:

- `backend/app/trading_application.py`
- `backend/services/storage_compaction.py`

작업:

- threshold flat fields가 compact/hot/runtime row에 유지되는지 검증

완료 기준:

- runtime/detail/slim/hot payload 어디서든 BC6 threshold trace를 읽을 수 있다.

## BC6-6. 테스트 보강

대상 파일:

- `tests/unit/test_state25_context_bridge.py`
- `tests/unit/test_trading_application_runtime_status.py`
- `tests/unit/test_storage_compaction.py`
- `tests/unit/test_state25_weight_patch_review.py`

작업:

- BC6 stage 기대값 갱신
- threshold requested/effective flat field 검증
- decision counterfactual 검증

완료 기준:

- BC6 관련 회귀 테스트가 모두 통과한다.

## BC6-7. 운영 설명 반영

대상 파일:

- `docs/current_detect_feedback_propose_operator_explainer_ko.md`

작업:

- `/detect -> /propose`에서 무엇이 보이는지 정리
- BC6 threshold translator는 현재 runtime/log-only 중심임을 명시

완료 기준:

- 운영자가 `/detect`, `/propose`, BC6 노출 위치를 헷갈리지 않는다.
