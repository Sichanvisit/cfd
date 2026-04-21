# Teacher-Label State25 Step 9-E5 Execution Handoff Gate Checklist

## 목적

Step 9-E5 execution handoff gate 구현 체크리스트.

## 입력 계약

- [ ] asset calibration report 입력 지원
- [ ] full labeling QA report 입력 지원
- [ ] pilot baseline report 입력 지원
- [ ] confusion tuning report 입력 지원

## gate 로직

- [ ] `READY / READY_WITH_WARNINGS / NOT_READY` 3상태 지원
- [ ] labeled seed shortfall blocker 구현
- [ ] primary coverage blocker 구현
- [ ] supported pattern count blocker 구현
- [ ] baseline readiness / skipped / macro F1 blocker 구현
- [ ] high severity confusion blocker 구현
- [ ] group skew / rare pattern / watchlist sparse warning 처리 구현

## 출력

- [ ] snapshot 요약 포함
- [ ] upstream status 포함
- [ ] blockers 목록 포함
- [ ] warnings 목록 포함
- [ ] unresolved confusion 목록 포함
- [ ] recommended action 목록 포함

## 스크립트

- [ ] report CLI 추가
- [ ] closed-history CSV 입력 지원
- [ ] baseline metrics JSON 입력 지원
- [ ] E1/E2/E4를 script 내부에서 다시 조합 가능

## 테스트

- [ ] READY 케이스 테스트
- [ ] NOT_READY blocker 케이스 테스트
- [ ] READY_WITH_WARNINGS 케이스 테스트

## 완료 조건

- [ ] Step 9-E5 report가 현재 seed에 대해 실행됨
- [ ] 현재 seed에 대한 execution handoff 상태가 문서/메모에 기록됨

## Deferred Recheck / Watch List

- [ ] 지금부터의 메인은 `10K labeled seed 누적 + watchlist pair 관찰 + E5 재확인 타이밍 관리`
- [ ] `labeled row 2500+`, `supported pattern count 증가`, `covered primary 8+`는 이미 충족된 과거 milestone으로 기록
- [ ] fresh closed row `+100` 이상 증가 시 Step 9 watch report 기준으로 E4/E5 재확인
- [ ] watchlist pair `12-23`, `5-10`, `2-16` 중 하나라도 `0 -> positive count`로 전환되면 E4/E5 재확인
- [ ] 현재 직접 blocker가 `full_qa_seed_shortfall` 1개인지 계속 확인
- [ ] `teacher_pattern_step9_watch_report.py` 출력으로 `rows_to_target`, `new_watchlist_pairs`, `blocker_codes`를 같이 추적
- [ ] `runtime recycle`은 먼저 `log_only` 한 사이클 관찰
- [ ] `runtime_recycle.last_reason / last_block_reason / log_only_count` 확인
- [ ] 한 사이클 관찰 전에는 `RUNTIME_RECYCLE_MODE=reexec` 전환 보류
- [ ] 위 조건 전에는 `NOT_READY` 상태를 유지하고 seed accumulation / live observation 중심으로 진행
