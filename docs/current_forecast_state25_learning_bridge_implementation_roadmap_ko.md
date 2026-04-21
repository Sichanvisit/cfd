# Forecast-State25 Learning Bridge Implementation Roadmap

## FSB0 Freeze Checklist

- direct-use field는 `state25_runtime_hint_v1`, `forecast_runtime_summary_v1`, `entry_wait_exit_bridge_v1`로 한정한다.
- closed-history final label과 future outcome label은 replay-only로 고정한다.
- runtime bridge는 `log_only / dual-write`로만 시작하고 live policy를 즉시 바꾸지 않는다.

작성일: 2026-04-03 (KST)

## 1. 목적

이 문서는 [forecast-state25 learning bridge 설계](/C:/Users/bhs33/Desktop/project/cfd/docs/current_forecast_state25_learning_bridge_design_ko.md)를 실제 코드와 리포트로 옮기기 위한 구현 로드맵이다.

핵심 순서는 아래 한 줄로 요약된다.

`runtime bridge -> replay/outcome bridge -> seed enrichment -> baseline auxiliary -> candidate compare -> log_only live overlay`

## 2. 구현 원칙

1. 처음부터 live policy를 바꾸지 않는다.
2. 모든 단계는 `dual-write / log-only / replay-first`로 시작한다.
3. future leakage가 생기지 않도록 runtime hint와 outcome label을 분리한다.
4. 기존 forecast owner와 state25 owner는 유지하고 bridge만 추가한다.

## 3. 단계별 로드맵

### FSB0. Scope Freeze

목표:

- bridge 범위를 확정하고 역할 충돌을 막는다.

해야 할 일:

- `state25`는 scene owner로 유지
- `forecast`는 branch owner로 유지
- `wait_quality / economic_target`은 outcome owner로 유지
- runtime direct-use field와 learning-only field를 명시

출력:

- bridge contract field list
- no-leakage field boundary

완료 기준:

- runtime에서 쓸 field와 replay-only field가 분리 문장으로 고정됨

### FSB1. Runtime Bridge Metadata

목표:

- 현재 runtime row와 entry decision row에 `forecast_state25_runtime_bridge_v1`를 기록한다.

대상 파일:

- [context_classifier.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/context_classifier.py)
- [trading_application_runner.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application_runner.py)
- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)

구현 항목:

1. `state25_runtime_hint_v1` builder 추가
2. `forecast_runtime_summary_v1` builder 추가
3. `entry_wait_exit_bridge_v1` builder 추가
4. runtime status / detail / entry decision payload에 dual-write

초기 모드:

- `log_only`
- 판단 변경 없음
- 기록만 추가

출력:

- `runtime_status.json`
- `runtime_status.detail.json`
- `entry_decisions.csv`

완료 기준:

- 최신 runtime row에서 bridge field가 보임
- 기존 진입/대기/청산 동작은 그대로임

### FSB2. Replay / Outcome Bridge

목표:

- runtime bridge와 실제 future outcome을 묶는 replay report를 만든다.

대상 파일:

- [outcome_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/engine/offline/outcome_labeler.py)
- [entry_wait_quality_replay_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_wait_quality_replay_bridge.py)
- 새 파일 권장
  - `backend/services/forecast_state25_outcome_bridge.py`
  - `scripts/forecast_state25_outcome_bridge_report.py`

구현 항목:

1. runtime row에서 bridge snapshot 회수
2. transition / management outcome label 연결
3. wait_quality / economic_target 연결
4. `forecast_state25_outcome_bridge_v1` report 작성

출력:

- json report
- md summary report

완료 기준:

- 특정 scene family별로 어떤 forecast가 나왔는지와 실제 결과가 어땠는지를 함께 읽을 수 있음

### FSB3. Closed-History Seed Enrichment

목표:

- replay/outcome bridge 결과를 closed history와 experiment seed에 붙인다.

대상 파일:

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- [teacher_pattern_experiment_seed.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_experiment_seed.py)
- 새 파일 권장
  - `backend/services/forecast_state25_seed_enrichment.py`
  - `scripts/backfill_forecast_state25_learning_seed.py`

권장 column:

- `forecast_state25_scene_family`
- `forecast_state25_group_hint`
- `forecast_confirm_side`
- `forecast_decision_hint`
- `forecast_wait_confirm_gap`
- `forecast_hold_exit_gap`
- `forecast_same_side_flip_gap`
- `forecast_belief_barrier_tension_gap`
- `forecast_transition_outcome_status`
- `forecast_management_outcome_status`

완료 기준:

- `trade_closed_history.csv`에 enrichment 컬럼이 생김
- seed report에서 coverage가 보임

### FSB4. Baseline Auxiliary Task

목표:

- forecast-state25 bridge를 pilot baseline과 candidate 학습에 auxiliary task로 연결한다.

대상 파일:

- [teacher_pattern_pilot_baseline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_pilot_baseline.py)
- [teacher_pattern_pilot_baseline_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_pilot_baseline_report.py)

권장 task:

- `forecast_transition_task`
- `forecast_management_task`
- `forecast_wait_quality_task`
- `forecast_economic_task`

중요 원칙:

- future 결과로 만든 컬럼은 입력 feature로 직접 넣지 않는다
- auxiliary target으로만 쓴다

완료 기준:

- baseline report에 forecast-state25 integration 섹션이 생김
- 최소 1개 이상 task가 `ready=true`로 열림

### FSB5. Candidate Compare Integration

목표:

- AI3 compare와 AI4 gate에서 forecast-state25 축 regression/gain을 따로 본다.

대상 파일:

- [teacher_pattern_candidate_pipeline.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_candidate_pipeline.py)
- [teacher_pattern_promotion_gate.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_promotion_gate.py)

비교 항목:

- transition auxiliary delta
- management auxiliary delta
- wait-quality auxiliary delta
- economic utility delta
- symbol별 regression concentration
- scene family별 regression concentration

완료 기준:

- candidate summary에 forecast-state25 compare 항목이 생김
- gate에서 이 축을 soft/hard blocker로 구분해 읽을 수 있음

### FSB6. Execution Log-Only Overlay

목표:

- forecast-state25 bridge가 threshold / size / wait bias에 어떤 영향을 줄지 runtime에서 기록만 한다.

대상 파일:

- [teacher_pattern_execution_policy_integration.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_execution_policy_integration.py)
- [teacher_pattern_execution_policy_log_only_binding.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_execution_policy_log_only_binding.py)
- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)

기록 대상:

- `candidate_if_threshold_delta`
- `candidate_if_size_multiplier`
- `candidate_if_wait_bias_release`
- `candidate_if_hold_bias`

완료 기준:

- 실제 매매 변화 없이 trace만 쌓임
- runtime status와 entry row에서 예상 overlay가 읽힘

### FSB7. Canary

목표:

- 충분한 근거가 생기면 아주 좁은 범위에서만 실제 반영한다.

권장 범위:

- symbol 1개
- scene family 1개
- threshold 또는 size 중 1개만

조건:

- AI4 gate 통과
- AI6 log_only 관찰 안정
- rollback 기준 정의 완료

완료 기준:

- canary applied / held / rolled_back가 명확히 기록됨

### FSB8. Bounded Live

목표:

- canary가 안정적일 때 제한된 범위 live 반영으로 확장한다.

권장 제한:

- symbol allowlist
- scene family allowlist
- max threshold delta
- max size multiplier
- rollback window

완료 기준:

- bounded live contract가 명시됨
- 자동 rollback이 동작함

## 4. 구현 우선순위

지금 바로 손으로 밀 순서는 아래가 맞다.

1. `FSB1 runtime bridge`
2. `FSB2 replay / outcome bridge`
3. `FSB3 seed enrichment`
4. `FSB4 baseline auxiliary task`
5. `FSB5 candidate compare`
6. `FSB6 log_only overlay`
7. `FSB7 canary`
8. `FSB8 bounded live`

## 5. 지금 단계에서의 현실적인 메인

현재 상태를 감안하면 지금 당장 메인은 `FSB1`이다.

이유:

- runtime에 먼저 안 남기면 이후 replay / seed / compare도 일관되게 묶을 수 없다
- 특히 사용자 의도인 `더 좋은 진입`, `더 좋은 기다림`, `더 좋은 청산`의 출발점이 runtime scene trace이기 때문이다

즉 첫 구현은 `행동 변경`이 아니라 `scene-forecast bridge 기록`부터다.

## 6. 추천 보고서

구현 이후 바로 보고 싶은 리포트는 아래 순서가 좋다.

1. runtime status detail
2. entry decision trace
3. forecast-state25 outcome bridge md
4. experiment seed report
5. pilot baseline report
6. candidate watch latest

## 7. 완료 기준

이번 로드맵이 기본 완성됐다고 보려면 아래가 보여야 한다.

- runtime bridge가 안정적으로 기록된다
- replay/outcome bridge가 md/json으로 떨어진다
- seed enrichment가 closed history에 붙는다
- baseline/candidate가 이 축을 auxiliary로 읽는다
- compare/gate가 이 축 regression을 구분해 본다
- live는 log_only -> canary -> bounded live 순서로만 열린다

## 8. 결론

forecast-state25 bridge는 별도 기능 하나가 아니다.

이건 지금 이미 만든 `forecast`, `state25`, `wait_quality`, `economic_target`, `candidate loop`를 한 체인으로 묶는 마지막 공통 학습 기반이다.

그래서 구현 순서도 `예측을 더 잘하게 만드는 일`과 `그 예측을 더 잘 배우게 만드는 일`을 동시에 만족하도록 짜야 한다.
