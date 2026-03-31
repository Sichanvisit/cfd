# Decision Log Coverage Gap Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `decision_log_coverage_gap`을
실행 가능한 순서로 쪼개기 위한 로드맵이다.

현재 방향은 아래처럼 잡는다.

- reader / matcher는 이미 상당 부분 준비됨
- 남은 핵심은 source retention / archive / backfill 운영
- 따라서 이 로드맵은 `logic tuning`이 아니라
  `coverage 확보와 provenance 고정`에 집중한다


## 2. 관련 기준 문서

- [refinement_r0_b6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)
- [decision_log_coverage_gap_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
- [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- [refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_execution_roadmap_ko.md)


## 3. 현재 상태

현재까지 구현된 것:

- archive-aware forensic reader
- detail sidecar history reader
- zero-anchor generic runtime linkage 완화
- archive manifest 시간 범위 기록 보강

현재 남은 것:

- 실제 archive/backfill source 생성
- coverage audit 자동화
- backfill 실행 기준 정리
- rerun 결과 검증


## 4. 전체 실행 순서

```text
C0. coverage baseline freeze
-> C1. source inventory / retention matrix
-> C2. coverage audit report
-> C3. archive generation hardening
-> C4. targeted backfill execution
-> C5. forensic rerun + delta review
-> C6. close-out + P1/P2 handoff
```


## 5. C0. Coverage Baseline Freeze

목표:

- 지금 coverage gap 상태를 기준선으로 고정한다

현재 상태:

- `구현 완료`
- 구현 파일:
  [decision_log_coverage_gap_baseline_freeze.py](c:\Users\bhs33\Desktop\project\cfd\scripts\decision_log_coverage_gap_baseline_freeze.py)
- 테스트 파일:
  [test_decision_log_coverage_gap_baseline_freeze.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_decision_log_coverage_gap_baseline_freeze.py)
- 최신 산출물:
  [decision_log_coverage_gap_c0_baseline_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c0_baseline_latest.json),
  [decision_log_coverage_gap_c0_baseline_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c0_baseline_latest.csv),
  [decision_log_coverage_gap_c0_baseline_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c0_baseline_latest.md)

최신 기준선:

- `coverage_earliest_time = 2026-03-27T15:29:43`
- `coverage_latest_time = 2026-03-29T23:41:00`
- `sample_rows = 30`
- `matched_rows = 7`
- `unmatched_outside_coverage = 23`
- `coverage_gap_rows = 23`
- `top_family = decision_log_coverage_gap`
- `recommended_next_step = C1_source_inventory_retention_matrix`

해야 할 일:

- 현재 `earliest coverage / latest coverage / gap count` 기록
- 현재 B2/B3/B4/B5 결과 파일 경로 고정
- 이후 비교 기준으로 사용할 baseline memo 생성

완료 기준:

- backfill 전 상태를 다시 비교할 수 있다
- 이후 C1~C5에서 baseline 대비 delta를 직접 비교할 수 있다


## 6. C1. Source Inventory / Retention Matrix

목표:

- 현재 decision source가 실제로 어디까지 있는지 표로 정리한다

대상 source:

- active csv
- legacy csv
- detail jsonl
- rotated detail jsonl
- archive parquet
- archive manifest

확인 항목:

- 파일 종류
- 시간 범위
- symbol 범위
- row count
- provenance field 존재 여부

완료 기준:

- "reader가 못 읽는가"가 아니라
  "source가 실제로 없는가"를 표로 말할 수 있다


## 7. C2. Coverage Audit Report

목표:

- coverage 상태를 수동 감각이 아니라 리포트로 본다

해야 할 일:

- coverage earliest/latest 자동 산출
- forensic sample 중 coverage outside count 집계
- symbol별 / 날짜별 gap 분포 집계
- recent adverse window와 coverage window overlap 집계

출력 예:

- `coverage_window_audit_latest.json`
- `coverage_window_audit_latest.md`

완료 기준:

- 지금 어느 날짜대가 비어 있는지 자동으로 알 수 있다


## 8. C3. Archive Generation Hardening

목표:

- 앞으로 생성되는 decision source가 coverage를 잃지 않게 만든다

해야 할 일:

- rollover 시 manifest 필드 검증
- archive row provenance 확인
- active -> legacy -> archive 전환 시 시간 범위 보존 확인
- detail/source linkage 필드 누락 점검

핵심 파일:

- [rollover_entry_decisions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\rollover_entry_decisions.py)
- [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

완료 기준:

- future window는 현재와 같은 archive 공백을 덜 만들 수 있다


## 9. C4. Targeted Backfill Execution

목표:

- 필요한 기간에 한해 실제 backfill을 수행한다

기본 원칙:

- 전량 복구보다 우선순위 구간부터
- recent adverse sample이 몰린 구간 우선
- acceptance / recent operate window 우선

해야 할 일:

- backfill 대상 기간 목록 작성
- source availability 확인
- 가능한 경우 archive 생성 또는 import
- backfill 후 manifest 갱신

완료 기준:

- 최소 한 개 이상의 최근 forensic 중요 구간이 coverage 안쪽으로 들어온다


## 10. C5. Forensic Rerun + Delta Review

목표:

- backfill 후 coverage gap이 실제로 줄었는지 본다

rerun 대상:

- [r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_match_rows.py)
- [r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_table.py)
- [r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_families.py)
- [r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_actions.py)

확인할 것:

- `coverage_gap` 감소 여부
- `fallback_match` 변화 여부
- family 우선순위 재정렬 여부
- logic family가 더 선명해졌는지 여부

완료 기준:

- coverage 문제와 logic 문제의 경계가 전보다 선명해진다


## 11. C6. Close-Out + P1/P2 Handoff

목표:

- coverage 문제를 닫고 다음 운영 관측 단계로 넘긴다

P1로 넘길 것:

- coverage 안쪽 샘플 중심 lifecycle correlation
- entry / wait / exit chain 분석

P2로 넘길 것:

- coverage 안쪽 샘플 기준 expectancy / attribution
- family별 경제성 해석

완료 기준:

- 이제 "로그가 없어서 모른다"보다
  "로그는 있고 그 의미를 읽으면 된다" 상태가 된다


## 12. 테스트 / 검증 기준

coverage 작업은 코드 변경이 생길 경우 아래를 최소 기준으로 본다.

```powershell
python -m pytest tests/unit/test_entry_engines.py -q
python -m pytest tests/unit/test_storage_compaction.py -q
python -m pytest tests/unit/test_rollover_entry_decisions_script.py -q
python -m pytest tests/unit/test_r0_b_actual_entry_forensic_match_rows.py -q
python -m pytest tests/unit -q
```

현재 기준선:

- 전체 unit suite: `1106 passed`
- `decision_log_coverage_gap_baseline_freeze` 단위 테스트: `2 passed`


## 13. 현재 최우선 순서

가장 현실적인 다음 순서는 아래다.

1. coverage baseline memo 생성
2. source inventory / retention matrix 작성
3. coverage audit report 자동화
4. future archive generation hardening
5. targeted backfill
6. forensic rerun


## 14. 한 줄 결론

`decision_log_coverage_gap` 로드맵의 목적은 forensic 로직을 더 복잡하게 만드는 것이 아니라, forensic truth가 닿는 시간 구간을 넓혀 이후 분석이 믿을 수 있게 만드는 것이다.
## 15. C1 Latest Status

`C1 source inventory / retention matrix` is now implemented.

- Script:
  [decision_log_coverage_gap_source_inventory.py](c:\Users\bhs33\Desktop\project\cfd\scripts\decision_log_coverage_gap_source_inventory.py)
- Test:
  [test_decision_log_coverage_gap_source_inventory.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_decision_log_coverage_gap_source_inventory.py)
- Outputs:
  [decision_log_coverage_gap_c1_source_inventory_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c1_source_inventory_latest.json)
  [decision_log_coverage_gap_c1_source_inventory_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c1_source_inventory_latest.csv)
  [decision_log_coverage_gap_c1_source_inventory_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c1_source_inventory_latest.md)

Latest snapshot:

- `total_source_records = 57`
- `active_csv_count = 1`
- `legacy_csv_count = 2`
- `active_detail_count = 1`
- `legacy_detail_count = 2`
- `rotated_detail_count = 51`
- `archive_parquet_count = 0`
- `entry_manifest_source_count = 0`
- `coverage_gap_rows = 23`
- `inventory_state = archive_gap_dominant`
- `recommended_next_step = C2_coverage_audit_report`

Interpretation:

- The reader can already see active / legacy / detail rotate sources.
- The operational gap is the absence of `entry_decisions` archive parquet and entry-specific archive/rollover/retention manifests.
- After C1, the next step is `C2 coverage audit report`, not more matcher tuning.


## 16. C2 Latest Status

`C2 coverage audit report` is now implemented.

- Script:
  [decision_log_coverage_gap_audit_report.py](c:\Users\bhs33\Desktop\project\cfd\scripts\decision_log_coverage_gap_audit_report.py)
- Test:
  [test_decision_log_coverage_gap_audit_report.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_decision_log_coverage_gap_audit_report.py)
- Outputs:
  [decision_log_coverage_gap_c2_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c2_audit_latest.json)
  [decision_log_coverage_gap_c2_audit_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c2_audit_latest.csv)
  [decision_log_coverage_gap_c2_audit_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c2_audit_latest.md)

Latest audit snapshot:

- `outside_coverage_rows = 23`
- `forensic_ready_outside_rows = 15`
- `before_coverage_rows = 23`
- `after_coverage_rows = 0`
- `top_gap_symbol = XAUUSD (20)`
- `top_gap_open_date = 2026-03-27 (11)`
- `top_gap_symbol_date = 2026-03-27|XAUUSD (11)`
- `top_gap_setup_id = range_upper_reversal_sell (13)`
- `recommended_next_step = C3_archive_generation_hardening`

Interpretation:

- Current coverage gaps are not scattered randomly.
- They cluster before the present coverage window.
- The operational next step is to harden archive/rollover/retention generation before attempting targeted backfill.


## 17. C3 Latest Status

`C3 archive generation hardening` is now implemented in code.

Key changes:

- [entry_decision_rollover.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_decision_rollover.py)
  added as the shared rollover/archive/manifest helper.
- [rollover_entry_decisions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\rollover_entry_decisions.py)
  now delegates to the shared helper.
- [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)
  now uses the same helper during runtime append, so active `entry_decisions.csv` can auto-roll on size/day/schema triggers.

Validation:

- manual script path test remains green
- runtime append auto-rollover test added
- full unit suite: `1111 passed`

Current live dry-run:

- `would_roll = true`
- `rollover_reasons = ["schema_change"]`
- archive and manifest roots resolve correctly

Interpretation:

- C3 code hardening is in place.
- The current live `entry_decisions.csv` is now ready to roll safely when the operator chooses to execute it.
- The next strategic step is still `C4 targeted backfill`, but an actual live rollover execution can be done first if we want real archive/manifests before backfill.


## 18. C4/C5 Latest Status

Coverage track now stands at:

- `C0 baseline freeze`: complete
- `C1 source inventory / retention matrix`: complete
- `C2 coverage audit report`: complete
- `C3 archive generation hardening`: complete
- `live rollover execution`: complete
- `C4 targeted backfill`: complete
- `C5 forensic rerun + delta review`: complete

Reference memo:

- [decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md)
- [decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md)

Latest C5 fixed result:

- `rerun_state = archive_provenance_improved_but_gap_unchanged`
- `archive_source_delta = 1`
- `matched_rows_delta = 0`
- `coverage_gap_rows_delta = 0`
- `recommended_next_step = C6_close_out_handoff`

Interpretation:

- internal archive provenance was strengthened,
- but the actual forensic coverage gap did not shrink,
- so the remaining problem should now be treated as an external or unavailable historical coverage gap, not a missing internal reader path.


## 19. C6 Close-Out Status

`C6 close-out + handoff` is now ready.

Close-out reference:

- [decision_log_coverage_gap_c6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c6_close_out_handoff_ko.md)

Fixed close-out interpretation:

- the internal reader and archive path is no longer the top blocker
- targeted internal backfill was executed
- C5 delta remained flat on actual gap metrics
- the remaining top issue should now be treated as an `external / unavailable historical coverage gap`

Handoff direction:

- if external historical decision sources become available, reopen a backfill-only coverage track
- otherwise keep the limitation explicit and move into `P1 lifecycle correlation` and `P2 expectancy` with coverage-aware separation
