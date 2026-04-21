# D3 continuation stage 분해 실행 로드맵

## 목표

continuation 내부를 `INITIATION / ACCEPTANCE / EXTENSION`으로 분리하는 공용 계약을
문서, 코드, runtime detail, shadow artifact까지 같은 언어로 고정한다.

이번 단계는 continuation stage rule implementation이며,
기존 dominance 계산/행동 로직 변경은 포함하지 않는다.

---

## R1. contract 정의

핵심 작업:

- `continuation_stage_enum_v1` 정의
- stage 판단 재료 정의
- field catalog 정의
- classification rule, control rule, dominance protection rule 고정

완료 기준:

- `continuation_stage_contract_v1`가 코드와 문서에서 동일하게 정의됨

---

## R2. summary / artifact 생성

핵심 작업:

- `continuation_stage_summary_v1` 생성
- JSON/Markdown artifact 생성

완료 기준:

- `continuation_stage_latest.json`
- `continuation_stage_latest.md`

가 정상 생성됨

---

## R3. runtime detail export 연결

핵심 작업:

- `trading_application.py`에서 D3 report generation 연결
- `runtime_status.detail.json`에 contract/summary/artifact path surface

완료 기준:

- detail payload에서 D3 contract와 summary가 읽힘

---

## R4. 테스트 잠금

핵심 작업:

- contract 단위 테스트
- artifact 생성 테스트
- runtime export 테스트

완료 기준:

- D3 대상 pytest 통과
- `py_compile` 통과

---

## 하지 말아야 할 것

- 아직 row-level continuation stage classification을 dominance 계산에 직접 반영하지 않는다
- continuation stage가 `dominant_side`를 바꾸게 하지 않는다
- `EXTENSION`을 곧바로 reversal evidence로 취급하지 않는다
- texture를 stage처럼 계산하지 않는다
- execution/state25 변경 로직을 붙이지 않는다

---

## 최종 완료 기준

- `continuation_stage_contract_v1`
- `continuation_stage_summary_v1`
- `continuation_stage_artifact_paths`

가 runtime detail에서 공통 surface되고,
shadow artifact도 정상 생성되며,
stage는 시간 위치이고 texture는 실행 품질이라는 규칙이 계속 보호된다.
