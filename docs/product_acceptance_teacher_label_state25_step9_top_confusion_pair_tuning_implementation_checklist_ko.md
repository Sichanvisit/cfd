# Teacher-Label State25 Step 9-E4 Top Confusion Pair Tuning 체크리스트

- [x] current pilot baseline top confusion을 실제 seed 기준으로 확인
- [x] group confusion `A -> D`를 우선순위로 고정
- [x] pattern confusion `1 -> 5`를 우선순위로 고정
- [x] watchlist pair `12-23`, `5-10`, `2-16`는 현재 `observe_only`로 유지
- [x] `teacher_pattern_confusion_tuning.py` 추가
- [x] `teacher_pattern_confusion_tuning_report.py` 추가
- [x] `teacher_pattern_labeler.py`에 1/5/13/14 fallback 보정 반영
- [x] `teacher_pattern_backfill.py`에 relabel provenance 추가
- [x] recent `2K` bounded relabel 실제 적용
- [x] pilot baseline 재실행
- [x] confusion tuning report 재실행
- [x] unit test 추가 및 통과

## 현재 판단

- E4 구현은 완료
- 현재 seed에선 confusion ranking이 `A->D`, `1->5`로 고정됨
- watchlist pair는 아직 실제 관측이 거의 없어 조정 단계보다 관찰 단계
- execution handoff 전 단계로는 아직 이르며 labeled row 추가 누적이 더 필요
