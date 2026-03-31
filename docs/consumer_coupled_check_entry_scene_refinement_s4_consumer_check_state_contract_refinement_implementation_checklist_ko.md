# Consumer-Coupled Check/Entry Scene Refinement
## S4. Consumer Check State Contract Refinement Implementation Checklist

### 목표

S1/S2/S3에서 정리된 사례를 실제 `consumer_check_state_v1` 규칙으로 반영하고,
scene family별 stage/display 계약을 더 일관되게 만든다.

### 현재 상태

- `Step 1 ~ Step 11`: 구현/테스트/재관측/memo까지 1차 완료
- latest runtime window에서 `BTC suppression`은 직접 확인
- `NAS downgrade`, `XAU reconciliation`은 direct test로는 잠겼고 runtime exact family 재등장은 추가 관찰 권장

## Step 1. Input Casebook Freeze

### 해야 할 일

- 아래 입력 문서를 최종 입력으로 고정한다

### 입력 문서

- `consumer_coupled_check_entry_scene_refinement_s1_must_show_scene_casebook_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s2_must_hide_scene_casebook_ko.md`
- `consumer_coupled_check_entry_scene_refinement_s3_visually_similar_scene_alignment_audit_ko.md`

### 완료 기준

- 어떤 case가 이번 S4에 들어오는지 범위가 명확하다

## Step 2. Contract Candidate Inventory

### 해야 할 일

- S1/S2/S3 candidate를 한 표로 합친다

### 항목

- family
- current stage
- current display
- desired action
- owner file

### 완료 기준

- contract candidate inventory가 완성된다

## Step 3. Global vs Symbol-Specific 분리

### 해야 할 일

- candidate를 공통 규칙과 symbol 예외로 나눈다

### 예시

- 공통:
  - blocked confirm hidden rule
  - weak structural observe translation
- 심볼 예외:
  - BTC lower buy cadence suppression
  - XAU upper reject family reconciliation

### 완료 기준

- 공통 규칙과 예외 규칙 경계가 명확해진다

## Step 4. BTC Suppression Rule 설계

### 해야 할 일

- `BTC lower structural observe`에 대한 suppression 규칙을 정한다

### 핵심 질문

- 반복 run에서 hide할지
- 첫 1회만 남길지
- cadence window를 둘지

### 완료 기준

- BTC suppression rule이 정리된다

## Step 5. NAS Downgrade Rule 설계

### 해야 할 일

- `NAS lower rebound probe`를 `PROBE -> OBSERVE`로 내릴지 규칙화한다

### 핵심 질문

- 어떤 blocked/probe 조합에서 downgrade할지
- score/repeat를 어디까지 내릴지

### 완료 기준

- NAS downgrade rule이 정리된다

## Step 6. XAU Reconciliation Rule 설계

### 해야 할 일

- `XAU middle anchor cadence reduction`
- `XAU upper reject family reconciliation`
를 나눠서 정리한다

### 핵심 질문

- middle anchor는 cadence만 줄일지
- upper reject confirm은 weak observe로 남길지

### 완료 기준

- XAU rule이 정리된다

## Step 7. Late Reconciliation Boundary 정리

### 해야 할 일

- late block가 어떤 경우에 stage/display를 덮어쓸 수 있는지 정리한다

### 완료 기준

- `entry_service`와 `entry_try_open_entry`의 경계가 명확해진다

## Step 8. Code Implementation

### 해야 할 일

- owner 파일에 실제 contract를 반영한다

### 주 대상 파일

- `backend/services/consumer_check_state.py`
- `backend/services/entry_service.py`
- `backend/services/entry_try_open_entry.py`
- 필요 시 `backend/trading/chart_painter.py`

### 완료 기준

- contract가 코드에 반영된다

## Step 9. Regression Test

### 해야 할 일

- stage/display/late-block 관련 테스트를 보강한다

### 우선 대상

- `tests/unit/test_entry_service_guards.py`
- `tests/unit/test_chart_painter.py`
- `tests/unit/test_entry_try_open_entry_probe.py`
- `tests/unit/test_entry_try_open_entry_policy.py`

### 완료 기준

- 핵심 regression이 테스트로 잠긴다

## Step 10. Runtime Re-Observe

### 해야 할 일

- 재시작 후 recent row를 다시 관찰한다

### 확인 포인트

- BTC leakage 감소
- NAS probe downgrade 반영
- XAU family inconsistency 감소

### 완료 기준

- 수정이 실제 runtime에도 반영된다

## Step 11. Reconfirm Memo 작성

### 해야 할 일

- S4 변경 결과를 memo 문서로 정리한다

### 필수 섹션

- changed contract
- expected effect
- runtime result
- residual issue

### 완료 기준

- 다음 S5가 바로 이어질 수 있다

## S4 완료 조건

아래가 충족되면 S4를 완료로 본다.

- casebook candidate가 contract rule로 변환됐다
- code owner에 반영됐다
- regression test가 있다
- runtime re-observe가 됐다
- reconfirm memo가 있다
