# Teacher-Label State25 Labeled Row Acquisition 체크리스트
- [x] runtime accumulation / backfill / hybrid 3갈래 정의
- [x] 기본 권장 전략을 `hybrid`로 고정
- [x] runtime provenance / backfill provenance 구분 규칙 고정
- [x] overwrite 금지 원칙 고정
- [x] bounded backfill dry-run 우선 원칙 고정
- [x] recent `1K -> 2K -> 5K` 확장 원칙 고정
- [x] Step 8 QA re-run을 필수 게이트로 고정
- [x] Step 9 handoff seed 기준 (`1K -> 3K~5K -> 10K`) 고정
- [x] backfill service/script 구현
- [ ] runtime-labeled fresh close 샘플 확보
- [x] bounded backfill dry-run 실행
- [x] bounded backfill apply 실행
- [x] Step 8 QA re-run 결과 기록
- [x] Step 9 seed 확정

## 테스트 묶음

- `tests/unit/test_teacher_pattern_backfill.py`
- `tests/unit/test_teacher_pattern_labeling_qa.py`
- `tests/unit/test_teacher_pattern_labeler.py`

## 테스트 결과

- `pytest -q tests/unit/test_teacher_pattern_backfill.py`
- `pytest -q tests/unit/test_teacher_pattern_labeling_qa.py tests/unit/test_teacher_pattern_labeler.py`

## dry-run 메모

- `python scripts/backfill_teacher_pattern_labels.py --dry-run --limit 1000`
- 현재 recent 1K closed row 기준 `predicted_rows = 841`
- preview distribution은 `1`, `14`, `9` 패턴이 우세했다

## apply / QA re-run 메모

- `python scripts/backfill_teacher_pattern_labels.py --apply --limit 1000`
- backup: [trade_closed_history.backup_teacher_pattern_backfill.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.backup_teacher_pattern_backfill.csv)
- apply 결과:
  - `updated_rows = 841`
  - `skipped_unmatched_rows = 159`
- Step 8 QA re-run 결과:
  - `gate_status = PASS_WITH_WARNINGS`
  - `labeled_rows = 841`
  - `unlabeled_rows = 7743`
  - `warnings = unlabeled_rows_present / rare_pattern_watch_triggered / low_confidence_review_required`
- `python scripts/backfill_teacher_pattern_labels.py --apply --limit 2000`
- backup: [trade_closed_history.backup_teacher_pattern_backfill_1.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.backup_teacher_pattern_backfill_1.csv)
- 2K apply 결과:
  - `updated_rows = 926`
  - `skipped_labeled_rows = 841`
  - `skipped_unmatched_rows = 233`
- 2K 이후 Step 8 QA re-run 결과:
  - `gate_status = PASS_WITH_WARNINGS`
  - `labeled_rows = 1767`
  - `unlabeled_rows = 6818`
  - `warnings = unlabeled_rows_present / rare_pattern_watch_triggered / low_confidence_review_required`
- 현재는 `1K labeled seed` 기준을 넘겨서 Step 9 시작 가능 상태다
