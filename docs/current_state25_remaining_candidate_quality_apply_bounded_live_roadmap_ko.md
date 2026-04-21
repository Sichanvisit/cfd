# State25 Remaining Main Roadmap

## 목적

이 문서는 지금 시점에서 `state25` 프로젝트의 남은 메인 작업만 다시 묶어 보여주는 통합판이다.

기존 문서들은 이미 많이 있다.
다만 현재는 문서가

- `AI3 retrain / compare / promote`
- `AI4 gate / rollback`
- `AI5 execution integration`
- `AI6 active candidate runtime / apply`

처럼 단계별로 잘게 나뉘어 있어서,
`그래서 지금 사람 손으로 뭘 먼저 밀어야 하느냐`를 한 번에 보기엔 조금 흩어져 있다.

이 문서는 그 흩어진 문서를

1. `후보 품질 개선`
2. `AI6 apply 개방`
3. `bounded live`

라는 현재 메인 흐름으로 다시 묶는다.

## 이미 있는 기준 문서

이미 작성된 문서는 아래와 같다.

- 상위 큰 그림:
  - [state25 auto-improvement execution roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_teacher_label_state25_auto_improvement_execution_roadmap_ko.md)
- AI3:
  - [state25 retrain / compare / promote design](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_retrain_compare_promote_design_ko.md)
  - [state25 retrain / compare / promote implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_retrain_compare_promote_implementation_roadmap_ko.md)
- AI4:
  - [state25 promotion gate / rollback design](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_promotion_gate_rollback_design_ko.md)
  - [state25 promotion gate / rollback implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_promotion_gate_rollback_implementation_roadmap_ko.md)
- AI5:
  - [state25 execution policy integration design](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_execution_policy_integration_design_ko.md)
  - [state25 execution policy integration implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_execution_policy_integration_implementation_roadmap_ko.md)
- AI6:
  - [state25 auto-promote / live actuator design](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_auto_promote_live_actuator_design_ko.md)
  - [state25 auto-promote / live actuator implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_auto_promote_live_actuator_implementation_roadmap_ko.md)
  - [state25 active candidate runtime consumption design](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_active_candidate_runtime_consumption_design_ko.md)
  - [state25 active candidate runtime consumption implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_active_candidate_runtime_consumption_implementation_roadmap_ko.md)
- readiness split:
  - [log-only vs canary/live readiness split](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_log_only_vs_canary_live_readiness_split_ko.md)
  - [log-only vs canary/live readiness split implementation roadmap](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_log_only_vs_canary_live_readiness_split_implementation_roadmap_ko.md)
- soft regression handling:
  - [offline soft-regression log-only policy](/C:/Users/bhs33/Desktop/project/cfd/docs/current_state25_offline_soft_regression_log_only_policy_ko.md)

즉 문서는 이미 있다.
지금 필요한 건 `남은 메인 작업만 다시 한 줄로 묶는 지도`다.

## 현재 실제 상태

지금 실제 상태를 한 줄로 줄이면 아래와 같다.

- `AI1 누적`은 이미 자동으로 돈다
- `AI3~AI6` 오프라인 재평가 루프도 이미 자동으로 돈다
- runtime은 새 `state25 candidate runtime surface`를 실제로 읽고 쓴다
- 다만 현재 후보는 아직 자주 `hold_offline / hold_regression` 쪽에 걸린다
- 그래서 `active_candidate_state.json`은 아직 비어 있거나 baseline fallback 상태다
- 즉 시스템이 멈춘 게 아니라 `후보 overlay를 아직 live에 얹을 근거가 부족한 상태`다

현재 해석:

- 시장을 보는 본체 엔진은 이미 계속 돈다
- `active_candidate_state`는 시장 state가 아니라 `candidate overlay control state`다
- 그래서 이 파일이 비어 있어도 진입/청산은 계속 된다
- 비어 있다는 건 `state25 overlay는 아직 비활성`이라는 뜻이다

## 지금부터의 메인 3축

### 1. Candidate 품질 개선

이게 현재 사람 손으로 밀 메인 1순위다.

지금 막히는 핵심 이유는 단순히 `Step9 seed shortfall`만이 아니다.
실제 후보가 자주 아래 상태로 떨어진다.

- `hold_no_material_gain`
- `hold_regression`
- `hold_offline`

즉 지금 질문은
`candidate loop가 도느냐`가 아니라
`왜 candidate가 baseline보다 자주 못 이기느냐`다.

여기서 봐야 할 것:

- 어떤 task가 regression blocker인지
  - pattern
  - group
  - economic_total
  - wait_quality
- regression이 hard인지 soft인지
- 특정 symbol / pattern에서만 밀리는지
- Step9 부족 때문인지, 순수 offline compare 문제인지

실무 목표:

- `hold_regression` 빈도를 줄인다
- 최소한 `log_only_review_ready`나 `promote_review_ready`가 반복 관찰되게 만든다

추천 작업:

1. `teacher_pattern_candidate_retrain_compare_promote.py` 결과를 누적해 blocker 빈도를 본다
2. 최근 후보들의 공통 regression task를 뽑는다
3. 그 task에 맞는 seed / feature / label / support 부족을 좁힌다
4. 다음 후보에서 `hold_regression -> soft regression -> review_ready`로 올라오는지 본다

추가 live watch:

- NAS `lower_rebound BUY` 경로는 forecast / probe / energy 완화 이후 현재 `add-on / pyramid` 최종 확인 단계까지 올라온 상태다
- `shadow_lower_rebound_probe_observe_nas_lower_breakdown_probe` reason variant도 pyramid 완화 대상에 포함되도록 이미 반영했다
- 다만 직전 live는 `market_closed_session`으로 끊겨 최종 확인이 보류됐다
- NAS 세션 재개 후에는 `entry_decisions.csv` 최신 row에서 `pyramid_not_in_drawdown` 해소 여부와 다음 blocker 변화를 먼저 확인한다

### 2. AI6 Apply 개방

이건 지금 코드상 준비는 끝났다.
다만 기본값이 꺼져 있다.

현재 상태:

- `STATE25_CANDIDATE_WATCH_APPLY_AI6=false`
- candidate watch는 15분마다 계속 평가만 한다
- 후보가 충분히 좋아져도 기본값이 false면 실제 state file write는 안 한다

이 단계의 의미:

- `좋은 후보`가 나왔을 때만
- `active_candidate_state.json`에 실제 promote / rollback apply를 쓴다
- runtime이 그 state를 읽고 threshold / size log-only overlay를 소비한다

개방 조건:

- 적어도 `log_only` 단계에서 열 만한 근거가 있어야 한다
- 최근 soft regression 허용 정책과 readiness split 기준을 통과해야 한다
- candidate가 `keep_current_baseline`이 아니라 `log_only로는 검토 가능` 수준까지 올라와야 한다

실무 목표:

- 무조건 켜는 것이 아니라
- `후보가 실제로 열릴 만한 시점`이 왔을 때 `false -> true`로 바꾼다

### 3. Bounded Live

이건 마지막 단계다.

순서는 항상 아래와 같다.

1. `disabled`
2. `log_only`
3. `canary`
4. `bounded live`

중요한 점:

- `log_only`는 비교 관찰 단계다
- `canary`는 아주 좁은 범위에서만 실제 반영하는 단계다
- `bounded live`는 완전 개방이 아니라 제한된 범위 live다

즉 이 단계는 `candidate overlay를 실제 돈 흐름에 연결하는 마지막 단계`다.

지금은 아직 여기까지 갈 타이밍이 아니다.
먼저 candidate가 꾸준히 살아남아야 한다.

## 실무 순서

지금부터 사람이 직접 밀 순서는 아래가 맞다.

1. `candidate 품질 개선`
2. `AI6 apply를 열 수 있는 후보가 나오는지 확인`
3. `AI6 apply 기본값 개방`
4. `log_only 관찰`
5. `canary`
6. `bounded live`

즉 지금 가장 중요한 건
`AI6를 바로 켜는 것`이 아니라
`켜도 되는 후보를 먼저 만들기`다.

## 지금 단계에서 보는 보고서

### 후보 품질 개선용

- `python scripts/teacher_pattern_candidate_retrain_compare_promote.py`
- `python scripts/teacher_pattern_promotion_gate_report.py`
- `python scripts/teacher_pattern_execution_policy_integration_report.py`
- [latest candidate run](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/latest_candidate_run.json)
- [latest gate report](/C:/Users/bhs33/Desktop/project/cfd/models/teacher_pattern_state25_candidates/latest_gate_report.json)

### watch / 자동 루프 상태용

- `python scripts/state25_candidate_watch.py --max-cycles 1`
- [state25 candidate watch latest md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/state25_candidate_watch_latest.md)
- [state25 candidate watch latest json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/teacher_pattern_state25/state25_candidate_watch_latest.json)

### live runtime 소비 확인용

- [runtime_status.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)
- [runtime_status.detail.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.detail.json)

## 단계별 완료 기준

### R1. Candidate 품질 개선 완료 기준

- `hold_regression`이 main default가 아니다
- `log_only_review_ready` 또는 `promote_review_ready`가 반복 관찰된다
- regression blocker가 한두 task로 좁혀져 있고, 이유를 설명할 수 있다

### R2. AI6 apply 개방 완료 기준

- `STATE25_CANDIDATE_WATCH_APPLY_AI6=true`를 켜도 이유를 설명할 수 있다
- watch report에서 `apply_ai6_requested`와 `applied_action`이 정상적으로 찍힌다
- runtime status에서 state25 candidate runtime surface가 정상적으로 소비된다

### R3. Bounded Live 착수 기준

- log-only candidate bind가 일정 기간 문제 없이 관찰된다
- canary로 올려도 될 symbol / stage 범위를 좁혀서 말할 수 있다
- rollback 기준이 이미 정의되어 있다

## 지금 이 문서를 어떻게 쓰면 되나

다음 턴부터는 아래처럼 쓰면 된다.

- `지금 메인 1순위 뭐냐`
  - 이 문서 기준으로 `candidate 품질 개선`
- `AI6 apply 지금 켜도 되냐`
  - 이 문서 기준으로 `좋은 후보가 반복 관찰될 때만`
- `bounded live 지금 가도 되냐`
  - 이 문서 기준으로 `아직 아님`, 먼저 `log_only` 안정화

## 결론

지금 남은 큰 공사는 더 이상 많지 않다.
이미 `누적`, `재학습`, `gate`, `integration`, `AI6 runtime surface`까지는 붙었다.

이제 남은 메인은 아래 세 줄이다.

1. `후보를 실제로 통과하게 만들기`
2. `그 후보를 log-only로 실제 열기`
3. `그다음 bounded live로 좁게 반영하기`

즉 지금부터는 `새 파이프라인 공사`보다
`후보 품질 -> apply 개방 -> bounded live`의 운영 단계라고 보면 된다.
