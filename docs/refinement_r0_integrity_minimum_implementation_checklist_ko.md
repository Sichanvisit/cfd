# R0 Integrity Minimum Implementation Checklist

## 1. 목적

이 문서는 [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)을 실제 구현 순서로 내린 체크리스트다.

핵심은 `R0를 전부 한 번에 고치는 것`이 아니라, 아래 순서로 범위를 잠그고 검증 가능한 단위로 나누는 것이다.


## 2. 이번 단계에서 할 것과 하지 않을 것

### 할 것

- owner separation audit
- probe promotion miss 사례 수집
- non-action taxonomy 정리
- semantic canary recent window 테스트 안정화

### 하지 않을 것

- `Stage E` 심볼별 수치 튜닝
- chart flow baseline 재조정
- semantic target/split 재설계
- promotion gate 확장


## 3. 입력 기준

- 마스터 계획: [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)
- R0 spec: [refinement_r0_integrity_minimum_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_integrity_minimum_spec_ko.md)
- R0 matrix/casebook: [refinement_r0_owner_matrix_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_owner_matrix_casebook_ko.md)
- R0 taxonomy/key linkage: [refinement_r0_non_action_taxonomy_and_key_linkage_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_non_action_taxonomy_and_key_linkage_ko.md)
- 대상 파일:
  - `backend/services/entry_service.py`
  - `backend/services/storage_compaction.py`
  - `scripts/check_semantic_canary_rollout.py`
  - `tests/unit/test_check_semantic_canary_rollout.py`


## 4. 구현 순서

### Step 1. Owner Matrix 작성

할 일:

- `observe_reason`
- `blocked_by`
- `action_none_reason`

세 필드가 어떤 경로에서 채워지는지 코드 기준으로 정리한다.

확인 포인트:

- fallback이 서로를 덮어쓰지 않는지
- quick trace / compact row에서도 의미가 유지되는지
- row 해석 순서가 문서와 코드에서 어긋나지 않는지

완료 기준:

- owner matrix 초안이 있다.
- 대표 row 예시 3개 이상으로 설명 가능하다.


### Step 2. Probe Promotion Miss 케이스북 작성

할 일:

- `probe_candidate_v1.active=true`
- `entry_probe_plan_v1.ready_for_entry=false`

조건의 대표 케이스를 수집한다.

최소 분류:

- `probe_not_promoted`
- `confirm_suppressed`
- `execution_soft_blocked`
- `policy_hard_blocked`
- `other/missing-reason`

완료 기준:

- 최소 1건 이상 대표 케이스를 각 분류에 연결할 수 있다.
- 분류 불가 케이스가 있으면 별도 backlog로 남긴다.


### Step 3. Non-Action Taxonomy 고정

할 일:

- row 해석 규칙을 문서화한다.
- runtime row에서 "왜 non-action인지"를 읽는 순서를 정한다.

권장 해석 순서:

1. `observe_reason`
2. `blocked_by`
3. `action_none_reason`
4. `probe_state`
5. `entry_probe_plan_v1`
6. `semantic_live_reason`

완료 기준:

- non-action taxonomy table이 문서에 들어간다.
- row-only interpretation이 가능하다.


### Step 4. Storage / Key 연결 점검

할 일:

- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`

가 R0에서 필요한 해석 필드를 놓치지 않는지 확인한다.

확인 포인트:

- `observe_reason`
- `probe_state`
- `blocked_by`
- `action_none_reason`

완료 기준:

- replay/export에서 key suffix로 reason 추적이 가능한지 설명 가능하다.
- 누락 필드가 있으면 R2 backlog로 넘기지 말고 R0 범위 내에서 바로 보강할지 판정한다.


### Step 5. Semantic Canary 테스트 안정화

할 일:

- `write_canary_report()`의 recent window 계산이 날짜 변화에 덜 민감하도록 정리한다.
- 필요하면 기준 시각 주입 또는 relative fixture 전략을 도입한다.

최소 확인 항목:

- `tests/unit/test_check_semantic_canary_rollout.py`
- recent rows count
- output file 생성
- fallback / threshold counts 유지

완료 기준:

- 날짜가 바뀌어도 테스트가 안정적으로 통과한다.
- canary report의 recent window 기준이 문서로 설명된다.

현재 반영 메모:

- `write_canary_report(..., now=...)` 기준 시각 주입 지원
- `build_canary_report(..., now=...)` 기준 시각 주입 지원
- `window_start`, `semantic_live_reason_counts` 산출


### Step 6. 테스트 및 회귀 확인

최소 실행 권장:

- `pytest tests/unit/test_check_semantic_canary_rollout.py`

상황에 따라 함께 볼 것:

- `pytest tests/unit/test_semantic_v1_runtime_adapter.py`
- `pytest tests/unit/test_semantic_v1_shadow_compare.py`
- `pytest tests/unit/test_promote_semantic_preview_to_shadow.py`

완료 기준:

- canary 관련 테스트가 통과한다.
- R0 수정이 semantic observability를 깨지 않는다.


### Step 7. 문서 동기화

할 일:

- R0 spec과 checklist를 현재 상태로 맞춘다.
- 마스터 refinement 문서의 R0 섹션을 요약 기준으로 유지한다.

완료 기준:

- R0 문서만 읽어도 지금 상태와 다음 착수점이 보인다.


## 5. 이번 단계의 done definition

아래가 모두 만족되면 R0 구현 착수 단계가 끝난 것으로 본다.

- owner matrix가 정리됨
- probe promotion miss casebook이 정리됨
- non-action taxonomy가 정리됨
- canary recent window 테스트가 안정화됨
- 마스터 refinement 문서와 R0 전용 문서가 서로 어긋나지 않음


## 6. 다음 단계

R0가 끝나면 다음은 [refinement_track_execution_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_track_execution_plan_ko.md)의 `R1. Stage E 미세조정`이다.

즉 순서는 아래처럼 본다.

```text
R0 정합성 최소셋
-> R1 Stage E 미세조정
-> R2 저장 / export / replay 정합성
-> R3 Semantic ML Step 3~7 refinement
-> R4 Acceptance / promotion-ready
```
