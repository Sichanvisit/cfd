# Decision Log Coverage Gap C6 Close-Out Handoff

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `decision_log_coverage_gap` 트랙의 `C6 close-out + handoff`를 공식적으로 고정하기 위한 문서다.

핵심 질문은 이것이다.

`우리가 내부 코드와 운영 범위 안에서 줄일 수 있는 coverage gap은 어디까지 닫혔고, 무엇이 외부 historical source 공백으로 남았는가?`

## 2. 트랙 요약

이번 coverage 트랙에서 수행한 단계는 아래와 같다.

- `C0 baseline freeze`
- `C1 source inventory / retention matrix`
- `C2 coverage audit report`
- `C3 archive generation hardening`
- `live rollover execution`
- `C4 targeted backfill execution`
- `C5 forensic rerun + delta review`

관련 핵심 문서:

- [decision_log_coverage_gap_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_detailed_reference_ko.md)
- [decision_log_coverage_gap_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_execution_roadmap_ko.md)
- [decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c4_targeted_backfill_memo_ko.md)
- [decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\decision_log_coverage_gap_c5_forensic_rerun_delta_review_memo_ko.md)

## 3. 이번 트랙에서 실제로 닫힌 것

이번 C 트랙으로 내부적으로 닫힌 것은 아래와 같다.

1. reader/matcher 한계와 source 부재를 구분할 수 있게 됐다.
2. `entry_decisions` active/manual/runtime 경로가 공통 rollover/archive helper를 사용하게 됐다.
3. live rollover를 실제로 실행해서 archive parquet / entry manifests를 생성했다.
4. internal historical source 2개를 targeted backfill로 archive/manifests에 올렸다.
5. rerun을 반복해도 기준이 흔들리지 않도록 C5 frozen baseline snapshot을 고정했다.

즉 이제는
`reader가 못 읽는 것인지`
와
`workspace 안에 historical coverage가 실제로 없는 것인지`
를 분리해서 말할 수 있다.

## 4. 끝까지 남은 것

최신 C5 기준:

- `rerun_state = archive_provenance_improved_but_gap_unchanged`
- `archive_source_delta = 1`
- `matched_rows_delta = 0`
- `coverage_gap_rows_delta = 0`
- `top_family = decision_log_coverage_gap`

이 의미는 분명하다.

- provenance는 좋아졌다.
- 내부 archive/manifest/reader path도 강화됐다.
- 하지만 현재 adverse-entry forensic gap은 줄지 않았다.

따라서 현재 남은 문제는
`미해결 internal logic bug`
가 아니라
`external / unavailable historical coverage gap`
으로 읽는 것이 맞다.

## 5. 공식 해석

이번 C6에서 고정하는 공식 해석은 아래와 같다.

### 5-1. 닫힌 해석

- `decision_log_coverage_gap`은 더 이상 “reader path 부족” 문제로 보지 않는다.
- `decision_log_coverage_gap`은 더 이상 “archive hardening 미구현” 문제로 보지 않는다.
- `decision_log_coverage_gap`은 더 이상 “internal targeted backfill 미수행” 문제로 보지 않는다.

### 5-2. 남는 해석

- 현재 남은 gap은 `현재 workspace에 없는 historical decision coverage` 가능성이 높다.
- 따라서 이 gap은 내부 코드만 더 붙인다고 줄어들 문제로 보지 않는다.
- 이후 이 gap을 줄이려면 외부 historical source 확보 또는 별도 backfill source 확보가 필요하다.

## 6. acceptance

이번 close-out은 아래 조건을 만족하므로 완료로 본다.

1. C0~C5 산출물과 해석이 문서로 고정되어 있다.
2. internal archive/manifest/rollover hardening이 코드로 구현되어 있다.
3. live rollover 실행까지 완료되었다.
4. targeted internal backfill이 실제 실행되었다.
5. C5 rerun delta 결과가 안정적으로 재현된다.
6. 전체 unit 기준선이 green이다.

## 7. handoff

이제 다음 단계는 두 갈래로 나뉜다.

### 운영 갈래

- 외부 historical source를 구할 수 있으면 별도 backfill 트랙으로 이어간다.
- 외부 source가 없으면 현재 gap을 명시적 coverage limitation으로 유지한다.

### 상위 로드맵 갈래

- `P1 lifecycle correlation observability`
- `P2 expectancy / attribution observability`

단, handoff 조건은 명확하다.

- coverage가 있는 window와 coverage가 없는 window를 분리해서 읽는다.
- `unknown`으로 뭉개지 말고 `outside_coverage`를 명시적 상태로 유지한다.
- P1/P2 분석은 coverage-in-scope 표본과 coverage-out-of-scope 표본을 섞지 않는다.

## 8. 다음 액션

가장 자연스러운 다음 액션은 아래 둘 중 하나다.

1. 외부 historical decision source를 확보할 수 있으면 별도 backfill 실행
2. 그게 아니면 coverage limitation을 명시한 상태로 `P1 lifecycle correlation` 시작

현재 기준으로는 `C 트랙 자체는 close-out 가능 상태`다.

## 9. 한 줄 결론

`decision_log_coverage_gap` 트랙은 내부 코드와 운영 경로 기준으로는 충분히 닫혔다. 지금 남은 것은 더 많은 내부 튜닝이 아니라, workspace 밖 historical source availability 문제다.

## 10. Next Canonical P-Track Docs

After this close-out, the main upward references are:

- [profitability_operations_p_track_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_detailed_reference_ko.md)
- [profitability_operations_p_track_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p_track_execution_roadmap_ko.md)

The practical next start remains:

- small `P0` foundation work
- then `P1 lifecycle correlation observability`

Current P1 references:

- [profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_detailed_reference_ko.md)
- [profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\profitability_operations_p1_lifecycle_correlation_execution_roadmap_ko.md)
