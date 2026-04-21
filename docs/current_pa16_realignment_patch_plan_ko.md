# Current PA1-PA6 Realignment Patch Plan

## 목적

이 문서는 기존 `PA1~PA6` 구현이 현재 운영 구조와 어디서 어긋나는지 다시 정리하고,
안전한 순서로 realignment patch를 넣기 위한 상세 작업 기준서다.

핵심 원칙은 하나다.

- 이미 올라간 `scene / review packet / preview-only bias` 구조를 거꾸로 PA1~PA6에 억지로 밀어넣지 않는다.
- 대신 `PA1 leg`, `PA2 checkpoint`, `PA5 eval semantics` 중 지금 당장 낡은 가정이 남아 있는 지점만 최소 패치한다.

## 현재 리뷰 findings 요약

### 1. PA1 leg 경계가 너무 끈적하다

- `direction_flip`이 생겨도 새 leg가 실제로 열리는 조건이 너무 좁다.
- 특히 `entry_candidate_bridge_selected` 같은 "새 진입 의도"가 살아 있는 row가 들어와도,
  `outcome=entered` 또는 직접 `observe_action=BUY/SELL`가 아니면 기존 leg를 너무 오래 유지한다.
- 결과적으로 큰 live runner / hold / protective 흐름이 한 leg에 과도하게 묶인다.

### 2. PA2 checkpoint bucket이 현재 관리 문맥을 거의 안 본다

- 현재 checkpoint type은 사실상 `leg_row_count`, `opposite_pressure`, `reclaim_signal`에 많이 의존한다.
- 그런데 지금 row에는 이미 다음 문맥이 있다.
  - `exit_stage_family`
  - `checkpoint_rule_family_hint`
  - `runner_secured`
  - `source`
- 이 정보가 checkpoint 분류에 거의 안 들어가서 `RUNNER_CHECK` 비중이 과해진다.

### 3. PA5 recommendation semantics가 현재 단계보다 뒤처져 있다

- eval artifact가 아직도 `proceed_to_pa6_best_action_resolver`를 추천한다.
- 하지만 실제 구조는 이미 `PA7 review packet`, `scene preview-only hold`, `PA8 baseline-only review` 단계까지 왔다.
- 따라서 recommendation 문구와 gating 의미를 다시 맞춰야 한다.

## 구현 순서

### Step 1. PA1 leg reopen realignment

대상 파일:

- [path_leg_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_leg_runtime.py)
- [test_path_leg_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_leg_runtime.py)

수정 목표:

- `entry_candidate_bridge_selected + bridge_action`이 살아 있는 경우를
  "fresh entry intent"로 인정한다.
- 이 신호가 active leg와 반대 방향이면,
  기존 `entered/observe_action`만 보던 것보다 한 단계 빠르게 새 leg를 열 수 있게 한다.
- 단순 `breakout_candidate_direction` 같은 약한 힌트만으로 leg를 쪼개지는 않게 유지한다.

검증 포인트:

- shallow rebuild는 계속 같은 leg를 유지해야 한다.
- selected bridge flip은 새 leg를 열어야 한다.

### Step 2. PA2 checkpoint context-aware rebucketing

대상 파일:

- [path_checkpoint_segmenter.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_segmenter.py)
- [test_path_checkpoint_segmenter.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_segmenter.py)

수정 목표:

- `runner_secured_continuation`, `exit_stage_family=runner`, `runner_secured=true`는
  row-count만 기다리지 말고 `RUNNER_CHECK` 후보로 인정한다.
- `open_loss_protective`, `active_open_loss`, `protective_exit_bias`, `exit_stage_family=protective`
  같은 protective late row는 `RUNNER_CHECK` 대신 `LATE_TREND_CHECK` 쪽으로 보낸다.
- `hold/profit bias` late row는 protective/runner와 구분해 `LATE_TREND_CHECK`로 정리한다.

검증 포인트:

- runner context는 threshold 이전에도 `RUNNER_CHECK`가 가능해야 한다.
- protective late context는 runner threshold를 넘었어도 `RUNNER_CHECK`로 빨려들지 않아야 한다.

### Step 3. PA5 eval / review semantics realignment

대상 파일:

- [path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_dataset.py)
- [test_path_checkpoint_dataset.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_dataset.py)

수정 목표:

- dataset summary recommendation을 현재 단계에 맞게 바꾼다.
- `PA6` 추천을 기본값으로 두지 않는다.
- 새 의미:
  - 데이터 부족 -> `collect_more_*_before_pa7`
  - manual exception 존재 -> `proceed_to_pa7_review_queue`
  - manual exception이 충분히 정리된 baseline -> `proceed_to_pa8_action_baseline_review`

검증 포인트:

- 작은 테스트셋은 여전히 수집 추천이어야 한다.
- manual exception이 남아 있으면 `PA7 review queue` 추천이어야 한다.

## 이번 패치에서 의도적으로 하지 않는 것

- `scene bias`를 PA6 resolver 본체에 섞지 않는다.
- `time_decay_risk` / `trend_exhaustion` preview-only 정책은 건드리지 않는다.
- `PA7~PA9` 전체 정의 재작성은 별도 문서
  [current_pa789_roadmap_realignment_v1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_pa789_roadmap_realignment_v1_ko.md)
  에 맡긴다.

## 완료 조건

- PA1 selected bridge flip test 통과
- PA2 runner/protective rebucket test 통과
- PA5 recommendation semantics test 통과
- 관련 영향권 회귀 테스트 통과
- 최신 action eval artifact가 더 이상 `proceed_to_pa6_best_action_resolver`를 기본 추천으로 남기지 않음
