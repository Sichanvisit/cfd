# State25 Detail Micro Backfill 체크리스트

- [x] runtime `log_entry(...)`에 `entered_row.micro_*` carry helper 추가
- [x] helper 단위 테스트 추가
  - [test_entry_try_open_entry_probe.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_try_open_entry_probe.py)
- [x] detail-driven richer backfill service 추가
  - [teacher_pattern_detail_micro_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_detail_micro_backfill.py)
- [x] CLI script 추가
  - [backfill_teacher_pattern_detail_micro.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/backfill_teacher_pattern_detail_micro.py)
- [x] unit test 추가
  - [test_teacher_pattern_detail_micro_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_teacher_pattern_detail_micro_backfill.py)
- [x] dry-run 검증 수행
- [x] over-match 방지 위해 strong key만 허용
- [x] `body_size_pct_20` point->percent 정규화 보정
- [x] 실데이터 coverage 한계 기록

## 현재 상태
- 구현: 완료
- 테스트: 완료
- 실데이터 bounded apply: `0 match`로 보류
- 다음 주력: runtime fresh labeled close 축적
