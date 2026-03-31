# Decision Log Coverage Gap C4 Targeted Backfill Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `decision_log_coverage_gap` 트랙의 `C4 targeted backfill execution` 결과를
짧고 명확하게 고정하기 위한 메모다.

핵심 질문은 이것이다.

`현재 workspace 안에서 실제로 backfill 가능한 internal source가 있었고, 그것을 archive/manifests로 올렸는가?`


## 2. 구현 파일

- [decision_log_coverage_gap_targeted_backfill.py](c:\Users\bhs33\Desktop\project\cfd\scripts\decision_log_coverage_gap_targeted_backfill.py)
- [entry_decision_rollover.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_decision_rollover.py)
- [test_decision_log_coverage_gap_targeted_backfill.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_decision_log_coverage_gap_targeted_backfill.py)


## 3. 산출물

- [decision_log_coverage_gap_c4_backfill_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c4_backfill_latest.json)
- [decision_log_coverage_gap_c4_backfill_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c4_backfill_latest.csv)
- [decision_log_coverage_gap_c4_backfill_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c4_backfill_latest.md)
- backfill manifest:
  [decision_log_coverage_gap_backfill_20260330_014003.json](c:\Users\bhs33\Desktop\project\cfd\data\manifests\backfill\decision_log_coverage_gap_backfill_20260330_014003.json)


## 4. 현재 결과

최신 실행 결과:

- `candidate_source_count = 5`
- `selected_source_count = 2`
- `executed_backfill_count = 2`
- `primary_overlap_selection_count = 1`
- `boundary_support_selection_count = 1`
- `already_archived_skip_count = 1`
- `outside_scope_skip_count = 2`
- `recommended_next_step = C5_forensic_rerun_delta_review`

선정된 source:

1. `entry_decisions.legacy_20260327_212023.csv`
   - reason: `primary_overlap_backfill`
   - time range: `2026-03-27T15:29:43 -> 2026-03-27T21:18:50`

2. `entry_decisions.legacy_20260328_000522.csv`
   - reason: `boundary_support_backfill:adjacent_after_target`
   - time range: `2026-03-27T21:20:23 -> 2026-03-28T00:04:40`

생성된 archive parquet:

- [entry_decisions.legacy_20260327_212023_20260330_014003_225233_entry_decisions_legacy_20260327_212023.parquet](c:\Users\bhs33\Desktop\project\cfd\data\trades\archive\entry_decisions\year=2026\month=03\day=27\entry_decisions.legacy_20260327_212023_20260330_014003_225233_entry_decisions_legacy_20260327_212023.parquet)
- [entry_decisions.legacy_20260328_000522_20260330_014003_225234_entry_decisions_legacy_20260328_000522.parquet](c:\Users\bhs33\Desktop\project\cfd\data\trades\archive\entry_decisions\year=2026\month=03\day=27\entry_decisions.legacy_20260328_000522_20260330_014003_225234_entry_decisions_legacy_20260328_000522.parquet)


## 5. 의미

C4의 의미는 다음과 같다.

- 이제 `decision_log_coverage_gap`은 단순히 archive hardening만 끝난 상태가 아니다.
- 실제 internal historical source 두 개가 archive parquet + archive manifest로 올라갔다.
- 즉 `현재 coverage boundary 주변 historical provenance`가 더 강해졌다.

하지만 C4가 아직 증명하지 않은 것도 있다.

- `coverage_gap_rows = 23`이 실제로 줄었는지
- B2/B3/B4/B5 결과가 얼마나 달라졌는지

그건 아직 모른다.
그 판단은 `C5 forensic rerun + delta review`에서 해야 한다.


## 6. 테스트 기준선

실행 후 기준선:

- targeted tests:
  - `test_decision_log_coverage_gap_targeted_backfill.py`: `2 passed`
  - `test_rollover_entry_decisions_script.py`, `test_entry_engines.py`: `16 passed`
  - `test_r0_b_actual_entry_forensic_match_rows.py`: `9 passed`
- full unit suite:
  - `1113 passed`


## 7. 다음 단계

다음 단계는 `C5 forensic rerun + delta review`다.

즉 이제 물어야 할 질문은 이것이다.

`C4에서 새로 archive한 source를 포함해서 B2/B3/B4/B5를 다시 돌리면, coverage gap과 family 우선순위가 실제로 바뀌는가?`
