# F4. Threshold Provisional Band 실행 로드맵

## 1. 목적

F4는 live F2 metrics를 F3 retained threshold profile과 비교해,
현재 row가 provisional band 기준으로 어디까지 올라왔는지를 read-only로 surface하는 단계다.

---

## 2. 진행 원칙

### 원칙 1. structure gate 우선

F1이 막으면 F4도 `STRUCTURE_BLOCKED`다.

### 원칙 2. confirmed/building 분리

- 둘 다 confirmed floor 이상 -> `CONFIRMED_CANDIDATE`
- 하나가 앞서고 다른 하나가 building floor 이상 -> `BUILDING_CANDIDATE`

### 원칙 3. extension cap 유지

`EXTENSION`은 confirmed 상한 금지

### 원칙 4. read-only 유지

execution/state25는 여전히 바꾸지 않는다.

---

## 3. 단계별 로드맵

### F4-1. contract 고정

목적:

- provisional band 해석 필드와 enum을 먼저 고정한다.

핵심 작업:

- `flow_threshold_provisional_band_contract_v1`
- band position enum
- provisional state enum

완료 기준:

- 문서/코드/runtime에서 같은 이름으로 F4를 읽을 수 있다.

### F4-2. conviction band 위치 계산

목적:

- `aggregate_conviction_v1`가 confirmed/building floor 대비 어디 있는지 표준화한다.

핵심 작업:

- `aggregate_conviction_band_position_v1`
- `aggregate_conviction_gap_to_confirmed_v1`
- `aggregate_conviction_gap_to_building_v1`

완료 기준:

- conviction이 band 기준 어디까지 왔는지 숫자와 enum 둘 다 보인다.

### F4-3. persistence band 위치 계산

목적:

- `flow_persistence_v1`가 confirmed/building floor 대비 어디 있는지 표준화한다.

핵심 작업:

- `flow_persistence_band_position_v1`
- `flow_persistence_gap_to_confirmed_v1`
- `flow_persistence_gap_to_building_v1`

완료 기준:

- persistence가 band 기준 어디까지 왔는지 숫자와 enum 둘 다 보인다.

### F4-4. provisional candidate state 결정

목적:

- conviction/persistence 위치 + structure gate + extension cap을 합쳐 provisional state를 만든다.

핵심 작업:

- `STRUCTURE_BLOCKED`
- `CONFIRMED_CANDIDATE`
- `BUILDING_CANDIDATE`
- `UNCONFIRMED_CANDIDATE`

분류 규칙 적용

완료 기준:

- 같은 row에서 왜 confirmed/building/unconfirmed인지 설명 가능하다.

### F4-5. summary / artifact 생성

목적:

- live 분포를 symbol별로 빠르게 점검할 수 있게 만든다.

핵심 작업:

- state count summary
- conviction band position count summary
- persistence band position count summary
- threshold profile count summary

완료 기준:

- artifact만 봐도 어떤 symbol이 band에 도달했는지 읽을 수 있다.

### F4-6. runtime export 연결

목적:

- F4 contract/summary/artifact를 runtime detail에 export한다.

핵심 작업:

- `trading_application.py` import
- report init
- attach/generate 순서 추가
- detail payload export

완료 기준:

- runtime detail에 F4 contract/summary/artifact가 보인다.

### F4-7. 테스트 고정

목적:

- F4가 structure-first 권한을 깨지 않는지 확인한다.

핵심 테스트:

- blocked row -> `STRUCTURE_BLOCKED`
- eligible strong row -> `CONFIRMED_CANDIDATE`
- eligible/weak mixed row -> `BUILDING_CANDIDATE`
- extension row -> confirmed cap 적용
- artifact write
- runtime export

완료 기준:

- 단위 테스트와 runtime export 테스트 통과

---

## 4. 산출물

문서:

- `current_f4_flow_threshold_provisional_band_detailed_plan_ko.md`
- `current_f4_flow_threshold_provisional_band_execution_roadmap_ko.md`

코드:

- `backend/services/flow_threshold_provisional_band_contract.py`

테스트:

- `tests/unit/test_flow_threshold_provisional_band_contract.py`
- `tests/unit/test_trading_application_runtime_status.py` 보강

artifact:

- `data/analysis/shadow_auto/flow_threshold_provisional_band_latest.json`
- `data/analysis/shadow_auto/flow_threshold_provisional_band_latest.md`

---

## 5. 다음 단계 연결

F4가 끝나면 다음은 자연스럽게 아래 순서다.

1. F5
   exact pilot match를 hard gate에서 bonus로 재배치

2. F6 이후
   XAU/NAS/BTC shadow canary와 lifecycle에 calibrated band 연결

즉 F4는 threshold 자체를 final truth로 박는 단계가 아니라,
"retained anchor 기준으로 current row가 어디까지 왔는지"를 operational하게 surface하는 단계다.
