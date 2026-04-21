# Product Acceptance PA2 Teacher Label Entry Acceptance Detailed Reference

## 목적

이 문서는 사용자 스크린샷 3장을 기준으로
`들어갔어야 했는데 시스템이 entry로 못 올린 자리`
를 다시 정의하기 위한 PA2 상세 문서다.

## 핵심 문제

현재 시스템은 실제 진입 발생이 충분하지 않다.
그래서 `must_enter = 0`만으로 entry acceptance가 끝났다고 보기 어렵다.

이번 teacher-label 스크린샷은 아래를 알려준다.

- 실제로 들어갔어야 하는 자리들이 있다
- 그 자리를 시스템은 `observe / wait / hidden`으로 오래 두고 있을 가능성이 있다
- 따라서 PA2는 `queue 0`이 아니라 `teacher-label miss entry` 기준으로 다시 본다

## teacher-label entry 정의

이번 스크린샷 기준 entry는 아래처럼 정의한다.

- 추세 green zone 안 continuation pullback
- support reclaim 이후 재상승 초입
- noise/range가 아니라 추세 방향이 비교적 살아 있는 구간
- top maturity 이후 늦은 chase는 제외
- red zone countertrend bounce의 무리한 재진입도 제외

즉 이번 PA2는
`들어가야 할 자리`를 더 잘 올리고,
`들어가면 안 될 자리`는 계속 막는
두 방향의 정밀도 조정이다.

## symbol reading

### NAS

- green zone continuation에서 missed entry가 있었을 가능성
- top maturity에서는 chase 억제가 필요

### XAU

- 상승 trend continuation에서 entry missed 가능성
- red zone bounce는 entry보다 no-reentry 쪽으로 봐야 함

### BTC

- noise/range가 많아서 entry를 아무데나 늘리면 안 됨
- 따라서 BTC는 `missed entry 복구`보다 `range false-positive 억제`와 같이 봐야 함

## primary owner

- [backend/services/consumer_check_state.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/consumer_check_state.py)
- [backend/services/entry_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [backend/services/entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [backend/trading/chart_flow_policy.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/chart_flow_policy.py)

## evidence owner

- [product_acceptance_chart_capture_casebook_round1_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/product_acceptance_chart_capture_casebook_round1_ko.md)
- [data/trades/entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [data/runtime_status.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json)

## first target question

첫 질문은 이거다.

`teacher label 기준으로는 entry여야 하는데, 현재 시스템은 어느 구간에서 observe/wait에 머물러 있는가`

이 질문에 답하면 그다음부터는

- threshold 문제인지
- promotion 문제인지
- guard 완화 문제인지
- scene 분류 문제인지

를 나눠서 볼 수 있다.
