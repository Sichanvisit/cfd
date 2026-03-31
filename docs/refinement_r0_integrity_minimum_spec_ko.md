# R0 Integrity Minimum Spec

## 1. 목적

이 문서는 [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)의 `R0. 정합성 최소셋`을 전용 spec으로 분리한 문서다.

R0의 목적은 단순히 필드를 더 저장하는 것이 아니라, 현재 runtime row와 trace만 읽어도 아래 질문에 즉시 답할 수 있게 만드는 것이다.

- 왜 observe인지
- 왜 blocked인지
- 왜 probe가 승격되지 않았는지
- 왜 semantic runtime이 inactive인지


## 2. 이 문서의 역할

- `R0`의 source of truth 역할을 한다.
- 구현 순서는 별도 문서인 [refinement_r0_integrity_minimum_implementation_checklist_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_implementation_checklist_ko.md)에서 다룬다.
- owner matrix와 probe promotion 사례는 [refinement_r0_owner_matrix_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_owner_matrix_casebook_ko.md)에 고정한다.
- non-action taxonomy와 key linkage는 [refinement_r0_non_action_taxonomy_and_key_linkage_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_non_action_taxonomy_and_key_linkage_ko.md)에 고정한다.
- `R1 Stage E` 이상의 미세조정은 이 문서의 범위 밖이다.


## 3. 범위

### 3-1. 포함 범위

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_candidate_v1`
- `entry_probe_plan_v1`
- semantic canary report
- semantic runtime activation reason

### 3-2. 주 대상 파일

- `backend/services/entry_service.py`
- `backend/services/storage_compaction.py`
- `scripts/check_semantic_canary_rollout.py`
- `tests/unit/test_check_semantic_canary_rollout.py`

### 3-3. 비포함 범위

- `Position / Response / State / Evidence / Belief / Barrier` 재설계
- `Stage E` 체감 튜닝
- symbol override 값 조정
- semantic target/split 재정의


## 4. 현재 해석 기준

R0는 아래 owner 분리를 흐리지 않는 방향으로만 진행한다.

| 필드 | 뜻 | owner 해석 |
| --- | --- | --- |
| `observe_reason` | 왜 observe 또는 directional wait 문맥이 형성됐는지 | semantic / observe 계층 |
| `blocked_by` | 어떤 직접 guard, gate, consumer block이 action을 막았는지 | block / execution gate 계층 |
| `action_none_reason` | 최종적으로 왜 non-action으로 귀결됐는지 | consumer / action 결과 계층 |
| `probe_candidate_v1` | probe 후보가 왜 살아 있는지와 기본 readiness | observe / probe candidate 계층 |
| `entry_probe_plan_v1` | probe 후보가 실제 진입 계획으로 승격됐는지 | entry planning 계층 |

핵심 원칙은 이렇다.

- `observe_reason`는 "맥락 설명"이다.
- `blocked_by`는 "즉시 차단 원인"이다.
- `action_none_reason`는 "최종 non-action 라벨"이다.
- 세 필드는 서로 대체재가 아니라, 서로 다른 owner를 가진다.


## 5. 현재 코드 기준 스냅샷

2026-03-25 KST 기준 현재 코드에서는 이미 아래 기반이 있다.

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
  - `observe_reason`, `blocked_by`, `action_none_reason` 기록
  - `probe_not_promoted`, `confirm_suppressed`, `execution_soft_blocked`, `policy_hard_blocked` 기록
  - `entry_probe_plan_v1` 생성
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
  - `decision_row_key`에 `observe_reason`, `probe_state`, `blocked_by`, `action_none_reason` suffix 반영
- [check_semantic_canary_rollout.py](c:\Users\bhs33\Desktop\project\cfd\scripts\check_semantic_canary_rollout.py)
  - recent window 기반 canary report 생성
  - 기준 시각 주입이 가능해져 날짜 변화에 덜 흔들린다.
  - `semantic_live_reason_counts`, `window_start`가 함께 기록된다.

즉 R0는 "없는 구조를 새로 만드는 단계"라기보다, 이미 존재하는 trace 구조를 설명 가능하고 흔들리지 않게 정제하는 단계다.


## 6. R0 세부 작업축

### R0-1. Owner Separation Audit

목표:

- `observe_reason / blocked_by / action_none_reason`가 실제 코드에서도 다른 owner를 유지하는지 점검한다.

해야 할 일:

- row 생성 경로에서 세 필드가 어디서 채워지는지 추적한다.
- 같은 상황에서 세 필드가 서로 덮어쓰이거나 빈 문자열 fallback으로 섞이지 않는지 확인한다.
- `row-only interpretation` 기준으로 각 필드가 어떤 질문에 답하는지 표로 고정한다.

산출물:

- owner matrix
- field precedence 메모
- 대표 예시 row 3~5개


### R0-2. Probe Promotion Casebook

목표:

- `probe_candidate_v1.active=true`인데 `entry_probe_plan_v1.ready_for_entry=false`인 케이스를 설명 가능하게 만든다.

해야 할 일:

- 대표 non-action 케이스를 모은다.
- 아래 분류가 실제로 분리되는지 확인한다.
  - `probe_not_promoted`
  - `confirm_suppressed`
  - `execution_soft_blocked`
  - `policy_hard_blocked`
- 분류되지 않는 예외 케이스가 있으면 `other/missing-reason`으로 모아 별도 기록한다.

산출물:

- promotion miss casebook
- 대표 blocked sample 표
- missing reason 후보 목록


### R0-3. Non-Action Taxonomy and Trace Contract

목표:

- "왜 non-action인지"를 row 하나만으로 해석할 수 있는 분류표를 만든다.

해야 할 일:

- `observe_reason`, `blocked_by`, `action_none_reason`, `probe_state`, `entry_probe_plan_v1`, `semantic_live_reason`의 해석 순서를 고정한다.
- runtime row, compact row, replay/export row에서 빠지면 안 되는 최소 필드를 정한다.
- `semantic inactive`, `probe inactive`, `consumer blocked`, `default side blocked`를 row 기준으로 구별 가능하게 만든다.

산출물:

- non-action taxonomy table
- trace contract v1
- row interpretation cheat sheet


### R0-4. Semantic Canary Stabilization

목표:

- semantic canary report가 날짜 변화에 흔들리지 않게 만든다.

해야 할 일:

- `recent window` 계산이 테스트 가능한 형태인지 점검한다.
- 필요하면 `now` 주입 또는 기준 시각 override를 허용한다.
- fixture row가 절대 날짜에 덜 의존하도록 보정한다.
- canary report에서 `semantic inactive`와 fallback reason이 runtime row와 같은 언어로 읽히는지 확인한다.

산출물:

- deterministic canary test
- recent window 계산 기준 고정
- runtime activation reason 해석 메모


## 7. R0 완료 기준

아래가 모두 만족되면 R0를 완료로 본다.

- 대표 non-action reason을 설명 가능한 분류표로 만들 수 있다.
- `probe_candidate_v1.active=true`인데 `ready_for_entry=false`인 대표 케이스를 reason별로 설명할 수 있다.
- `probe_not_promoted`, `confirm_suppressed`, `execution_soft_blocked`, `policy_hard_blocked`가 row 기준으로 분리 해석된다.
- canary report 테스트가 날짜 변화에 흔들리지 않는다.
- runtime row만 봐도 `semantic inactive` 이유를 설명할 수 있다.


## 8. R0 이후 handoff

R0가 끝나면 다음은 [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)의 `R1. Stage E 미세조정`으로 넘어간다.

즉 R0는 튜닝 단계가 아니라, 이후 미세조정을 믿고 진행하기 위한 trace 해석 기반 정리 단계다.
