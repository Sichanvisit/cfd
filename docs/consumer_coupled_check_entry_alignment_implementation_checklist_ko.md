# Consumer-Coupled Check / Entry Alignment Implementation Checklist

## 1. 목표

체크와 진입을 같은 Consumer chain에 묶는다.

즉 이번 구현은:

- chart만 먼저 좋아 보이게 만드는 작업이 아니다
- entry owner를 바꾸는 작업도 아니다
- `Consumer pre-entry state`를 chart와 entry가 공통 소비하게 만드는 작업이다

기준 문서:

- [consumer_coupled_check_entry_alignment_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_spec_ko.md)
- [consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\consumer_coupled_check_entry_alignment_baseline_snapshot_ko.md)

## Current Status

현재 1차 구현으로 아래까지 반영됨:

- Step 1 baseline snapshot
- Step 2 `consumer_check_state_v1` contract
- Step 3 consumer-side display/entry floor
- Step 5 painter translation 연결

다음 실관측 초점:

- NAS100 실제 window에서 `check_display_ready=true`, `entry_ready=false` 케이스가 directional check로 잘 보이는지
- chart/runtime reason 모순이 늘지 않는지


## 2. 구현 순서

### Step 1. Consumer Baseline Snapshot

대상:

- `data/trades/entry_decisions.csv`
- `data/runtime_status.json`

작업:

- NAS100 / BTCUSD / XAUUSD 대표 row를 뽑아
  - `observe_reason`
  - `probe_scene_id`
  - `core_reason`
  - `consumer_guard_result`
  - `blocked_by`
  - `action_none_reason`
  - current chart kind
  를 casebook으로 고정한다.

완료 기준:

- `체크가 안 뜨는 이유`와 `진입이 안 되는 이유`를 같은 row에서 설명 가능하다.

### Step 2. `consumer_check_state_v1` contract 추가

대상:

- `backend/services/entry_service.py`

작업:

- `check_candidate`
- `check_display_ready`
- `entry_ready`
- `check_side`
- `check_stage`
- `check_reason`
- `entry_block_reason`
- `consumer_guard_result`
- `consumer_block_kind`
- `consumer_block_source_layer`
- `display_strength_level`

필드 추가

완료 기준:

- runtime row에 canonical check payload가 남는다.

### Step 3. Consumer-side display/entry floor 계산

대상:

- `backend/services/entry_service.py`

작업:

- 같은 owner에서 `display floor`와 `entry floor`를 계산한다.
- 두 floor 모두 semantic/consumer reason을 그대로 사용한다.

핵심 정책:

- `probe_pair_gap_not_ready`
  - display true / entry false 가능
- `probe_forecast_not_ready`
  - display true / entry false 가능
- generic directional observe
  - explicit probe/confirm surface가 없으면 display false
- `probe_against_default_side`
  - 둘 다 false
- `execution_soft_blocked`
  - display 유지 가능 / entry false
- `policy_hard_blocked`
  - 둘 다 false

완료 기준:

- 같은 row에서 check와 entry의 차이를 한 payload로 읽을 수 있다.

### Step 4. NAS100 1차 scene 적용

대상:

- `backend/services/entry_service.py`

작업:

- `nas_clean_confirm_probe`
- `probe_pair_gap_not_ready`
- `probe_forecast_not_ready`

에 대해 check-first, entry-later 동작을 넣는다.

완료 기준:

- NAS 최신 병목 케이스가 neutral `WAIT`만 남지 않는다.

### Step 5. painter translation 연결

대상:

- `backend/trading/chart_painter.py`

작업:

- `consumer_check_state_v1`가 있으면 chart event 우선 해석
- 없으면 기존 fallback 유지

완료 기준:

- chart와 runtime reason이 같은 payload를 공유한다.

### Step 6. strength / visual 연결

대상:

- `backend/trading/chart_painter.py`
- 필요 시 `backend/trading/chart_flow_policy.py`

작업:

- `OBSERVE` -> 약한 directional wait
- `PROBE` -> probe strength
- `READY` -> ready strength

로 current strength 10단계와 연결

완료 기준:

- check가 먼저 떠도 READY와 체감이 섞이지 않는다.

### Step 7. 회귀 테스트

대상:

- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_chart_painter.py`

작업:

- `consumer_check_state_v1` 생성 테스트
- display/entry floor 분리 테스트
- NAS scene regression
- chart translation regression

완료 기준:

- check-first 연결이 meaning drift 없이 유지된다.

### Step 8. 재관측

대상:

- `data/analysis/chart_flow_distribution_latest.json`
- `data/analysis/chart_flow_rollout_status_latest.json`
- `data/runtime_status.json`
- `data/trades/entry_decisions.csv`

작업:

- NAS100 post-change window 관찰
- BTC/XAU side effect 확인
- Stage E 악화 여부 확인

완료 기준:

- check visibility는 좋아지고, entry false positive는 늘지 않는다.

### Step 9. 후속 확대 여부 결정

작업:

- NAS 안정화 후 BTC/XAU 적용 여부 결정
- ML threshold assist를 same-chain modifier로 연결할지 검토

완료 기준:

- 후속 확장이 문서화된 기준으로 결정된다.

## 3. 우선순위

- `P0`
  - Step 1
  - Step 2
  - Step 3
  - Step 4
- `P1`
  - Step 5
  - Step 6
  - Step 7
- `P2`
  - Step 8
  - Step 9

## 4. 현재 추천 착수점

바로 구현으로 들어가면 첫 코드는 `entry_service.py` 중심이다.

즉 시작 순서는:

1. `Step 1 baseline snapshot`
2. `Step 2 consumer_check_state_v1`
3. `Step 3 consumer-side floor`

가 맞다.
