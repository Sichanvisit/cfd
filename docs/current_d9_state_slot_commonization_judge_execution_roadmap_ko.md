# D9. 공용화 판정 실행 로드맵

## 목표

XAU pilot 결과를 기반으로 decomposition slot을 공용화 가능한지 판정하는 summary 층을 만든다.

## 작업 순서

### 1. contract 추가

- `state_slot_commonization_judge_contract_v1`
- verdict enum과 slot judgement field 고정

### 2. XAU pilot / validation 입력 결합

- `xau_pilot_mapping`
- `xau_readonly_surface`
- `xau_decomposition_validation`

세 report를 사용해 slot catalog 생성

### 3. verdict 생성

- `COMMON_READY`
- `COMMON_WITH_SYMBOL_THRESHOLD`
- `XAU_LOCAL_ONLY`
- `HOLD_FOR_MORE_SYMBOLS`

### 4. summary / artifact 추가

- `state_slot_commonization_judge_summary_v1`
- `state_slot_commonization_judge_latest.json`
- `state_slot_commonization_judge_latest.md`

### 5. runtime detail export 연결

- contract / summary / artifact path surface

## 완료 후 기대 상태

- D10에 앞서 어떤 slot이 공용 가능한지 선명하게 분리된다.
