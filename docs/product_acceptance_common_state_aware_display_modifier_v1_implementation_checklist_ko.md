# Product Acceptance Common State-Aware Display Modifier v1 Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는
`product_acceptance_common_state_aware_display_modifier_v1`
를 실제 작업 순서로 옮긴 구현 체크리스트다.

성격:

- 구현 직전 문서
- PA 메인축의 첫 코드 작업 범위를 고정하는 실행용 체크리스트
- `상세 reference -> 구현 체크리스트 -> 구현 memo` 흐름을 남기기 위한 로그 문서

## 선행 문서

- [state_forecast_product_acceptance_handoff_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\state_forecast_product_acceptance_handoff_ko.md)
- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)
- [product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_detailed_reference_ko.md)

## 이번 단계 목표

이번 단계의 목표는 아래 하나다.

```text
chart acceptance의 scene 의미 owner와 display modifier owner를 분리하고,
BF bridge를 공통 state-aware display modifier 입력으로 올린다.
```

이번 단계에서 같이 하지 않는 것:

- entry acceptance 조정
- wait / hold acceptance 조정
- exit acceptance 조정
- broad raw add
- broad collector rebuild
- symbol별 ad hoc 예외 확장

## 작업 순서

### Step 0. PA0 baseline/casebook 기준선 먼저 고정

목표:

- 이후 modifier 작업이 추상 조정이 아니라 casebook 기준 작업이 되게 만든다

작업:

- 최근 chart snapshot / entry rows / exit rows 기준 소스를 다시 묶는다
- must-show / must-hide 기준 케이스를 우선 chart acceptance 기준으로 정리한다
- 이미 있는 NAS / XAU / BTC casebook 문서와 이번 공통 modifier 범위를 분리해서 본다

주 대상 자료:

- [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [runtime_status.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [chart_flow_distribution_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)

완료 조건:

- must-show / must-hide 기준이 코드 조정 전에 다시 고정된다

기준 문서:

- [product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md)
- [product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_implementation_checklist_ko.md)

### Step 1. `consumer_check_state.py`에서 scene baseline helper를 먼저 분리

목표:

- scene 의미 계산과 modifier 적용을 같은 블록에서 동시에 하지 않게 만든다

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 에서
  baseline scene snapshot 계산 helper를 분리한다
- 이 helper는 아래까지만 책임지게 만든다
  - `check_candidate`
  - `check_side`
  - baseline `check_stage`
  - `entry_ready`
  - hard/soft block baseline reason
- `display_score` / `display_repeat_count` 최종 계산은 modifier 적용 이후로 밀어낸다

완료 조건:

- scene owner path와 modifier path가 함수 경계상 구분된다

### Step 2. common modifier contract를 policy에 고정

목표:

- modifier가 임시 if-branch 집합이 아니라 공통 policy read path를 갖게 만든다

작업:

- [chart_flow_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_flow_policy.py) 에
  `display_modifier` 또는 동등한 policy section을 추가한다
- 아래 항목을 policy에서 읽을 수 있게 만든다
  - awareness preserve floor
  - continuation / chop / conflict soft cap
  - score floor / cap
  - repeat tempering thresholds
  - modifier debug contract version

완료 조건:

- modifier 기준이 consumer 내부 하드코딩에서 조금이라도 분리된다

### Step 3. BF bridge read path를 modifier 정식 입력으로 올리기

목표:

- BF1이 point fix가 아니라 modifier input root가 되게 만든다

작업:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 의
  `_act_wait_bridge_from_payload_v1(...)`를 modifier input builder로 승격한다
- 첫 구현에서는 BF1을 필수 입력으로 사용한다
- BF2~BF5는 optional hook만 열어 둔다
- modifier reason/debug surface가 어떤 bridge를 읽었는지 남기게 만든다

완료 조건:

- `bf1_awareness_keep` 단일 point fix 구조에서 한 단계 올라와,
  modifier 입력 계약이 분명해진다

### Step 4. effective display surface 계산 helper를 별도로 만든다

목표:

- final `display_ready / stage / score / repeat_count`가 modifier 적용 결과로 읽히게 만든다

작업:

- baseline scene snapshot + modifier inputs를 받아
  effective display surface를 계산하는 helper를 추가한다
- 최소 아래 출력이 한 곳에서 계산되게 만든다
  - `effective_display_ready`
  - `effective_stage`
  - `effective_display_strength_level`
  - `effective_display_score`
  - `effective_display_repeat_count`
- 첫 구현에서는 기존 `consumer_check_state_v1` 필드를 유지하되,
  내부 계산 경로만 분리한다

완료 조건:

- chart acceptance final surface가 “scene baseline + modifier 적용” 형태로 설명 가능해진다

### Step 5. symbol override를 threshold/relief axis로만 남기기

목표:

- symbol tuning이 meaning override처럼 보이지 않게 만든다

작업:

- [chart_symbol_override_policy.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_symbol_override_policy.py) 기준으로
  symbol별 차이가 threshold / relief / tolerance 범위인지 확인한다
- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py) 안의
  symbol-specific display relief/suppression 중
  policy axis로 옮길 수 있는 것은 분리 후보로 표시한다
- 이번 단계에서는 전부 옮기려 하지 말고,
  hold-out list를 남겨도 된다

완료 조건:

- symbol별 차이가 왜 있는지 설명 경계가 선명해진다

### Step 6. painter는 passive reader인지 회귀 확인

목표:

- painter가 다시 의미 owner로 번지지 않게 한다

작업:

- [chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py) 가
  최종 `consumer_check_state_v1` surface를 읽는 passive reader인지 확인한다
- 이번 단계에서 painter 의미 결정 로직을 같이 확장하지 않는다

완료 조건:

- 변경의 중심이 consumer/modifier path에 머문다

### Step 7. 테스트 고정점 잠그기

우선 확인 테스트:

- [test_consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_consumer_check_state.py)
- [test_chart_painter.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_chart_painter.py)

특히 다시 확인할 포인트:

- BF1 awareness preserve 계약
- `check_stage` / `check_display_ready` 회귀
- `display_repeat_count` 회귀
- painter가 consumer state를 올바른 event kind로 번역하는지
- symbol override scene toggle 회귀

완료 조건:

- owner split 이후에도 기존 must-show / must-hide 성격이 크게 깨지지 않는다

### Step 8. 구현 직후 memo 남기기

목표:

- 다음 스레드에서도 작업 의도와 범위를 바로 읽게 만든다

작업:

- 구현이 끝나면 `implementation_memo` 문서를 별도로 남긴다
- 구현 결과 memo: [product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_common_state_aware_display_modifier_v1_implementation_memo_ko.md)
- 아래를 꼭 적는다
  - 어떤 owner를 건드렸는지
  - 어떤 contract를 추가/분리했는지
  - 무엇은 이번 단계에 일부러 안 했는지
  - 어떤 테스트를 돌렸는지
  - 다음 reopen point가 무엇인지

완료 조건:

- `상세 -> 체크리스트 -> 구현 memo` 흐름이 PA에서도 끊기지 않는다

## 구현 중 금지사항

- scene meaning을 modifier가 새로 만들지 않는다
- side/candidate를 modifier가 뒤집지 않는다
- symbol별 ad hoc 예외를 먼저 더 쌓지 않는다
- painter에서 의미 보정을 다시 시작하지 않는다
- entry / wait / exit acceptance까지 한 번에 같이 건드리지 않는다

## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. scene baseline 계산과 modifier 적용 경로가 코드상 분리된다
2. BF1 bridge가 modifier 정식 입력으로 올라온다
3. `consumer_check_state_v1`가 modifier debug surface를 남긴다
4. symbol override 경계가 threshold/relief 중심으로 정리된다
5. 관련 테스트가 회귀 없이 유지된다
6. 구현 memo가 추가된다

## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. PA1 chart acceptance casebook 재리뷰
2. PA2 entry acceptance 재정렬
3. PA3 wait / hold acceptance 재정렬
4. PA4 exit acceptance 재정렬
