# D2 Rejection 분리 규칙 실행 로드맵

## 목표

rejection을 `FRICTION_REJECTION`과 `REVERSAL_REJECTION`으로 분리하는 공용 계약을
문서, 코드, runtime detail, shadow artifact까지 같은 언어로 고정한다.

이번 단계는 rule implementation이며,
기존 dominance 계산/행동 로직 변경은 포함하지 않는다.

---

## R1. contract 정의

핵심 작업:

- `rejection_type_enum_v1` 정의
- `rejection_consumption_role_enum_v1` 정의
- field catalog 정의
- classification rule, control rule, dominance protection rule 고정

완료 기준:

- `rejection_split_rule_contract_v1`가 코드와 문서에서 동일하게 정의됨

---

## R2. summary / artifact 생성

핵심 작업:

- `rejection_split_rule_summary_v1` 생성
- JSON/Markdown artifact 생성

완료 기준:

- `rejection_split_rule_latest.json`
- `rejection_split_rule_latest.md`

가 정상 생성됨

---

## R3. runtime detail export 연결

핵심 작업:

- `trading_application.py`에서 D2 report generation 연결
- `runtime_status.detail.json`에 contract/summary/artifact path surface

완료 기준:

- detail payload에서 D2 contract와 summary가 읽힘

---

## R4. 테스트 잠금

핵심 작업:

- contract 단위 테스트
- artifact 생성 테스트
- runtime export 테스트

완료 기준:

- D2 대상 pytest 통과
- `py_compile` 통과

---

## 하지 말아야 할 것

- 아직 row-level rejection classification을 dominance 계산에 직접 반영하지 않는다
- `rejection split`이 `dominant_side`를 바꾸게 하지 않는다
- 단일 `upper_reject`, `soft_block`, `wait_bias`를 reversal override로 승격하지 않는다
- execution/state25 변경 로직을 붙이지 않는다

---

## 최종 완료 기준

- `rejection_split_rule_contract_v1`
- `rejection_split_rule_summary_v1`
- `rejection_split_rule_artifact_paths`

가 runtime detail에서 공통 surface되고,
shadow artifact도 정상 생성되며,
dominance ownership은 계속 보호된다.
