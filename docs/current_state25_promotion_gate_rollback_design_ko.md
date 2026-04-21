# State25 Promotion Gate Rollback Design

## 목적

이 문서는 `AI4 promotion gate / rollback`를 실제로 어떻게 읽고 판단할지 정리한다.

쉽게 말하면 이 문서는 아래 질문에 답한다.

- 후보 모델이 좋아 보여도 왜 바로 live에 올리면 안 되는가
- 언제 `hold`, 언제 `shadow`, 언제 `promote_ready`, 언제 `rollback_recommended`로 볼 것인가
- `AI3 compare 결과`와 `Step 9 readiness`, `canary evidence`를 어떻게 한 줄로 묶을 것인가

## 지금 AI4가 필요한 이유

`AI3`까지 오면 후보 모델은 다시 만들 수 있다.

하지만 여기서 바로 live에 붙이면 아직 위험하다.

- offline compare가 좋아도 live에서 wait drift가 커질 수 있다
- 특정 symbol만 과도하게 몰릴 수 있다
- must-release / bad-exit가 늘 수 있다
- Step 9 execution handoff 자체가 아직 준비 안 된 상태일 수 있다

그래서 AI4는 `좋아 보이는 후보`를 `올려도 되는 후보`와 분리하는 층이다.

## 이번 AI4의 범위

이번 구현은 아래까지를 다룬다.

1. AI3 산출물 읽기
2. Step 9 readiness 읽기
3. optional canary evidence 읽기
4. gate stage 결정
5. rollback 사유 정리
6. 사람이 읽는 md/json 보고서 생성

중요한 점:

- 이번 단계는 아직 실제 live promote를 하지 않는다
- 이번 단계는 `promote decision contract`를 고정하는 단계다
- 실제 execution binding은 AI5에서 다룬다

## 입력

### 1. candidate manifest

- `models/teacher_pattern_state25_candidates/latest_candidate_run.json`

여기서 읽는 핵심 값:

- `candidate_id`
- `output_dir`
- `compare_report_path`
- `promotion_decision_path`

### 2. AI3 compare report

- `teacher_pattern_candidate_compare_report.json`

여기서 읽는 핵심 값:

- reference baseline 존재 여부
- candidate / reference readiness
- task delta

### 3. AI3 promotion decision

- `teacher_pattern_candidate_promotion_decision.json`

여기서 읽는 핵심 값:

- `hold_regression`
- `hold_no_material_gain`
- `promote_review_ready`
- `shadow_only_first_candidate`

### 4. Step 9 watch report

- `data/analysis/teacher_pattern_state25/teacher_pattern_step9_watch_latest.json`

여기서 읽는 핵심 값:

- `execution_handoff_ready`
- `handoff_status`
- `blocker_codes`
- `labeled_rows`
- `rows_to_target`

### 5. optional canary evidence

아직 자동 생성기는 없지만, AI4 contract는 미리 고정한다.

권장 필드:

- `rows_observed`
- `utility_delta`
- `must_release_delta`
- `bad_exit_delta`
- `wait_drift_delta`
- `symbol_skew_delta`
- `watchlist_confusion_delta`

## gate stage 해석

### 1. `hold_offline`

의미:

- offline compare에서 후보를 밀 이유가 없다

대표 상황:

- `hold_regression`
- `hold_no_material_gain`

### 2. `shadow_only`

의미:

- 첫 후보라 reference가 부족하거나, 비교 기준이 아직 얕다
- live binding이 아니라 shadow 관찰만 허용한다

### 3. `hold_step9`

의미:

- 후보 자체는 나쁘지 않지만 Step 9 execution handoff가 아직 준비되지 않았다

즉:

- candidate quality 문제라기보다, state25 운영 readiness 문제다

### 4. `shadow_ready`

의미:

- offline candidate는 좋아 보인다
- Step 9도 준비됐다
- 하지만 canary evidence가 아직 없다

즉:

- 다음 단계는 promote가 아니라 `shadow / small canary`다

### 5. `promote_ready`

의미:

- canary evidence까지 봤을 때 gate를 통과했다
- 이제 AI5 bounded integration을 검토할 수 있다

### 6. `rollback_recommended`

의미:

- canary에서 실제로 나빠진 신호가 나왔다
- current baseline으로 유지하거나 즉시 되돌리는 것이 맞다

## rollback trigger

이번 AI4에서 기본 rollback trigger는 아래 6개다.

1. `must_release_delta` 증가
2. `bad_exit_delta` 증가
3. `utility_delta` 음수 악화
4. `wait_drift_delta` 과도한 증가
5. `symbol_skew_delta` 과도한 확대
6. `watchlist_confusion_delta` 증가

핵심은 이거다.

`오프라인 metric이 좋다`보다 `live에서 실제로 이상한 부작용이 생기지 않았다`가 더 중요하다.

## 기본 임계값

- `min_rows_observed = 50`
- `min_utility_delta = 0.0`
- `max_must_release_delta = 0`
- `max_bad_exit_delta = 0`
- `max_wait_drift_delta = 0.05`
- `max_symbol_skew_delta = 0.10`
- `max_watchlist_confusion_delta = 0`

이 값은 첫 버전이므로, 이후 canary 경험을 보며 조정한다.

## 출력

candidate 폴더마다 아래 두 파일이 생긴다.

- `teacher_pattern_promotion_gate_report.json`
- `teacher_pattern_promotion_gate_report.md`

루트에는 최신 포인터가 생긴다.

- `models/teacher_pattern_state25_candidates/latest_gate_report.json`

## 현재 상태 해석

현재 첫 candidate는 AI3 기준 `hold_no_material_gain`이다.

따라서 지금 AI4를 실제로 돌리면 가장 자연스러운 결과는:

- `gate_stage = hold_offline`
- `recommended_action = keep_current_baseline`

이건 실패가 아니라 정상이다.

지금은 gate가 비어 있지 않고, `좋지 않은 후보를 그냥 올리지 않게 막는 안전층`이 생긴 것이다.
