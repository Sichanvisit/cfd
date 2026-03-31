# Shadow Compare Quality Refinement Implementation Checklist

## 1. 목적

이 문서는 [refinement_shadow_compare_quality_refinement_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_quality_refinement_plan_ko.md) 실행 checklist다.

목표는 shadow compare 품질 문제를

- baseline snapshot
- scorable row audit
- trace quality audit
- compare policy refinement
- promotion gate rebind

순서로 정리해서, preview / promotion 판단 근거를 더 믿을 수 있게 만드는 것이다.

## 2. 이번 단계에서 할 것 / 하지 않을 것

### 할 것

- S0 baseline snapshot
- S1 scorable row audit
- shadow compare report에 exclusion taxonomy 추가
- 테스트 보강
- 실제 report 재생성
- 결과 메모 작성

### 하지 않을 것

- timing / entry_quality / exit target 재정의
- split health 수치 변경
- live rollout mode 변경
- chart / execution rule 변경

## 3. 입력 기준

기준 문서:

- [refinement_shadow_compare_quality_refinement_plan_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_quality_refinement_plan_ko.md)
- [refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r3_step7_preview_shadow_compare_reconfirm_memo_ko.md)

중요 파일:

- [shadow_compare.py](c:\Users\bhs33\Desktop\project\cfd\ml\semantic_v1\shadow_compare.py)
- [run_semantic_v1_preview_audit.py](c:\Users\bhs33\Desktop\project\cfd\scripts\run_semantic_v1_preview_audit.py)
- [replay_dataset_builder.py](c:\Users\bhs33\Desktop\project\cfd\backend\trading\engine\offline\replay_dataset_builder.py)

## 4. 구현 순서

### Step 1. S0 Baseline Snapshot 고정

목표:

- latest shadow compare의 warning 상태를 수치와 문장으로 고정한다.

완료 기준:

- baseline snapshot memo가 있다.

### Step 2. S1 Scorable Row Audit 구현

목표:

- `scorable_shadow_rows = 0`의 직접 이유를 report에서 읽을 수 있게 한다.

해야 할 일:

- exclusion reason taxonomy 정의
- report summary / slice summary 반영
- markdown 반영

완료 기준:

- report JSON / markdown만 봐도 unscorable 원인을 분류할 수 있다.

### Step 3. 테스트 보강

목표:

- missing replay join
- invalid label status
- ambiguous / censored
- no transition counts

케이스가 회귀 테스트로 고정된다.

완료 기준:

- 관련 테스트가 통과한다.

### Step 4. 실제 report 재생성

목표:

- live data 기준 shadow compare report를 다시 생성해 실제 reason 분포를 본다.

완료 기준:

- latest report에 reason taxonomy가 들어간다.

### Step 5. 결과 문서화

목표:

- 이번 단계에서 확인한 baseline / scorable row 원인을 memo로 남긴다.

완료 기준:

- 다음 active step이 S2인지 S3인지 문서만 봐도 판단 가능하다.

## 5. Done Definition

아래를 만족하면 S0/S1을 닫는다.

- shadow compare report에 scorable exclusion taxonomy가 있다.
- 테스트가 그 taxonomy를 고정한다.
- 실제 latest report에서 대표 reason counts를 확인했다.
- baseline snapshot / scorable row memo가 있다.

현재 상태 메모:

- S0 baseline snapshot 완료
  - [refinement_shadow_compare_quality_baseline_snapshot_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_quality_baseline_snapshot_ko.md)
- S1 scorable row casebook 완료
  - [refinement_shadow_compare_quality_scorable_row_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_quality_scorable_row_casebook_ko.md)
- replay join alignment / source scope audit 완료
  - [refinement_shadow_compare_replay_join_alignment_audit_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_shadow_compare_replay_join_alignment_audit_ko.md)
- 다음 active step은 `S2 trace quality audit`이 아니라, 먼저 `compare source alignment policy`를 고정하는 쪽이 더 맞다.
