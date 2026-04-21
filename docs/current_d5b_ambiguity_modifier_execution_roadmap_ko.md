# D5b ambiguity modifier 실행 로드맵

## 목표

애매한 장면을 `LOW / MEDIUM / HIGH` ambiguity로 분리해 boundary/caution 조정축으로 남기는 공용 계약을
문서, 코드, runtime detail, shadow artifact까지 같은 언어로 고정한다.

이번 단계는 ambiguity modifier rule implementation이며,
기존 dominance 계산/행동 로직 변경은 포함하지 않는다.

---

## R1. contract 정의

핵심 작업:

- `ambiguity_level_enum_v1` 정의
- ambiguity source 정의
- field catalog 정의
- classification rule, control rule, dominance protection rule 고정

완료 기준:

- `ambiguity_modifier_contract_v1`가 코드와 문서에서 동일하게 정의됨

---

## R2. summary / artifact 생성

핵심 작업:

- `ambiguity_modifier_summary_v1` 생성
- JSON/Markdown artifact 생성

완료 기준:

- `ambiguity_modifier_latest.json`
- `ambiguity_modifier_latest.md`

가 정상 생성됨

---

## R3. runtime detail export 연결

핵심 작업:

- `trading_application.py`에서 D5b report generation 연결
- `runtime_status.detail.json`에 contract/summary/artifact path surface

완료 기준:

- detail payload에서 D5b contract와 summary가 읽힘

---

## R4. 테스트 잠금

핵심 작업:

- contract 단위 테스트
- artifact 생성 테스트
- runtime export 테스트

완료 기준:

- D5b 대상 pytest 통과
- `py_compile` 통과

---

## 하지 말아야 할 것

- 아직 row-level ambiguity calculation을 dominance 계산에 직접 반영하지 않는다
- `HIGH ambiguity`를 friction이나 continuation에 조용히 흡수하지 않는다
- ambiguity modifier가 `dominant_side`를 바꾸게 하지 않는다
- execution/state25 변경 로직을 붙이지 않는다

---

## 최종 완료 기준

- `ambiguity_modifier_contract_v1`
- `ambiguity_modifier_summary_v1`
- `ambiguity_modifier_artifact_paths`

가 runtime detail에서 공통 surface되고,
shadow artifact도 정상 생성되며,
ambiguity는 boundary/caution 조정용 modifier이고 dominance 보호 규칙 아래에 있다는 점이 계속 유지된다.
