# Product Acceptance PA0 Baseline Freeze and Target Capture Implementation Checklist

작성일: 2026-03-31 (KST)

## 목적

이 문서는
`PA0 baseline freeze and target capture`
를 실제 작업 순서로 옮긴 구현 체크리스트다.

성격:

- 구현 직전 문서
- baseline capture 범위를 고정하는 실행용 체크리스트
- 이후 PA1~PA4가 참조할 latest 산출물을 남기기 위한 작업 문서

## 선행 문서

- [product_acceptance_reorientation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_detailed_reference_ko.md)
- [product_acceptance_reorientation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_reorientation_execution_roadmap_ko.md)
- [product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\product_acceptance_pa0_baseline_freeze_and_target_capture_detailed_reference_ko.md)

## 이번 단계 목표

이번 단계의 목표는 아래 하나다.

```text
PA1~PA4가 흔들리지 않게, tri-symbol chart / entry / exit baseline과 casebook seed queue를 latest 산출물로 고정한다.
```

이번 단계에서 하지 않는 것:

- scene 수정
- modifier 도입
- symbol override 조정
- entry / wait / exit threshold 조정
- painter visual 조정

## 작업 순서

### Step 1. 입력 source와 canonical field 경계 고정

목표:

- baseline script가 어떤 데이터를 어디서 읽는지 흔들리지 않게 만든다

작업:

- 아래 source를 PA0 canonical source로 고정한다
  - [entry_decisions.csv](C:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
  - [runtime_status.json](C:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
  - [chart_flow_distribution_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
  - [trade_closed_history.csv](C:\Users\bhs33\Desktop\project\cfd\trade_closed_history.csv)
- entry row는 `consumer_check_state_v1` nested contract를 우선 읽는다
- closed trade row는 `net_pnl_after_cost`, `giveback_usd`, `post_exit_mfe`, `wait_quality_label`, `loss_quality_label`를 우선 읽는다

완료 조건:

- baseline script가 참조하는 입력 경계가 문서와 코드에서 일치한다

### Step 2. recent tri-symbol row freeze 로직 구현

목표:

- 최근 row를 심볼별로 같은 기준으로 비교 가능하게 만든다

작업:

- `entry_decisions.csv`에서 심볼별 recent row window를 수집한다
- 심볼별로 아래 baseline summary를 만든다
  - recent row count
  - stage counts
  - display ready ratio
  - top observe / blocked / non-action reasons
  - display score / repeat count ladder
- `chart_flow_distribution_latest.json`와 합쳐 chart density snapshot을 남긴다

완료 조건:

- tri-symbol baseline summary가 latest report에 포함된다

### Step 3. chart / entry casebook seed queue 구현

목표:

- PA1 / PA2에서 바로 쓸 대표 후보를 latest report에 남긴다

작업:

- 아래 seed list를 생성한다
  - `must-show missing`
  - `must-hide leakage`
  - `must-enter candidate`
  - `must-block candidate`
- 각 후보는 최소 아래 필드를 남긴다
  - symbol
  - time
  - observe_reason
  - blocked_by
  - action_none_reason
  - probe_scene_id
  - check_stage
  - display_ready
  - display_score
  - ranking score / seed reason

완료 조건:

- chart / entry seed queue가 json/csv/md에 모두 남는다

### Step 4. divergence seed queue 구현

목표:

- visually similar but semantically diverged 사례를 PA1/PA2 재검토용 seed로 남긴다

작업:

- 비슷한 `box_state / bb_state / reason family / probe_scene` 기반으로 row를 묶는다
- 같은 group 안에서 stage/display/side가 갈라지는 사례를 divergence seed로 뽑는다

완료 조건:

- divergence seed list가 latest report에 포함된다

### Step 5. closed trade baseline과 hold / exit seed queue 구현

목표:

- PA3 / PA4가 참고할 closed trade 기준선을 남긴다

작업:

- recent closed trade baseline summary를 심볼별로 만든다
- 아래 seed list를 생성한다
  - `must-hold candidate`
  - `must-release candidate`
  - `good-exit candidate`
  - `bad-exit candidate`
- 각 후보에는 최소 아래를 남긴다
  - symbol
  - open_time / close_time
  - entry_reason / exit_reason
  - net_pnl_after_cost
  - giveback_usd
  - post_exit_mfe
  - wait_quality_label
  - loss_quality_label
  - ranking score / seed reason

완료 조건:

- hold / exit seed queue가 latest report에 포함된다

### Step 6. latest json / csv / markdown writer 추가

목표:

- 다음 단계가 바로 읽을 수 있는 latest artifact를 남긴다

작업:

- 아래 파일을 쓰는 writer를 구현한다
  - `product_acceptance_pa0_baseline_latest.json`
  - `product_acceptance_pa0_baseline_latest.csv`
  - `product_acceptance_pa0_baseline_latest.md`
- markdown에는 quick read summary를 담는다
- csv에는 summary row와 seed queue row를 평탄화해서 넣는다

완료 조건:

- latest 3종 산출물이 일관된 형식으로 생성된다

### Step 7. 테스트 잠그기

우선 확인 테스트:

- 신규 `test_product_acceptance_pa0_baseline_freeze.py`

테스트에서 확인할 것:

- tri-symbol baseline summary 생성
- must-show / must-hide / must-enter / must-block seed 생성
- hold / exit seed 생성
- json/csv/md writer 동작

완료 조건:

- PA0 script contract가 테스트로 고정된다

### Step 8. latest 산출물 실제 생성

목표:

- 문서만 아니라 실제 baseline freeze 결과를 남긴다

작업:

- PA0 script를 현재 데이터에 대해 실행한다
- `data/analysis/product_acceptance` 아래 latest 산출물을 생성한다
- quick read 결과를 implementation memo에 남긴다

완료 조건:

- PA0 latest artifact가 실제 workspace에 남는다

### Step 9. implementation memo 작성

목표:

- 다음 스레드가 바로 이어받을 수 있게 작업 로그를 닫는다

작업:

- 구현 후 `implementation_memo` 문서를 추가한다
- 아래를 적는다
  - 어떤 입력 source를 canonical로 잡았는지
  - 어떤 seed queue를 만들었는지
  - 어떤 heuristic을 썼는지
  - 어떤 테스트를 돌렸는지
  - 다음 reopen point가 무엇인지

완료 조건:

- PA0도 `상세 reference -> 구현 체크리스트 -> 구현 memo` 흐름이 완성된다

## 구현 중 금지사항

- baseline 수집 중에 acceptance rule을 함께 수정하지 않는다
- symbol별 예외를 baseline script 안에서 보정하지 않는다
- raw detector/forecast를 새로 추가하지 않는다
- PA1 modifier 구현을 같은 단계에서 같이 시작하지 않는다

## Done Definition

이번 체크리스트는 아래 조건을 만족하면 완료다.

1. PA0 상세 문서와 스크립트 출력 계약이 일치한다
2. tri-symbol baseline summary가 생성된다
3. chart / entry / hold / exit seed queue가 생성된다
4. json/csv/md latest artifact가 생성된다
5. 테스트가 통과한다
6. implementation memo가 추가된다

## 다음 단계

이 체크리스트가 끝나면 다음으로 넘어간다.

1. PA1 chart acceptance casebook review
2. `product_acceptance_common_state_aware_display_modifier_v1` 구현 착수
