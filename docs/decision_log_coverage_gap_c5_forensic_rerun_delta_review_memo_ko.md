# Decision Log Coverage Gap C5 Forensic Rerun Delta Review Memo

작성일: 2026-03-30 (KST)

## 1. 목적

이 문서는 `decision_log_coverage_gap` 트랙의 `C5 forensic rerun + delta review` 결과를 고정하기 위한 메모다.

핵심 질문은 이것이다.

`C4 backfill 이후 B2/B3/B4/B5를 다시 돌렸을 때 coverage gap이 실제로 줄었는가, 아니면 provenance만 좋아졌는가?`

## 2. 구현 파일

- [decision_log_coverage_gap_forensic_rerun_delta_review.py](C:\Users\bhs33\Desktop\project\cfd\scripts\decision_log_coverage_gap_forensic_rerun_delta_review.py)
- [test_decision_log_coverage_gap_forensic_rerun_delta_review.py](C:\Users\bhs33\Desktop\project\cfd\tests\unit\test_decision_log_coverage_gap_forensic_rerun_delta_review.py)

## 3. 산출물

- [decision_log_coverage_gap_c5_delta_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c5_delta_latest.json)
- [decision_log_coverage_gap_c5_delta_latest.csv](C:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c5_delta_latest.csv)
- [decision_log_coverage_gap_c5_delta_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c5_delta_latest.md)
- [decision_log_coverage_gap_c5_before_snapshot.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c5_before_snapshot.json)

## 4. 현재 결과

최신 rerun delta는 아래처럼 고정됐다.

- `rerun_state = archive_provenance_improved_but_gap_unchanged`
- `recommended_next_step = C6_close_out_handoff`
- `archive_source_delta = 1`
- `matched_rows_delta = 0`
- `unmatched_outside_coverage_delta = 0`
- `coverage_gap_rows_delta = 0`
- `manual_review_rows_delta = 0`

before/after에서 실제로 바뀐 것은 주로 provenance 쪽이다.

- `decision_source_count: 3 -> 5`
- `archive_source_count: 0 -> 1`
- `rows_scanned: 22027 -> 26378`
- `coverage_latest_time: 2026-03-29T23:41:00 -> 2026-03-30T01:47:58`

반면 forensic 핵심 지표는 그대로였다.

- `matched_rows: 7 -> 7`
- `unmatched_outside_coverage: 23 -> 23`
- `coverage_gap_rows: 23 -> 23`
- `top_family: decision_log_coverage_gap -> decision_log_coverage_gap`
- `top_candidate_family: decision_log_coverage_gap -> decision_log_coverage_gap`

이번 C5부터는 rerun을 반복해도 같은 기준으로 비교되도록 frozen baseline snapshot을 먼저 읽는다.

- `baseline_snapshot_source = frozen_snapshot`
- baseline path:
  [decision_log_coverage_gap_c5_before_snapshot.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\decision_log_coverage_gap\decision_log_coverage_gap_c5_before_snapshot.json)

## 5. 해석

이번 C5의 결론은 분명하다.

- C4에서 archive/manifests provenance는 실제로 강화됐다.
- 하지만 그 강화가 현재 forensic coverage gap을 줄이지는 못했다.
- 따라서 지금 남은 gap은 `reader 부족`이나 `archive awareness 부족`이 아니라, 현재 workspace 안에 없는 historical decision coverage 공백으로 해석하는 것이 맞다.

즉 C5는 `계속 내부 로직을 더 붙이면 gap이 줄어들 것`이라는 가정을 약화시켰다.

현재 더 자연스러운 해석은 이것이다.

`내부 archive provenance는 충분히 강화되었고, 남은 gap은 외부 backfill 또는 historical source 부재 문제다.`

## 6. 테스트 기준선

검증 기준선은 아래다.

- `test_decision_log_coverage_gap_forensic_rerun_delta_review.py`: 신규 통과
- C5 실제 rerun 실행 성공
- 이후 전체 unit suite 재검증 예정

## 7. 다음 단계

다음 단계는 `C6 close-out + handoff`다.

C6에서 고정해야 할 핵심은 세 가지다.

1. `decision_log_coverage_gap` 트랙에서 내부적으로 개선 가능한 영역은 어디까지 닫혔는가
2. 아직 남은 gap을 `external / unavailable historical source gap`으로 공식 해석할 수 있는가
3. 이후 P1/P2 또는 다음 운영 트랙으로 어떤 전제로 넘길 것인가
