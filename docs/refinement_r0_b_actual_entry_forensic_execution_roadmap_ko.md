# R0-B Actual Entry Forensic 구현 로드맵

작성일: 2026-03-29 (KST)

## 1. 목적

이 문서는 `R0-B actual entry forensic`을 실제로 어떻게 수행할지 정리한 실행 로드맵이다.

핵심 전제는 단순하다.

- R0 기준선은 이미 있다
- 지금 필요한 건 새 phase 추가가 아니다
- 최근 adverse entry를 그 기준선으로 다시 읽고,
  수정 후보를 entry gate/guard 수준까지 좁히는 것이다

관련 기준 문서:

- [refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b_actual_entry_forensic_detailed_reference_ko.md)
- [refinement_r0_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_detailed_reference_ko.md)
- [external_advice_synthesis_and_master_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\external_advice_synthesis_and_master_roadmap_ko.md)


## 2. 현재 출발점

현재는 아래처럼 이해하는 것이 맞다.

- `R0` 기준선은 완료
- `S0 ~ S6`는 구현 완료, 한 윈도우 더 관찰
- 지금 가장 현실적인 즉시 대응은 `R0-B actual entry forensic`
- 그 결과를 `P0 / P1 / P2`로 넘긴다

즉 이 로드맵은
`구조를 새로 만드는 작업`이 아니라
`지금 손실 entry가 왜 열렸는지 설명 가능한 입력으로 만드는 작업`이다.


## 3. 이 로드맵에서 할 것과 하지 않을 것

### 할 것

- 실제 체결 기준 adverse entry 샘플 추출
- 직전 decision row 매칭
- R0 계약 필드 기반 forensic 테이블 생성
- 공통 family / guard 누수 / stage mismatch 가설 도출
- 수정 우선순위 후보 도출

### 하지 않을 것

- symbol balance 재튜닝
- chart display 재설계
- expectancy 전체 집계
- drift / health / adaptation 구현
- ContextClassifier 분해 같은 상위 아키텍처 작업


## 4. 전체 실행 순서

```text
R0-B1 샘플 추출
-> R0-B2 row 매칭
-> R0-B3 forensic 테이블 정규화
-> R0-B4 family clustering
-> R0-B5 수정 후보 도출
-> R0-B6 close-out + P0/P1 handoff
```


## 5. R0-B1. 샘플 추출

목표:

- 실제로 문제가 있다고 체감되는 entry sample을 먼저 고정한다

현재 상태:

- `구현 완료`
- 구현 파일:
  [r0_b_actual_entry_forensic_samples.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_samples.py)
- 최신 산출물:
  [r0_b1_adverse_entry_samples_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b1_adverse_entry_samples_latest.json),
  [r0_b1_adverse_entry_samples_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b1_adverse_entry_samples_latest.csv),
  [r0_b1_adverse_entry_samples_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b1_adverse_entry_samples_latest.md)

대상:

- 최근 손실 청산 trade
- 짧은 보유 후 손실 청산 trade
- entry 직후 adverse move가 큰 trade

우선순위:

1. `hold_seconds`가 짧고 손실인 trade
2. `MAE`가 빠르게 커진 trade
3. 사용자가 직접 문제라고 느낀 심볼의 recent trade

완료 기준:

- 최소 10건 내외의 recent adverse entry sample 목록이 있다
- symbol, open time, close time, ticket, direction이 정리돼 있다


## 6. R0-B2. Row 매칭

목표:

- 각 adverse entry sample을 직전 decision row와 안정적으로 연결한다

현재 상태:

- `구현 완료`
- 구현 파일:
  [r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_match_rows.py)
- 테스트 파일:
  [test_r0_b_actual_entry_forensic_match_rows.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_match_rows.py)
- 최신 산출물:
  [r0_b2_decision_row_matches_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b2_decision_row_matches_latest.json),
  [r0_b2_decision_row_matches_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b2_decision_row_matches_latest.csv),
  [r0_b2_decision_row_matches_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b2_decision_row_matches_latest.md)

최신 실행 기준선:

- sample 30건 중 `22건 매칭`
- `exact 15`, `fallback 7`, `unmatched 8`
- `unmatched 8`은 전부 `decision log coverage 밖`으로 분류됨
- `fallback 7`은 전부 coverage 안쪽이며 실제 open time과 가까운 시각으로 연결됨
- `exact 15`는 모두 `exact_runtime_snapshot_key`였고,
  이 중 다수가 `runtime_signal_row_v1|...|anchor_value=0.0` 형태의 generic key와 연결됨

현재 해석:

- B2 자체는 동작한다.
- 다만 `runtime_snapshot_key` exact linkage 중 일부는
  진짜 강한 exact key라기보다 `generic runtime anchor key 재사용` 가능성이 있다.
- 이 패턴은 B3에서 `suspicious_exact_runtime_linkage`로 별도 표시해서
  forensic truth로 바로 믿지 않도록 다루는 것이 안전하다.

수정 후 최신 기준선:

- `matcher generic runtime exact downgrade` 적용 후
  `sample 30 / matched 7 / exact 0 / fallback 7 / unmatched 23`
- `unmatched 23`은 전부 `decision log coverage 밖`으로 분류됨
- 즉 기존의 `runtime_linkage_integrity_gap 15`는
  실제 exact가 아니라 generic runtime key 과신이었고,
  현재 기준선에서는 `coverage gap`으로 흡수된다
- 추가로 `detail history reader`를 붙여
  active/legacy csv 외에 detail sidecar 회전 파일도 같이 읽도록 보강했다
- 그리고 `archive-aware matcher`를 추가해
  향후 `data/trades/archive/entry_decisions/**/*.parquet`와
  archive manifest의 `time_range_start/time_range_end`도
  forensic coverage source로 읽을 수 있게 했다
- 그 결과 coverage earliest는 여전히 `2026-03-27T15:29:43`이므로,
  현재 남은 23건은 reader 한계가 아니라
  현재 workspace 기준으로는
  `archive source 부재 + historical retention 공백`으로 보는 것이 맞다

입력 키:

- `trade_link_key`
- `decision_row_key`
- `runtime_snapshot_key`
- `replay_row_key`

작업:

- closed trade row에서 `trade_link_key` 추출
- `entry_decisions.csv`에서 해당 trade와 연결된 row 탐색
- 필요 시 decision time / anchor time 기준으로 최근접 row 보강

완료 기준:

- sample 1건당 대응 decision row 1건 이상을 찾을 수 있다
- linkage gap이 있으면 별도 메모로 분리된다


## 7. R0-B3. Forensic 테이블 정규화

목표:

- 모든 sample을 동일 형식으로 읽을 수 있게 만든다

현재 상태:

- `구현 완료`
- 구현 파일:
  [r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_table.py)
- 테스트 파일:
  [test_r0_b_actual_entry_forensic_table.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_table.py)
- 최신 산출물:
  [r0_b3_forensic_table_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b3_forensic_table_latest.json),
  [r0_b3_forensic_table_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b3_forensic_table_latest.csv),
  [r0_b3_forensic_table_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b3_forensic_table_latest.md)

최신 실행 기준선:

- `row_count 30`
- `manual_review_rows 30`
- `suspicious_exact_runtime_linkage_rows 0`
- `coverage_gap_rows 23`
- `fallback_match_rows 7`
- `entry_row_alignment_counts`
  - `unknown 23`
  - `row_says_not_ready 7`

현재 해석:

- B3는 단순 표 만들기 단계가 아니라,
  `generic runtime exact linkage`, `coverage gap`, `row readiness mismatch`를
  같은 언어로 분리해내는 데 성공했다.
- runtime exact downgrade 이후 현재 adverse sample의 다수는
  `coverage gap`으로 재분류된다.
- 즉 B3 이후의 핵심은
  `generic runtime linkage 경고`보다
  `retention coverage 부족`과
  coverage 안쪽에 남아 있는 `row_says_not_ready` 집합을 분리하는 것이다.

필수 열:

- `symbol`
- `time`
- `action`
- `outcome`
- `setup_id`
- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `quick_trace_state`
- `quick_trace_reason`
- `probe_plan_ready`
- `consumer_check_stage`
- `consumer_check_entry_ready`
- `r0_non_action_family`
- `r0_semantic_runtime_state`
- `decision_row_key`
- `runtime_snapshot_key`
- `trade_link_key`

추가 권장 열:

- `entry_price`
- `exit_price`
- `hold_seconds`
- `exit_reason`
- `mae_before_exit`

완료 기준:

- sample을 행 단위로 비교 가능한 단일 표가 있다
- 사람 눈으로만 보던 사례가 같은 필드 언어로 묶인다


## 8. R0-B4. Family Clustering

목표:

- 케이스를 "개별 손실"이 아니라 "반복 패턴"으로 읽는다

현재 상태:

- `구현 완료`
- 구현 파일:
  [r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_families.py)
- 테스트 파일:
  [test_r0_b_actual_entry_forensic_families.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_families.py)
- 최신 산출물:
  [r0_b4_family_clustering_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b4_family_clustering_latest.json),
  [r0_b4_family_clustering_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b4_family_clustering_latest.csv),
  [r0_b4_family_clustering_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b4_family_clustering_latest.md)

최신 실행 기준선:

- `row_count 30`
- `family_count 4`
- `repeat_families 4`
- `family_counts`
  - `decision_log_coverage_gap 23`
  - `consumer_stage_misalignment 3`
  - `guard_leak 2`
  - `probe_promoted_too_early 2`

현재 해석:

- B4는 문서상의 가설을 실제 반복 family로 내렸다.
- 현재 우선순위는
  `entry threshold 튜닝`보다 먼저
  `decision log coverage`를 다루는 것이다.
- 다만 이제 coverage 쪽 reader는
  active/legacy/detail/archive까지 모두 열려 있으므로,
  남은 gap은 매처 기능보다
  실제 source retention/backfill 문제로 해석하는 편이 더 정확하다.
- 그다음 실제 entry 품질 수정 후보는
  `consumer_stage_misalignment`, `guard_leak`, `probe_promoted_too_early`
  family에서 나온다.

묶는 축:

- `setup_id`
- `observe_reason`
- `consumer_check_stage`
- `quick_trace_state`
- `probe_plan_ready`
- `r0_non_action_family`

대표 가설:

- `probe_promoted_too_early`
- `confirm_quality_too_weak`
- `guard_leak`
- `consumer_stage_misalignment`
- `exit_not_entry_issue`

완료 기준:

- 최소 2개 이상의 반복 family를 설명할 수 있다
- 각 family마다 대표 sample을 1건 이상 지정할 수 있다


## 9. R0-B5. 수정 후보 도출

목표:

- forensic 결과를 실제 코드 owner 수준의 수정 후보로 내린다

현재 상태:

- `구현 완료`
- 구현 파일:
  [r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\scripts\r0_b_actual_entry_forensic_actions.py)
- 테스트 파일:
  [test_r0_b_actual_entry_forensic_actions.py](c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_r0_b_actual_entry_forensic_actions.py)
- 최신 산출물:
  [r0_b5_action_candidates_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b5_action_candidates_latest.json),
  [r0_b5_action_candidates_latest.csv](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b5_action_candidates_latest.csv),
  [r0_b5_action_candidates_latest.md](c:\Users\bhs33\Desktop\project\cfd\data\analysis\r0_b_actual_entry_forensic\r0_b5_action_candidates_latest.md)

최신 실행 기준선:

- `candidate_count 4`
- `critical_candidates 1`
- `high_candidates 3`

현재 우선순위:

1. `decision_log_coverage_gap`
   - owner:
     [entry_engines.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_engines.py),
     [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)
   - issue:
     adverse sample과 decision row retention coverage가 끊김
2. `consumer_stage_misalignment`
    - owner:
      [consumer_check_state.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py),
      [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
3. `guard_leak`
   - owner:
     [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py),
     [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
4. `probe_promoted_too_early`
   - owner:
     [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py),
     [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)

현재 해석:

- B5 결과상, 지금은 `entry threshold`나 `symbol balance`를 더 만질 타이밍이 아니다.
- 먼저 `decision log coverage`를 잡아
  forensic truth의 join 가능성을 높여야 한다.
- coverage를 잡는 일의 구현 축은 이제
  `archive-aware forensic read`까지 포함해 준비됐고,
  남은 과제는 실제 archive 생성/보존 운영이다.
- 그 다음 실제 entry behavior 수정은
  `consumer_stage_misalignment`, `guard_leak`, `probe_promoted_too_early`
  순으로 보는 것이 맞다.
- 이 중 `consumer_stage_misalignment`는
  첫 구현 패스가 이미 들어갔다.
  - `consumer_open_guard_v1` 계약 추가
  - order submit 직전 `consumer_stage_blocked / consumer_entry_not_ready`
    hard-stop 추가
  - 관련 테스트 추가
- `guard_leak`도 첫 구현 패스가 들어갔다.
  - `entry_blocked_guard_v1` 계약 추가
  - `forecast_guard / outer_band_guard / barrier_guard / middle_sr_anchor_guard`
    및 명시적 wait-suppress 사유에 대한 order submit 직전 hard-stop 추가
  - probe promotion 흐름은 유지되도록 strict guard set으로 범위를 좁힘
- `probe_promoted_too_early`도 첫 구현 패스가 들어갔다.
  - `probe_promotion_guard_v1` 계약 추가
  - `probe_not_promoted + plan_ready_for_entry=false + quick_trace_state=PROBE`
    류 조합에서 consumer state가 비어 있어도 submit 직전 hard-stop 추가
  - 즉 probe plan의 not-ready 상태가 consumer 누락으로 open path를 통과하지 않게 보강

출력 형식:

| family | suspected owner | suspected issue | next action |
|---|---|---|---|
| `probe_promoted_too_early` | `entry_try_open_entry.py` | probe promotion contract too permissive | first-pass hard-stop done |

대표 owner:

- [entry_service.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py)
- [entry_try_open_entry.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py)
- [consumer_check_state.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)
- [storage_compaction.py](c:\Users\bhs33\Desktop\project\cfd\backend\services\storage_compaction.py)

완료 기준:

- "어디를 볼지 모르겠다" 상태가 아니라
  "먼저 볼 코드 owner가 여기다" 상태가 된다


## 10. R0-B6. Close-Out + P0/P1 handoff

목표:

- forensic 결과를 상위 로드맵으로 자연스럽게 넘긴다

현재 기준 close-out 문서:

- [refinement_r0_b6_close_out_handoff_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r0_b6_close_out_handoff_ko.md)

다음 1순위 상세/실행 문서:

- [decision_log_coverage_gap_detailed_reference_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
- [decision_log_coverage_gap_execution_roadmap_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_execution_roadmap_ko.md)

P0로 넘길 것:

- decision trace에 꼭 들어가야 할 필드
- ownership ambiguity가 드러난 지점
- logging 보강 필요 필드

P1로 넘길 것:

- lifecycle correlation이 특히 필요한 family
- entry 문제인지 exit 문제인지 구분이 필요한 sample 그룹

완료 기준:

- forensic 결과가 단발 메모가 아니라
  다음 설계 작업의 입력으로 남는다
- 그리고 현재 active next step이
  `decision_log_coverage_gap`으로 문서상 고정된다


## 11. 테스트 / 검증 기준

R0-B 실행 전에 유지되어야 할 최소 기준:

```powershell
python -m pytest tests/unit/test_r0_row_interpretation.py -q
python -m pytest tests/unit/test_storage_compaction.py -q
python -m pytest tests/unit/test_entry_service_guards.py -q
python -m pytest tests/unit/test_check_semantic_canary_rollout.py -q
```

현재 기준 메모:

- R0 인접 targeted 테스트 통과
- 전체 unit suite: `1106 passed`
- 기존 observe/confirm routing red test까지 해소되어 현재 unit 기준선은 green 상태

즉 R0-B는
기반 계약이 깨진 상태에서 하는 forensic이 아니라,
상당히 잠긴 기준선 위에서 수행하는 forensic이다.


## 12. 산출물 목록

이 로드맵이 끝나면 아래 산출물이 있어야 한다.

- recent adverse entry sample list
- normalized forensic table
- family clustering memo
- owner-by-family fix candidate table
- P0 logging/trace requirement memo
- P1 lifecycle follow-up memo


## 13. 우선순위

현재 가장 자연스러운 순서는 아래다.

1. `R0-B1` 샘플 추출
2. `R0-B2` row 매칭
3. `R0-B3` forensic 테이블 정규화
4. `R0-B4` family clustering
5. `R0-B5` 수정 후보 도출
6. `R0-B6` P0/P1 handoff

이 순서가 좋은 이유:

- 먼저 샘플을 고정하고
- row와 체결을 연결하고
- 같은 필드 언어로 읽고
- 반복 family를 찾은 다음
- 마지막에 코드 수정 후보로 내릴 수 있기 때문이다


## 14. 한 줄 결론

R0-B 구현 로드맵의 목적은
최근 adverse entry를
`체결 감각`이 아니라
`R0 기준선을 가진 forensic 표준`
으로 다시 읽게 만드는 것이다.
