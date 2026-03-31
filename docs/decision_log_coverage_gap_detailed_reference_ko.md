# Decision Log Coverage Gap Detailed Reference

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `decision_log_coverage_gap`을
막연한 운영 이슈가 아니라
구현 가능한 문제 정의로 고정하기 위한 상세 기준 문서다.

핵심 질문은 아래 하나다.

`왜 recent adverse trade 중 상당수가 decision row와 안정적으로 연결되지 않는가?`


## 2. 문제 정의

현재 forensic 체인에서 드러난 핵심 사실은 아래다.

- adverse sample은 추출된다
- matcher는 동작한다
- active / legacy / detail / archive-aware reader도 연결돼 있다
- generic runtime linkage 과신 문제도 이미 완화됐다

그런데도 일부 sample은
decision row coverage 밖에 있다.

즉 현재 문제는
`매칭 알고리즘 부재`보다
`historical decision source coverage 부족`이다.


## 3. 현재 기준선

R0-B 최신 forensic 기준선:

- `sample 30`
- `matched 7`
- `exact 0`
- `fallback 7`
- `unmatched 23`

추가 해석:

- `coverage_gap 23`
- `fallback_match 7`
- `earliest coverage = 2026-03-27T15:29:43`

의미:

- 지금 workspace에서 접근 가능한 decision source는
  recent window 일부만 덮고 있다
- 그보다 과거 trade는 forensic join 시
  `unmatched_outside_coverage`로 남을 가능성이 높다


## 4. 이 문제가 중요한 이유

이 문제를 먼저 잡아야 하는 이유는 세 가지다.

### 4-1. forensic truth가 흔들린다

coverage 바깥 trade는
`진짜 entry leakage인지`
`그냥 로그 공백인지`
구분하기 어렵다.

### 4-2. expectancy / lifecycle 해석이 오염된다

P0/P1/P2로 넘어가려면
entry-wait-exit를 lifecycle로 읽어야 하는데,
entry decision row가 비어 있으면
해석이 끊긴다.

### 4-3. 잘못된 수정 우선순위를 만들 수 있다

coverage gap을
logic bug처럼 읽으면 안 된다.

즉 이 문제는
수정해야 할 entry logic보다 앞에 있는
`관측 가능성 문제`다.


## 5. 이미 해결된 것과 아직 안 된 것

### 5-1. 이미 해결된 것

- C0 baseline freeze 산출물 생성
  - [decision_log_coverage_gap_c0_baseline_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c0_baseline_latest.json)
  - [decision_log_coverage_gap_c0_baseline_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c0_baseline_latest.md)
- active / legacy csv reader
- detail jsonl sidecar reader
- archive-aware reader
- archive manifest의 시간 범위 기록 보강
- generic `runtime_snapshot_key` exact 과신 제거
- forensic table에서 `coverage_gap`과 `fallback_match` 분리

즉 reader / matcher / classification 쪽 기반은
상당 부분 준비됐다.

### 5-2. 아직 안 된 것

- 실제 historical archive source 확보
- backfill 정책 정의
- coverage window 자체를 운영 기준으로 점검하는 audit
- coverage 바깥 trade에 대한 explicit labeling 및 reporting 규칙

즉 현재 상태를 한 줄로 요약하면:

`baseline은 잠겼고, 이제 source inventory와 retention matrix를 통해 실제 공백의 위치와 성격을 명시적으로 확인해야 한다.`


## 6. scope

### 이 문서의 범위 안

- `entry_decisions` source retention
- active / legacy / detail / archive storage coverage
- archive manifest 시간 범위
- forensic matcher가 coverage 안/밖을 명확히 구분하는 것
- backfill 실행 기준

### 이 문서의 범위 밖

- symbol balance 재튜닝
- entry threshold 조정
- consumer / guard / probe 로직 재설계
- lifecycle expectancy 계산 자체


## 7. 핵심 owner

- [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
- [rollover_entry_decisions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\rollover_entry_decisions.py)
- [r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_match_rows.py)

보조 owner:

- [r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_table.py)
- [r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_families.py)
- [r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_actions.py)


## 8. 불변조건

`decision_log_coverage_gap`을 닫아가려면
최소한 아래 불변조건을 만족해야 한다.

1. coverage 안쪽 trade는
   decision row와 최소 한 번은 연결되거나,
   왜 연결되지 않았는지 explicit reason이 남아야 한다
2. coverage 바깥 trade는
   `logic unmatched`가 아니라 `outside_coverage`로 분리돼야 한다
3. archive manifest는
   `time_range_start / time_range_end`를 가져야 한다
4. forensic reader는
   active / legacy / detail / archive를 함께 읽더라도
   source provenance를 잃지 않아야 한다
5. future retention은
   recent adverse window가 archive 공백 때문에 끊기지 않도록 설계돼야 한다


## 9. 구현 전략의 기본 방향

이 문제는
`한 번에 과거 전부를 복구하는 프로젝트`로 가면 안 된다.

더 현실적인 방향은 아래다.

### 9-1. 운영 기준 먼저

- 현재 coverage earliest/latest를 자동으로 산출
- 공백 구간을 명시적으로 보고
- coverage outside trade 수를 매번 확인

### 9-2. 앞으로의 공백부터 막기

- active -> legacy -> archive 흐름이 시간 범위를 잃지 않도록 보강
- detail/source provenance를 같이 보존

### 9-3. 그 다음 필요한 구간만 backfill

- recent adverse sample이 많이 몰린 구간
- 최근 acceptance / rollout 기준 창
- forensic에 꼭 필요한 기간

즉 `전량 복구`보다
`필요 구간 우선 backfill`이 맞다.


## 10. 산출물

이 트랙이 진행되면 아래 산출물이 있어야 한다.

- coverage window audit report
- source inventory / retention matrix
- archive manifest validation report
- backfill 대상 기간 목록
- backfill 실행 로그
- backfill 후 rerun된 B2/B3/B4/B5 최신 리포트


## 11. 완료 기준

아래 조건을 만족하면
`decision_log_coverage_gap` 1차 완료로 본다.

1. current coverage window를 자동으로 알 수 있다
2. coverage gap이 reader 부족인지 source 부재인지 구분 가능하다
3. 앞으로 생성되는 decision source는 archive coverage를 잃지 않는다
4. 필요한 recent forensic 구간에 대해 backfill을 실행할 수 있다
5. R0-B rerun 시 `coverage_gap` 비중이 의미 있게 줄어든다


## 12. 한 줄 결론

`decision_log_coverage_gap`은 매칭 문제가 아니라 observability retention 문제이며, 이걸 해결해야 이후 forensic과 expectancy 해석이 믿을 수 있게 된다.
## 13. C1 Inventory Snapshot

`C1 source inventory / retention matrix` result fixed the operational picture more clearly.

- [decision_log_coverage_gap_c1_source_inventory_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c1_source_inventory_latest.json)
- [decision_log_coverage_gap_c1_source_inventory_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c1_source_inventory_latest.md)

Current key numbers:

- `total_source_records = 57`
- `active_csv = 1`
- `legacy_csv = 2`
- `active_detail = 1`
- `legacy_detail = 2`
- `rotated_detail = 51`
- `archive_parquet = 0`
- `archive_manifest = 0`
- `rollover_manifest = 0`
- `retention_manifest = 0`
- `coverage_gap_rows = 23`

This means the current bottleneck is not a missing reader path. It is an operational retention gap:

- decision rows exist in active and legacy CSV.
- detail-sidecar history exists heavily.
- but `entry_decisions` warm archive and entry-specific manifests are absent.

So the next correct question is:

`where is coverage missing by date/symbol/window, and what should be hardened or backfilled first?`

That is why the next step after C1 is `C2 coverage audit report`.


## 14. C2 Audit Snapshot

`C2 coverage audit report` made the current gap shape explicit.

- [decision_log_coverage_gap_c2_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c2_audit_latest.json)
- [decision_log_coverage_gap_c2_audit_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c2_audit_latest.md)

Current key readings:

- `outside_coverage_rows = 23`
- `forensic_ready_outside_rows = 15`
- `before_coverage_rows = 23`
- `after_coverage_rows = 0`
- `top_gap_symbol = XAUUSD (20)`
- `top_gap_open_date = 2026-03-27 (11)`
- `top_gap_setup_id = range_upper_reversal_sell (13)`

This matters because the gap is not just “older history is missing”.
It has a visible cluster shape:

- the missing rows sit before the current coverage window,
- they are concentrated in specific symbol/date/setup families,
- and they align with the operational absence of archive parquet and entry manifests.

So after C2, the next step is not `C4 targeted backfill` yet.
The correct next step is `C3 archive generation hardening`.


## 15. C3 Hardening Snapshot

`C3 archive generation hardening` changed the system from “manual rollover script exists” to “manual and runtime paths share the same rollover/archive helper”.

Implemented changes:

- shared helper:
  [entry_decision_rollover.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_decision_rollover.py)
- manual script wrapper:
  [rollover_entry_decisions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\rollover_entry_decisions.py)
- runtime append integration:
  [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py)

Important live dry-run signal:

- current `entry_decisions.csv` reports `would_roll = true`
- current trigger is `schema_change`

This means C3 is not only future-proofing.
It also tells us the current live file is already eligible for a safe rollover when we decide to execute it.


## 16. C4/C5 Snapshot

The coverage track has now moved past hardening and into verification.

Reference memos:

- [decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md)
- [decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md)

What changed operationally:

- live rollover was executed successfully
- archive parquet and entry manifests now exist for the active path
- targeted internal backfill archived two overlapping legacy sources
- C5 rerun now reads a frozen baseline snapshot so repeated reruns do not erase the meaningful delta

What changed analytically:

- `archive_source_delta = 1`
- `decision_source_count = 3 -> 5`
- `matched_rows_delta = 0`
- `coverage_gap_rows_delta = 0`
- `top_family` remains `decision_log_coverage_gap`

Meaning:

- the system improved provenance and retention evidence,
- but it did not reduce the current adverse-entry forensic gap,
- so the remaining gap is best treated as a historical coverage availability problem rather than a logic or reader-path problem.


## 17. C6 Close-Out Interpretation

The coverage track can now be closed in its internal scope.

Reference:

- [decision_log_coverage_gap_c6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c6_close_out_handoff_ko.md)

What is now considered closed:

- reader path hardening
- archive/manifest hardening
- runtime/manual rollover alignment
- targeted internal backfill
- stable rerun delta baseline

What is still open:

- historical decision rows that are outside currently available workspace coverage

So this issue should now be carried forward as an explicit coverage limitation, not as an unresolved internal implementation task.
