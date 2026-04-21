# F3. Retained Window Calibration 실행 로드맵

## 1. 목적

F3는 retained pilot windows를 calibration set으로 잠그고, 그 위에 symbol-specific provisional threshold profile을 올리는 단계다.

즉 F3는:

- F2 숫자를 바로 튜닝하지 않고
- 먼저 calibration anchor를 고정하고
- 나중에 F4/F5에서 tuning과 bonus 재배치를 더 안전하게 하도록 준비한다.

---

## 2. 진행 원칙

### 원칙 1. retained window first

band를 먼저 박지 않고, anchor window를 먼저 고정한다.

### 원칙 2. group before threshold

confirmed/building/mixed 분류가 threshold보다 먼저다.

### 원칙 3. structure stays common

구조는 공용으로 유지하고, 숫자 band만 심볼별로 조정한다.

### 원칙 4. provisional not final

F3의 숫자는 최종 확정치가 아니라 provisional band다.

### 원칙 5. read-only 유지

execution/state25는 그대로 건드리지 않는다.

---

## 3. 단계별 로드맵

### F3-1. retained window catalog 통합

목적:

- XAU/NAS/BTC pilot windows를 하나의 calibration catalog로 묶는다.

핵심 작업:

- XAU pilot mapping catalog 읽기
- NAS pilot mapping catalog 읽기
- BTC pilot mapping catalog 읽기
- 공통 retained window schema로 normalize

완료 기준:

- `retained_window_catalog_v1` 하나로 전체 pilot windows를 읽을 수 있다.

### F3-2. retained group 분류 고정

목적:

- 각 retained window를 confirmed/building/mixed/opposed 그룹으로 묶는다.

핵심 작업:

- `CONFIRMED_POSITIVE`
- `BUILDING_POSITIVE`
- `UNCONFIRMED_MIXED`
- `OPPOSED_FALSE`

분류 규칙 정의

완료 기준:

- 각 window가 어느 calibration 역할을 가지는지 명확히 surface된다.

### F3-3. symbol threshold profile 정의

목적:

- 각 symbol별 provisional band 출발점을 고정한다.

핵심 작업:

- `XAU_TUNED`
- `NAS_TUNED`
- `BTC_TUNED`

profile 정의

포함값:

- conviction confirmed/building floor
- persistence confirmed/building floor
- min persisting bars
- exact bonus strength

완료 기준:

- live row에서 symbol별 threshold profile이 바로 읽힌다.

### F3-4. row-level calibration surface 추가

목적:

- 현재 live row가 어떤 threshold profile을 따르는지 metadata로 남긴다.

핵심 작업:

- `flow_threshold_profile_v1`
- `aggregate_conviction_confirmed_floor_v1`
- `aggregate_conviction_building_floor_v1`
- `flow_persistence_confirmed_floor_v1`
- `flow_persistence_building_floor_v1`
- `flow_min_persisting_bars_v1`
- `retained_window_calibration_state_v1`
- `retained_window_calibration_reason_summary_v1`

완료 기준:

- NAS/XAU/BTC row마다 자기 calibration profile을 설명할 수 있다.

### F3-5. summary / artifact 생성

목적:

- retained window 집합 전체를 runtime 밖에서도 검토 가능하게 만든다.

핵심 작업:

- `retained_window_count`
- group count summary
- symbol group count summary
- threshold profile summary

artifact 생성

완료 기준:

- shadow artifact만 봐도 calibration anchor 구조를 읽을 수 있다.

### F3-6. runtime export 연결

목적:

- F3 contract/summary/artifact를 runtime detail에 export한다.

핵심 작업:

- `trading_application.py` import
- report init
- attach/generate 순서 삽입
- detail payload export

완료 기준:

- runtime detail에 F3 contract/summary/artifact가 보인다.

### F3-7. 테스트 고정

목적:

- F3가 단순 문서가 아니라 실제 runtime 계약으로 고정되게 한다.

핵심 테스트:

- contract field exposure
- row-level XAU/NAS/BTC threshold profile attach
- artifact write test
- runtime export test

완료 기준:

- 단위 테스트와 export 테스트 통과

---

## 4. 산출물

문서:

- `current_f3_retained_window_flow_calibration_detailed_plan_ko.md`
- `current_f3_retained_window_flow_calibration_execution_roadmap_ko.md`

코드:

- `backend/services/retained_window_flow_calibration_contract.py`

테스트:

- `tests/unit/test_retained_window_flow_calibration_contract.py`
- `tests/unit/test_trading_application_runtime_status.py` 보강

artifact:

- `data/analysis/shadow_auto/retained_window_flow_calibration_latest.json`
- `data/analysis/shadow_auto/retained_window_flow_calibration_latest.md`

---

## 5. 다음 단계 연결

F3가 끝나면 다음 순서는 자연스럽게 아래로 이어진다.

1. F4
   retained window 분포와 live shadow 분포를 같이 보며 conviction/persistence band 조정

2. F5
   exact pilot match를 bonus로 재배치

3. F6 이후
   XAU/NAS/BTC canary / lifecycle 쪽에 calibrated band를 실제로 연결

즉 F3는 tuning 이전의 anchor-lock 단계다.
