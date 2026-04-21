# Current PA7 Review Queue Processing Detailed Plan

## 목적

이 문서는 기존 `PA7 review queue packet`을 실제로 소화하기 위한 2차 처리 기준서다.

현재 queue에는 세 종류가 섞여 있다.

- 진짜 정책 충돌 그룹
- baseline / score가 비어 있는 hydration gap 그룹
- baseline과 hindsight는 사실상 같은데 confidence 부족 때문에 manual로 남은 그룹

이 세 종류를 분리하지 않으면 사람 검토가 noisy해진다.

## 왜 지금 필요한가

최신 packet에서 상위 그룹을 보면:

- `runner_secured_continuation -> WAIT` 는 row 수가 크지만,
  다수는 `runtime_proxy == hindsight WAIT`라서 실제 정책 충돌보다 confidence-only 성격이 강하다.
- 반면 `protective_exit_surface + active_open_loss + baseline PARTIAL_EXIT + hindsight WAIT`
  같은 그룹은 진짜 review 대상이다.
- 또 일부 그룹은 `management_action_label`과 score가 비어 있어
  review 이전에 hydration gap으로 처리하는 편이 맞다.

즉 PA7을 실제로 소화하려면
`manual_exception_count`만 보는 것이 아니라
`왜 manual로 남았는지`를 먼저 나눠야 한다.

## 새 2차 분류 축

### 1. policy_mismatch_review

의미:

- baseline action과 hindsight action이 실제로 다르다.
- 그리고 그 차이가 group 수준에서도 반복된다.

예시:

- `baseline PARTIAL_EXIT`, `hindsight WAIT`
- `baseline HOLD`, `hindsight PARTIAL_THEN_HOLD`

이 그룹은 사람이 먼저 봐야 한다.

### 2. baseline_hydration_gap

의미:

- group 다수가 `management_action_label` blank
- 동시에 runtime score도 비어 있다

즉 rule 문제보다
“예전 row가 현재 contract로 충분히 hydrate되지 못했다”에 가깝다.

이 그룹은 바로 policy review로 보내지 않고,
데이터/재생성 backlog로 분리하는 것이 맞다.

### 3. confidence_only_confirmed

의미:

- `resolved baseline`과 hindsight가 대부분 일치한다
- 그런데 low confidence / low gap 때문에 manual_exception으로 남았다

이 그룹은 “지금 당장 rule을 바꿔야 하는 queue”보다
“PA8 이전까지 표본을 더 쌓아도 되는 queue”에 가깝다.

## 구현 항목

### 입력

- [checkpoint_dataset_resolved.csv](/C:/Users/bhs33/Desktop/project/cfd/data/datasets/path_checkpoint/checkpoint_dataset_resolved.csv)

### 출력

- 새 서비스:
  [path_checkpoint_pa7_review_processor.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_pa7_review_processor.py)
- 새 빌더:
  [build_checkpoint_pa7_review_processor.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/build_checkpoint_pa7_review_processor.py)
- 새 artifact:
  `checkpoint_pa7_review_processor_latest.json`

## group-level 핵심 계산

### resolved_baseline_action_label

순서:

- `management_action_label`이 있으면 그것을 baseline으로 사용
- 없으면 `runtime_proxy_management_action_label`을 fallback baseline으로 사용

이 값이 있어야
“blank baseline noise”와 “진짜 disagreement”를 분리할 수 있다.

### blank_baseline_share

- blank `management_action_label` row 비율

### missing_score_share

- `runtime_hold_quality_score`
- `runtime_partial_exit_ev`
- `runtime_full_exit_risk`

셋이 모두 비어 있는 row 비율

### baseline_match_rate

- `resolved_baseline_action_label == hindsight_best_management_action_label`
  row 비율

## disposition 규칙

### confidence_only_confirmed

조건:

- `baseline_match_rate >= 0.85`
- `resolved_baseline_action_label`이 비어 있지 않음
- `row_count >= 10`

의미:

- rule 충돌보다는 confidence-only 검토

### baseline_hydration_gap

조건:

- `blank_baseline_share >= 0.60`
- `missing_score_share >= 0.60`

의미:

- 먼저 hydration / replay / backfill 관점으로 처리

### policy_mismatch_review

조건:

- `baseline_match_rate <= 0.25`
- `resolved_baseline_action_label`과 hindsight가 모두 비어 있지 않음

의미:

- 사람이 우선적으로 봐야 하는 정책 충돌

### mixed_review

위 세 조건에 깔끔히 안 들어가는 경우

## 우선순위

### High

- `policy_mismatch_review`
- row_count가 큰 `baseline_hydration_gap`

### Medium

- row_count가 큰 `mixed_review`

### Low

- `confidence_only_confirmed`

## 이번 단계에서 의도적으로 하지 않는 것

- 실제 hindsight/action 규칙 자체를 다시 바꾸지 않는다
- PA8 adoption으로 바로 넘기지 않는다
- scene bias preview 정책은 건드리지 않는다

## 완료 조건

- 새 processor artifact가 생성됨
- top group이 `policy_mismatch / hydration_gap / confidence_only`로 실제로 나뉨
- 다음 사람이 바로 무엇부터 봐야 하는지 packet 수준에서 읽을 수 있음
