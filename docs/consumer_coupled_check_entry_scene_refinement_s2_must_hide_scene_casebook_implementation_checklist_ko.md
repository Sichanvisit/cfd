# Consumer-Coupled Check/Entry Scene Refinement
## S2. Must-Hide Scene Casebook Implementation Checklist

### 목표

사용자가 차트에서 “남아 있으면 오해를 만드는 체크”를
scene family 기준으로 정리하고,
runtime row와 연결된 `must-hide casebook`으로 고정한다.

## 현재 상태

- `Step 1 ~ Step 9`: 1차 완료

현재 산출물:

- `consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_spec_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_ko.md`

현재 S2는:

- 대표 leakage family를 수집했고
- `hide / downgrade / reduce / defer` 방향을 정리했고
- S4 suppression contract candidate까지 준비한 상태다

## Step 1. S0 / S1 Baseline Reuse

### 해야 할 일

- S0 baseline과 S1 casebook을 다시 읽는다
- 아래를 이번 S2의 출발점으로 고정한다

### 확인 포인트

- `BTC/NAS lower rebound`가 leakage 핵심이라는 점
- `XAU upper reject`는 must-show와도 연결된다는 점
- `must-hide`는 hidden만이 아니라 downgrade/reduce도 있다는 점

### 완료 기준

- S2가 왜 leakage suppression 중심이어야 하는지 설명 가능하다

### 상태

- 완료

## Step 2. Leakage Candidate Intake

### 해야 할 일

- recent row에서 leakage 후보를 모은다
- 우선 family를 아래로 묶는다

### family

- `lower rebound probe leakage`
- `structural observe over-display`
- `blocked confirm leakage`

### 완료 기준

- 최소 6건 이상 사례를 확보한다

### 상태

- 부분 완료
- representative family 중심의 1차 casebook은 확보했고
- 이후 세부 scene를 늘릴 여지는 남아 있다

## Step 3. Runtime Row Mapping

### 해야 할 일

- 각 leakage candidate를 runtime row와 연결한다

### 필수 기록

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_scene_id`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `entry_ready`

### 완료 기준

- 각 candidate가 runtime row와 연결된다

### 상태

- 완료

## Step 4. Scene Family Classification

### 해야 할 일

- 모든 candidate를 family별로 분류한다

### 완료 기준

- 각 candidate가 하나의 leakage family에 들어간다

### 상태

- 완료

## Step 5. Suppression Direction 결정

### 해야 할 일

- 각 candidate에 대해 아래 중 하나를 정한다

### 선택지

- `hide`
- `downgrade`
- `reduce`

### 완료 기준

- 각 case마다 suppression 방향이 있다

### 상태

- 완료

## Step 6. Hide / Downgrade / Reduce 분류

### 해야 할 일

- candidate를 세 bucket으로 나눈다

### bucket

- `hide`
- `downgrade`
- `reduce`

### 완료 기준

- 실제 contract candidate를 바로 정리할 수 있다

### 상태

- 완료

## Step 7. Casebook 문서 작성

### 해야 할 일

- S2 casebook 문서를 만든다

### 필수 섹션

- family summary
- case table
- representative hide cases
- representative downgrade cases
- representative reduce cases

### 완료 기준

- S4에서 바로 참조 가능한 casebook이 만들어진다

### 상태

- 완료

## Step 8. Suppression Contract Candidate 정리

### 해야 할 일

- casebook을 바탕으로
  어떤 suppression contract를 넣을지 후보를 정리한다

### 예시

- `lower_rebound_probe_observe + barrier_guard + probe_not_promoted`는 reduce인가 downgrade인가
- `lower_rebound_confirm + energy_soft_block`는 hide인가 downgrade인가
- `outer_band_reversal_support_required_observe`는 repeat reduction만 할지 여부

### 완료 기준

- S4 contract refinement candidate list가 준비된다

### 상태

- 완료

## Step 9. Follow-up Priority 정리

### 해야 할 일

- S2 이후 우선순위를 적는다

### 일반 순서

1. `S3 visually similar scene alignment audit`
2. `S4 contract refinement`

### 완료 기준

- S2 이후 바로 다음 단계가 명확히 적혀 있다

### 상태

- 완료

## S2 완료 조건

아래가 충족되면 S2는 완료로 본다.

- leakage candidate가 충분히 수집돼 있다
- 각 case가 runtime row와 연결돼 있다
- family 분류가 돼 있다
- suppression 방향이 정리돼 있다
- `hide / downgrade / reduce` 분류가 있다
- S4 suppression contract candidate list가 있다

현재 판정:

- `S2 1차 구현 = 완료`
- 다음 우선순위는 `S3 visually similar scene alignment audit`
