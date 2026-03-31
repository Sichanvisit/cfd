# Consumer-Coupled Check/Entry Scene Refinement
## S3. Visually Similar Scene Alignment Audit Implementation Checklist

### 목표

차트상으로 유사하게 보이는데
내부에서는 서로 다른 side / scene / stage로 갈라지는 장면을
pair / cluster 기준으로 정리하고,
의도된 divergence와 수정 대상 divergence를 분리한다.

## 현재 상태

- `Step 1 ~ Step 9`: 1차 완료

현재 산출물:

- `consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_spec_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_ko.md`

현재 S3는:

- representative cluster를 정리했고
- divergence axis를 분류했고
- `intentional / accidental / partial alignment` 판정을 내렸고
- S4 alignment contract candidate까지 준비한 상태다

## Step 1. S0 / S1 / S2 Baseline Reuse

### 해야 할 일

- S0 baseline memo를 다시 읽는다
- S1 must-show casebook을 다시 읽는다
- S2 must-hide casebook을 다시 읽는다

### 확인 포인트

- `BTC/NAS leakage`가 강하다는 점
- `XAU divergence`가 강하다는 점
- must-show / must-hide만으로는 설명되지 않는 scene gap이 있다는 점

### 완료 기준

- S3가 왜 필요한지 baseline 관점에서 설명 가능하다

### 상태

- 완료

## Step 2. Cluster 후보 수집

### 해야 할 일

- visually similar cluster 후보를 모은다

### 우선 cluster

- `lower rebound end-of-drop`
- `upper reject / upper conflict`
- `middle anchor / middle wait`

### 완료 기준

- 최소 3개 cluster가 정리된다

### 상태

- 완료

## Step 3. Pair / Cluster Runtime Mapping

### 해야 할 일

- 각 cluster의 대표 pair를 recent row와 연결한다

### 필수 기록

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_scene_id`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `box_state`
- `bb_state`

### 완료 기준

- 각 cluster가 runtime row와 연결된다

### 상태

- 완료

## Step 4. Divergence Axis 정리

### 해야 할 일

- 각 pair가 왜 갈라지는지 아래 축으로 적는다

### 축

- `context divergence`
- `rule divergence`
- `symbol temperament divergence`
- `display translation divergence`

### 완료 기준

- 각 pair에 최소 하나의 divergence axis가 있다

### 상태

- 완료

## Step 5. Intentional / Accidental / Partial 분류

### 해야 할 일

- 각 pair를 아래 셋 중 하나로 분류한다

### 분류

- `intentional divergence`
- `accidental divergence`
- `partial alignment`

### 완료 기준

- 어떤 pair를 통일해야 하는지가 드러난다

### 상태

- 완료

## Step 6. Alignment Recommendation 작성

### 해야 할 일

- 각 pair에 대해 alignment recommendation을 적는다

### 선택지 예시

- `keep separated`
- `align stage only`
- `align display only`
- `align scene family`
- `needs symbol-specific exception`

### 완료 기준

- S4에서 바로 참조 가능한 정렬 권고가 있다

### 상태

- 완료

## Step 7. Audit 문서 작성

### 해야 할 일

- S3 audit 문서를 만든다

### 필수 섹션

- cluster summary
- pair table
- representative intentional cases
- representative accidental cases
- representative partial alignment cases

### 완료 기준

- S4 contract refinement의 직접 입력 문서가 된다

### 상태

- 완료

## Step 8. Alignment Contract Candidate 정리

### 해야 할 일

- audit 결과를 contract candidate로 묶는다

### 예시

- `BTC/NAS lower rebound`와 `XAU conflict`를 같은 family로 더 묶을지 여부
- `middle anchor observe`를 심볼별로 얼마나 통일할지 여부
- `upper reject family`를 더 공통적으로 읽게 할지 여부

### 완료 기준

- S4 contract refinement candidate list가 준비된다

### 상태

- 완료

## Step 9. Follow-up Priority 정리

### 해야 할 일

- S3 이후 우선순위를 적는다

### 일반 순서

1. `S4 consumer_check_state contract refinement`
2. `S5 symbol balance tuning`

### 완료 기준

- S3 이후 바로 다음 단계가 명확히 적혀 있다

### 상태

- 완료

## S3 완료 조건

아래가 충족되면 S3는 완료로 본다.

- cluster가 충분히 수집돼 있다
- 각 cluster가 runtime row와 연결돼 있다
- divergence axis가 정리돼 있다
- intentional / accidental / partial 분류가 있다
- alignment recommendation이 있다
- S4 alignment contract candidate list가 있다

현재 판정:

- `S3 1차 구현 = 완료`
- 다음 우선순위는 `S4 consumer_check_state contract refinement`
