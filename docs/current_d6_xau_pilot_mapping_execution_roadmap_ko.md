# D6 XAU pilot mapping 실행 로드맵

## 목표

XAU retained evidence window를 공용 decomposition 언어로 매핑하는 파일럿 계약을
문서, 코드, runtime detail, shadow artifact까지 같은 언어로 고정한다.

이번 단계는 XAU pilot mapping implementation이며,
기존 dominance 계산/행동 로직 변경은 포함하지 않는다.

---

## R1. pilot window catalog 정의

핵심 작업:

- XAU 상승 recovery core window 고정
- XAU 하락 rejection core window 고정
- linked profile key와 common slot mapping field 정의

완료 기준:

- `pilot_window_catalog_v1`가 코드와 문서에서 동일하게 정의됨

---

## R2. summary / artifact 생성

핵심 작업:

- `xau_pilot_mapping_summary_v1` 생성
- JSON/Markdown artifact 생성

완료 기준:

- `xau_pilot_mapping_latest.json`
- `xau_pilot_mapping_latest.md`

가 정상 생성됨

---

## R3. runtime detail export 연결

핵심 작업:

- `trading_application.py`에서 D6 report generation 연결
- `runtime_status.detail.json`에 contract/summary/artifact path surface

완료 기준:

- detail payload에서 D6 contract와 summary가 읽힘

---

## R4. 테스트 잠금

핵심 작업:

- contract 단위 테스트
- artifact 생성 테스트
- runtime export 테스트

완료 기준:

- D6 대상 pytest 통과
- `py_compile` 통과

---

## 하지 말아야 할 것

- 아직 current row-level XAU slot classifier를 dominance 계산에 직접 반영하지 않는다
- XAU pilot mapping이 `dominant_side`를 바꾸게 하지 않는다
- XAU pilot mapping을 영구 예외 규칙처럼 취급하지 않는다
- execution/state25 변경 로직을 붙이지 않는다

---

## 최종 완료 기준

- `xau_pilot_mapping_contract_v1`
- `xau_pilot_mapping_summary_v1`
- `xau_pilot_mapping_artifact_paths`

가 runtime detail에서 공통 surface되고,
shadow artifact도 정상 생성되며,
XAU는 common frame validation pilot이라는 원칙이 유지된다.
