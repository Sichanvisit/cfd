# F1. `flow_structure_gate_v1` 실행 로드맵

## F1-1. 계약 정의

목적:

- flow structure gate를 공용 contract로 고정한다.

작업:

- `flow_structure_gate_contract_v1`
- state enum
  - `ELIGIBLE / WEAK / INELIGIBLE / NOT_APPLICABLE`
- hard disqualifier enum
- primary reason enum

완료 기준:

- 문서와 코드가 같은 상태/이유 언어를 본다.

## F1-2. upstream ensure 경로 고정

목적:

- F1가 의존하는 common slot/local structure/dominance 재료를 같은 경로로 불러오게 한다.

작업:

- `state_slot_symbol_extension_surface`
  를 기준 upstream으로 사용
- row에 common slot이 없으면 extension surface attach

완료 기준:

- XAU/NAS/BTC 모두 slot core와 local structure 재료를 읽을 수 있다.

## F1-3. hard disqualifier 구현

목적:

- directional flow 후보 자격을 즉시 박탈하는 조건을 먼저 고정한다.

작업:

- `UNMAPPED_SLOT`
- `POLARITY_MISMATCH`
- `REVERSAL_REJECTION`
- `REVERSAL_OVERRIDE`
- `AMBIGUITY_HIGH`

완료 기준:

- 하드 탈락은 숫자나 추가 soft score와 무관하게 먼저 판정된다.

## F1-4. soft qualifier 구현

목적:

- directional flow 후보 자격의 강도를 판단한다.

작업:

- stage
- tempo
- breakout hold
- structure bias
- swing intact
- body drive

완료 기준:

- hard fail이 없을 때 `ELIGIBLE / WEAK / INELIGIBLE`를 soft score로 재현 가능하다.

## F1-5. extension 상한 고정

목적:

- late continuation이 fresh directional candidate처럼 승격되지 않게 막는다.

작업:

- `stage == EXTENSION`이면 기본적으로 `WEAK` 상한

완료 기준:

- extension row는 hard fail이 아니어도 기본적으로 fresh eligible이 되지 않는다.

## F1-6. row-level surface 생성

목적:

- gate 판정과 이유를 runtime row에서 바로 읽게 한다.

작업:

- profile 생성
- gate state
- hard/soft 이유
- slot/stage/rejection/tempo/ambiguity surface

완료 기준:

- row 하나만 봐도 왜 `ELIGIBLE`, `WEAK`, `INELIGIBLE`인지 설명 가능하다.

## F1-7. summary / artifact 연결

목적:

- F1 결과를 shadow artifact와 runtime detail에 올린다.

작업:

- summary 생성
- markdown/json artifact write
- runtime detail export

완료 기준:

- `flow_structure_gate_contract_v1`
- `flow_structure_gate_summary_v1`
- `flow_structure_gate_artifact_paths`
  가 runtime detail에 보인다.

## F1-8. 테스트 잠금

목적:

- 구조 gate regression을 방지한다.

작업:

- contract 테스트
- eligible case 테스트
- hard fail case 테스트
- extension/weak case 테스트
- runtime export 테스트

완료 기준:

- unit test 통과
- runtime export test 통과
