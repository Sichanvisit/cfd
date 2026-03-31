# Shadow Compare Scoreable Transition Coverage Implementation Checklist

## 1. 목적

이 문서는
[refinement_shadow_compare_scoreable_transition_coverage_spec_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_scoreable_transition_coverage_spec_ko.md)
실행 checklist다.

목표는
`production compare replay source`에 future bars를 붙여
transition label이 scoreable해지는지 실제로 확인하는 것이다.

## 2. 이번 단계에서 할 것 / 하지 않을 것

### 할 것

- baseline snapshot 정리
- future bar backed compare source refresh
- shadow compare 재생성
- preview audit 재확인
- 결과 memo 작성

### 하지 않을 것

- target fold 수정
- split health threshold 수정
- chart/runtime rule 수정
- promotion gate 기준 자체 수정

## 3. 입력 기준

- [shadow_compare_production_source_manifest_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\shadow_compare_production_source_manifest_latest.json)
- [semantic_shadow_compare_report_20260326_185628.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_185628.json)
- [semantic_preview_audit_20260326_185716.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_20260326_185716.json)

## 4. 구현 순서

### Step 1. Baseline Snapshot 고정

목표:

- 현재 `future_bar_resolution = none`
- `transition_label_status = INSUFFICIENT_FUTURE_BARS only`
- `scorable_shadow_rows = 0`

를 기준선으로 문서화한다.

### Step 2. Future Bar Refresh 실행

목표:

- [refresh_shadow_compare_production_source.py](c:\Users\bhs33\Desktop\project\cfd\scripts\refresh_shadow_compare_production_source.py)
를 `--fetch-mt5-future-bars`와 함께 실행한다.

완료 기준:

- compare source manifest에 `future_bar_path`가 생긴다.

### Step 3. Shadow Compare 재생성

목표:

- 기본 compare source 기준 latest report를 다시 만든다.

완료 기준:

- 새 report에서 `transition_label_status_counts` 변화 여부를 확인할 수 있다.

### Step 4. Preview Audit 재확인

목표:

- 새 compare report를 preview audit에 반영한다.

완료 기준:

- `shadow_compare warning issues`가 최신 상태로 갱신된다.

### Step 5. 결과 Memo

목표:

- 이번 단계가 실제로 무엇을 바꿨는지 정리한다.

완료 기준:

- 다음 active step이
  - trace quality audit인지
  - compare policy refinement인지
  - 다른 label quality 병목인지
문서만 보고 판단 가능하다.

## 5. Done Definition

다음 중 하나면 이번 단계를 닫는다.

- `future_bar_resolution != none` 이고 `scorable_shadow_rows > 0`
- 혹은 future bars를 붙였는데도 여전히 0이며, 그 다음 병목을 명확히 설명하는 memo가 있다
