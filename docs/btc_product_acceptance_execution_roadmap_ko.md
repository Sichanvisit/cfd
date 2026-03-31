# BTC Product Acceptance Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목표

BTC를 screenshot-driven 방식으로 맞춘다.

우선순위는 아래다.

1. 차트에서 원하는 체크 강도(3/2/1) 맞추기
2. lower buy 남발 없이 해석 가능한 상태 유지
3. 그 다음에만 entry/wait/exit acceptance로 내려가기

## 2. 단계

### BTC0. Baseline Capture

- 사용자 스크린샷을 첫 casebook 샘플로 고정
- 하단 회복 / middle reclaim / upper continuation 구간을 분리 기록

산출물:

- [btc_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_first_capture_casebook_ko.md)

### BTC1. Initial Adjustment Target Freeze

- 첫 패스에서 살릴 장면과 유지할 cadence 규칙을 고정

산출물:

- [btc_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_initial_adjustment_targets_ko.md)

### BTC2. First Display Importance Pass

- `consumer_check_state`에 BTC display importance 연결
- lower recovery / middle reclaim uplift
- upper continuation은 기본 1개 유지
- 기존 cadence suppression은 유지

owner:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

### BTC3. Screenshot Recheck

다음 BTC screenshot에서 아래를 판단한다.

- lower recovery가 충분히 살아났는가
- middle reclaim이 2개로 읽히는가
- upper continuation 남발이 없는가
- lower cadence suppression이 still healthy인가

### BTC4. Second Pass if Needed

필요할 때만 아래를 추가 조정한다.

- middle reclaim uplift 범위 조정
- upper continuation soft cap 추가
- cadence suppression 문맥 분리

### BTC5. Entry / Wait Tie-in

chart acceptance가 어느 정도 닫힌 뒤에만 아래로 내려간다.

- entry acceptance
- wait / hold acceptance
- exit acceptance

## 3. 현재 상태

현재는 `BTC2 first pass 완료 + 2차 미세조정 완료` 상태다.

구현 메모:

- [btc_product_acceptance_first_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_first_adjustment_implementation_memo_ko.md)
- [btc_product_acceptance_second_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\btc_product_acceptance_second_adjustment_implementation_memo_ko.md)

다음 active step은 `BTC3 screenshot recheck`다.
