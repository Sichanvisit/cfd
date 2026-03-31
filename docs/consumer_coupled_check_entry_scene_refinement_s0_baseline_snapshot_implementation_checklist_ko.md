# Consumer-Coupled Check/Entry Scene Refinement
## S0. Baseline Snapshot Implementation Checklist

### 목표

`BTCUSD / NAS100 / XAUUSD`의 현재 `consumer_check_state_v1`와 chart display 상태를
recent row 기준으로 동결하고,
이후 S1/S2/S3 refinement의 출발점으로 사용할 baseline snapshot을 만든다.

## 현재 상태

- `Step 1 ~ Step 8`: 완료
- `Step 9`: 로드맵 원문 인코딩 이슈로 보류

현재 S0 baseline 산출물은 아래 문서에 정리돼 있다.

- `consumer_coupled_check_entry_scene_refinement_s0_baseline_snapshot_spec_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s0_baseline_snapshot_memo_ko.md`

즉 S0의 실질 구현은 완료로 보고,
로드맵 sync는 후속 문서 정리 시점에 함께 반영한다.

## Step 1. Input Snapshot Freeze

### 해야 할 일

- 최근 기준 관찰 대상 파일을 고정한다
- baseline을 뽑는 시각을 기록한다
- 아래 입력 파일의 latest 상태를 확인한다

### 대상 파일

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`
- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`

### 완료 기준

- baseline snapshot의 기준 시각과 입력 파일 기준이 명확히 남는다

### 상태

- 완료

## Step 2. Tri-Symbol Recent Row Snapshot

### 해야 할 일

- `BTCUSD / NAS100 / XAUUSD` 각각 최근 row를 일정 개수 수집한다
- 최소 아래 항목을 같이 비교한다

### 필수 항목

- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `probe_scene_id`
- `consumer_check_stage`
- `consumer_check_side`
- `consumer_check_display_ready`
- `consumer_check_display_score`
- `consumer_check_display_repeat_count`
- `entry_ready`
- `action`
- `box_state`
- `bb_state`

### 완료 기준

- 세 심볼 recent row를 같은 포맷으로 비교할 수 있다

### 상태

- 완료

## Step 3. Stage Density Snapshot

### 해야 할 일

- 세 심볼 각각에서
  - `BLOCKED`
  - `OBSERVE`
  - `PROBE`
  - `READY`
  의 밀도를 요약한다
- `display_ready=true/false` 비율도 같이 본다

### 완료 기준

- 어떤 심볼이 지나치게 눌려 있고
- 어떤 심볼이 지나치게 많이 뜨는지
를 stage 기준으로 설명할 수 있다

### 상태

- 완료

## Step 4. Display Ladder Snapshot

### 해야 할 일

- `display_score`
- `display_repeat_count`
- `consumer_check_stage`
간의 실제 매핑을 최근 row 기준으로 요약한다

### 확인 포인트

- `OBSERVE`가 주로 1개 체크 밴드에 머무는가
- `PROBE`가 주로 2개 체크 밴드에 머무는가
- `READY`가 주로 3개 체크 밴드에 머무는가
- 예외 케이스가 있는가

### 완료 기준

- 현재 ladder가 실제 row에서 어떻게 쓰이는지 설명할 수 있다

### 상태

- 완료

## Step 5. Must-Show Missing Candidate Collection

### 해야 할 일

- 사용자가 보기엔 “떠야 했는데 안 뜬다”고 느끼는 장면 후보를 모은다
- 각 후보마다 아래를 남긴다

### 필수 기록

- symbol
- decision_time
- 차트상 장면 요약
- 내부 `observe_reason`
- `blocked_by`
- `consumer_check_display_ready`
- 왜 must-show missing 후보로 보는지

### 완료 기준

- 최소 대표 후보 3건 이상 확보

### 상태

- 부분 완료
- 이번 baseline에서는 recent data-only 기준 고신뢰 자동 후보가 충분히 모이지 않아,
  screenshot/manual casebook이 S1에서 보강되어야 한다

## Step 6. Must-Hide Leakage Candidate Collection

### 해야 할 일

- 사용자가 보기엔 “뜨면 안 되는데 뜬다”고 느끼는 장면 후보를 모은다
- 각 후보마다 아래를 남긴다

### 필수 기록

- symbol
- decision_time
- 차트상 장면 요약
- 내부 `observe_reason`
- `blocked_by`
- `consumer_check_stage`
- `consumer_check_display_ready`
- 왜 leakage 후보로 보는지

### 완료 기준

- 최소 대표 후보 3건 이상 확보

### 상태

- 완료
- `BTCUSD`, `NAS100`의 `lower_rebound_probe_observe + barrier_guard + probe_not_promoted`가
  대표 leakage 후보로 정리됐다

## Step 7. Visually Similar Divergence Seed Collection

### 해야 할 일

- 차트상으로는 유사해 보이는데
  내부에선 다른 side/scene/stage로 갈라진 사례를 모은다

### 예시 축

- `BTC vs NAS`
- `BTC vs XAU`
- `NAS vs XAU`

### 필수 기록

- 비교 대상 2개 이상
- 차트상 유사성 요약
- 내부 분기 차이
- divergence 원인 후보

### 완료 기준

- S3 alignment audit로 바로 넘길 seed list가 준비된다

### 상태

- 완료
- `BTC/NAS lower rebound family` vs `XAU conflict family` seed를 확보했다

## Step 8. Baseline Memo 작성

### 해야 할 일

- S0 결과를 memo 문서로 정리한다
- 아래를 반드시 포함한다

### 필수 섹션

- baseline 시각
- tri-symbol recent summary
- stage density summary
- display ladder summary
- must-show missing 후보
- must-hide leakage 후보
- divergence seed
- 다음 단계 우선순위

### 완료 기준

- S1/S2/S3가 이 memo를 baseline으로 바로 출발할 수 있다

### 상태

- 완료

## Step 9. Master Roadmap Sync

### 해야 할 일

- `consumer_coupled_check_entry_scene_refinement_roadmap_ko.md`에
  S0 상태를 반영한다
- 다음 active step을 명확히 적는다

### 완료 기준

- 로드맵 기준 현재 위치가 S0 완료 또는 진행중으로 명확히 보인다

### 상태

- 보류
- 원문 로드맵 파일 인코딩 이슈로 직접 sync는 잠시 미뤘다
- 대신 S0 memo와 checklist 현재 상태에 완료 여부를 명시했다

## S0 완료 조건

아래가 충족되면 S0를 완료로 본다.

- tri-symbol recent row snapshot이 있다
- stage density snapshot이 있다
- display ladder snapshot이 있다
- must-show missing 후보가 정리돼 있다
- must-hide leakage 후보가 정리돼 있다
- visually similar divergence seed가 정리돼 있다
- baseline memo와 master roadmap sync가 끝났다

현재 판정:

- `S0 실질 구현 = 완료`
- `로드맵 sync = 후속 문서 정리 시점 보완`
