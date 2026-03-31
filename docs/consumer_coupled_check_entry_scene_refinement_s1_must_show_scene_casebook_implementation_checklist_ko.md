# Consumer-Coupled Check/Entry Scene Refinement
## S1. Must-Show Scene Casebook Implementation Checklist

### 목표

사용자가 차트에서 “약한 체크라도 반드시 있어야 한다”고 느끼는 장면을
scene family 기준으로 정리하고,
runtime row와 연결된 `must-show casebook`으로 고정한다.

## 현재 상태

- `Step 1 ~ Step 9`: 1차 완료

현재 산출물:

- `consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_spec_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_ko.md`

현재 S1은:

- screenshot/manual case를 thread 기준으로 intake했고
- recent runtime row와 연결했고
- `good / missing / debatable` 분류와 contract candidate까지 정리한 상태다

## Step 1. S0 Baseline Reuse

### 해야 할 일

- S0 baseline memo를 기준선으로 다시 읽는다
- 아래를 이번 S1의 출발점으로 고정한다

### 확인 포인트

- `BTC/NAS leakage`가 강하다는 점
- `XAU divergence`가 강하다는 점
- `must-show missing`은 recent data-only로는 자동 확보가 부족하다는 점

### 완료 기준

- S1이 왜 screenshot/manual casebook 중심이어야 하는지 설명 가능하다

### 상태

- 완료

## Step 2. Screenshot / Manual Case Intake

### 해야 할 일

- 사용자가 표시한 chart screenshot에서
  “여긴 떠야 한다” 장면을 모은다
- 각 case에 임시 id를 붙인다

### 필수 기록

- symbol
- 대략적 chart 위치
- 사용자가 기대한 방향
- 사용자가 기대한 표시 강도

### 완료 기준

- 최소 6건 이상 사례를 확보한다

### 상태

- 완료
- thread에서 사용자가 직접 지적한 case와 runtime mapping을 함께 사용했다

## Step 3. Runtime Row Mapping

### 해야 할 일

- 각 screenshot/manual case를 recent row와 매핑한다
- 가장 가까운 `entry_decisions.csv` row를 찾는다

### 필수 기록

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_scene_id`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `consumer_check_display_score`
- `entry_ready`

### 완료 기준

- 각 case가 runtime row와 연결된다

### 상태

- 부분 완료
- 대부분 recent runtime row와 연결됐고
- `BTC upper reject manual carry-over`는 exact row 매핑 보강이 남아 있다

## Step 4. Scene Family Classification

### 해야 할 일

- case를 아래 family로 분류한다

### family

- `lower rebound`
- `upper reject`
- `middle reclaim / middle reject`
- `edge watch`
- `other`

### 완료 기준

- 모든 case가 적어도 하나의 family에 들어간다

### 상태

- 완료

## Step 5. Expected Minimum Display 결정

### 해야 할 일

- 각 case마다 최소 표시 기대치를 정한다

### 선택지

- `OBSERVE`
- `WATCH / WAIT`
- `PROBE`

### 완료 기준

- 각 case마다 `expected_min_display`가 있다

### 상태

- 완료

## Step 6. Good / Missing / Debatable 분류

### 해야 할 일

- 각 case를 아래 셋 중 하나로 분류한다

### 분류

- `good`
- `missing`
- `debatable`

### 완료 기준

- 실제 refinement 대상으로 봐야 할 `missing` case가 분리된다

### 상태

- 완료

## Step 7. Casebook 문서 작성

### 해야 할 일

- S1 casebook 문서를 만든다
- family별로 사례를 정리한다

### 필수 섹션

- family summary
- case table
- representative missing cases
- representative good cases
- representative debatable cases

### 완료 기준

- S4에서 바로 참조 가능한 casebook이 만들어진다

### 상태

- 완료

## Step 8. Contract Candidate 정리

### 해야 할 일

- casebook을 바탕으로
  어떤 scene contract를 추가/완화할지 후보를 정리한다

### 예시

- `outer_band_reversal_support_required_observe`는 must-show인가
- `middle_sr_anchor_required_observe`는 어떤 조건에서 must-show인가
- `upper_reject_probe_observe`는 어떤 guard가 있어도 약한 체크는 남겨야 하는가

### 완료 기준

- S4 contract refinement candidate list가 준비된다

### 상태

- 완료

## Step 9. Follow-up Priority 정리

### 해야 할 일

- S1 이후 우선순위를 적는다

### 일반 순서

1. `S2 must-hide scene casebook`
2. `S3 visually similar scene alignment audit`
3. `S4 contract refinement`

### 완료 기준

- S1 이후 바로 다음 단계가 명확히 적혀 있다

### 상태

- 완료

## S1 완료 조건

아래가 충족되면 S1은 완료로 본다.

- screenshot/manual case가 충분히 수집돼 있다
- 각 case가 runtime row와 연결돼 있다
- family 분류가 돼 있다
- `expected_min_display`가 정리돼 있다
- `good / missing / debatable` 분류가 있다
- S4 contract candidate list가 있다

현재 판정:

- `S1 1차 구현 = 완료`
- 다음 우선순위는 `S2 must-hide scene casebook`
