# BC7 State25 Threshold Review Lane 상세 계획

## 목적

BC6에서 만든 `state25 context bridge threshold log-only translator`를 detector와 `/propose` review backlog까지 연결한다.

이번 단계의 목표는 threshold를 바로 live apply 하는 것이 아니라, 아래 흐름을 안정적으로 보이게 만드는 것이다.

- `runtime row`
- `threshold review preview`
- `/detect`
- `/propose`

즉 BC7은 새 threshold 규칙을 적용하는 단계가 아니라, **threshold harden review 후보를 운영 루프에 surface하는 단계**다.

## 왜 필요한가

BC6만으로도 runtime trace와 decision counterfactual은 쌓이지만, 운영자는 체크방에서 그 후보를 바로 읽기 어렵다.

그래서 BC7에서는:

- detector가 `state25 context bridge threshold review 후보`를 surface하고
- `/propose`가 그 후보를 backlog 후보로 요약해서 보여주고
- 이후 hindsight / proposal review에서 threshold 보정 가치가 있었는지 비교할 수 있게 만든다

## 입력

- `state25_candidate_context_bridge_v1`
- `threshold_adjustment_requested`
- `threshold_adjustment_effective`
- `threshold_adjustment_suppressed`
- `decision_counterfactual`
- `context_bundle_summary_ko`

## 출력

### `/detect`

`candle/weight detector` 아래에 다음 유형이 뜰 수 있다.

- `NAS100 state25 context bridge threshold review 후보`

핵심 evidence:

- requested / effective threshold points
- reason keys
- decision counterfactual
- guard / failure modes
- context bundle summary

### `/propose`

`state25 context bridge threshold review 후보:` 섹션이 뜰 수 있다.

핵심 내용:

- requested / effective points
- context summary
- reason keys
- decision before/after
- guard / failure
- review backlog 추천 문장

## 구현 범위

- `backend/services/state25_threshold_patch_review.py`
  - threshold preview packet builder
- `backend/services/improvement_log_only_detector.py`
  - threshold review detector row surface
- `backend/services/trade_feedback_runtime.py`
  - `/propose` threshold review candidate 수집 및 report/snapshot 연결
- `backend/services/learning_parameter_registry.py`
  - threshold registry key 점검

## 운영 원칙

- threshold는 여전히 `log_only`
- detector/propose surface는 review 목적
- live apply 없음
- `decision counterfactual`까지만 우선 강하게 본다
- `outcome counterfactual`은 hindsight 축에서 후속 검토

## 완료 기준

- `/detect`에서 threshold review 후보가 surface 가능
- `/propose`에서 threshold review 후보 count/section/snapshot 확인 가능
- `state25_context_bridge_threshold_review_count`가 proposal payload에 남음
- 관련 테스트가 통과함
