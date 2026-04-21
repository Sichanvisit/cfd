# D4 location_context_v1 실행 로드맵

## 목표

같은 signal이라도 어디서 발생했는지를 `IN_BOX / AT_EDGE / POST_BREAKOUT / EXTENDED`로 분리하는 공용 계약을
문서, 코드, runtime detail, shadow artifact까지 같은 언어로 고정한다.

이번 단계는 location context rule implementation이며,
기존 dominance 계산/행동 로직 변경은 포함하지 않는다.

---

## R1. contract 정의

핵심 작업:

- `location_context_enum_v1` 정의
- location 판단 재료 정의
- field catalog 정의
- classification rule, control rule, dominance protection rule 고정

완료 기준:

- `location_context_contract_v1`가 코드와 문서에서 동일하게 정의됨

---

## R2. summary / artifact 생성

핵심 작업:

- `location_context_summary_v1` 생성
- JSON/Markdown artifact 생성

완료 기준:

- `location_context_latest.json`
- `location_context_latest.md`

가 정상 생성됨

---

## R3. runtime detail export 연결

핵심 작업:

- `trading_application.py`에서 D4 report generation 연결
- `runtime_status.detail.json`에 contract/summary/artifact path surface

완료 기준:

- detail payload에서 D4 contract와 summary가 읽힘

---

## R4. 테스트 잠금

핵심 작업:

- contract 단위 테스트
- artifact 생성 테스트
- runtime export 테스트

완료 기준:

- D4 대상 pytest 통과
- `py_compile` 통과

---

## 하지 말아야 할 것

- 아직 row-level location context classification을 dominance 계산에 직접 반영하지 않는다
- `AT_EDGE`만으로 reversal evidence를 만들지 않는다
- `EXTENDED`만으로 reversal evidence를 만들지 않는다
- location context가 `dominant_side`를 바꾸게 하지 않는다
- execution/state25 변경 로직을 붙이지 않는다

---

## 최종 완료 기준

- `location_context_contract_v1`
- `location_context_summary_v1`
- `location_context_artifact_paths`

가 runtime detail에서 공통 surface되고,
shadow artifact도 정상 생성되며,
location context는 modifier이고 dominance 보호 규칙 아래에 있다는 점이 계속 유지된다.
