# BC7 State25 Threshold Review Lane 구현 로드맵

## BC7-1. Threshold Preview Builder 확인

대상 파일:

- `backend/services/state25_threshold_patch_review.py`

작업:

- requested/effective threshold points 읽기
- reason keys / counterfactual / guard / failure trace 포함
- stale nested bridge면 runtime row에서 rebuild

완료 기준:

- threshold preview packet이 안정적으로 생성된다.

## BC7-2. Detector Surface

대상 파일:

- `backend/services/improvement_log_only_detector.py`

작업:

- threshold preview가 있으면 detector row 생성
- `state25 context bridge threshold review 후보` summary 부여
- `threshold_patch_preview` nested payload 부착

완료 기준:

- candle/weight detector에서 threshold review row surface 가능

## BC7-3. Proposal Snapshot 연결

대상 파일:

- `backend/services/trade_feedback_runtime.py`

작업:

- threshold review candidate collect
- report line 추가
- summary / why_now / recommended_action 연결
- evidence snapshot count / registry keys 추가
- return payload count / candidate list 추가

완료 기준:

- `/propose` payload가 threshold review 후보를 count와 섹션으로 보여준다.

## BC7-4. 운영 설명 문서 갱신

대상 파일:

- `docs/current_detect_feedback_propose_operator_explainer_ko.md`

작업:

- `/detect -> /propose`에서 threshold review 후보가 어떻게 보이는지 반영
- weight review와 threshold review의 차이를 짧게 정리

완료 기준:

- 운영자가 threshold review 후보의 위치를 문서에서 바로 찾을 수 있다.

## BC7-5. 테스트

대상 파일:

- `tests/unit/test_state25_threshold_patch_review.py`
- `tests/unit/test_improvement_log_only_detector_bc7.py`
- `tests/unit/test_trade_feedback_runtime_bc7.py`
- `tests/unit/test_learning_parameter_registry.py`

완료 기준:

- threshold review lane 경로가 회귀 테스트로 고정된다.
