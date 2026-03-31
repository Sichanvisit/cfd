# XAU Product Acceptance Execution Roadmap

작성일: 2026-03-30 (KST)

## 1. 목표

XAU를 NAS와 같은 screenshot-driven 방식으로 맞춘다.

우선순위는 아래다.

1. 차트에서 원하는 체크 강도(3/2/1) 맞추기
2. 과표시 없이 해석 가능한 상태 유지
3. 그 다음에만 entry/wait/exit acceptance로 내려가기

## 2. 단계

### XAU0. Baseline Capture

- 사용자 스크린샷을 첫 casebook 샘플로 고정
- 하단 회복 / second support / upper reject 구간을 분리 기록

산출물:

- [xau_product_acceptance_first_capture_casebook_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_first_capture_casebook_ko.md)

### XAU1. Initial Adjustment Target Freeze

- 첫 패스에서 살릴 장면과 건드리지 않을 억제 규칙을 고정

산출물:

- [xau_product_acceptance_initial_adjustment_targets_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_initial_adjustment_targets_ko.md)

### XAU2. First Display Importance Pass

- `consumer_check_state`에 XAU display importance 연결
- lower recovery / second support / upper reject 핵심 장면 uplift
- 기존 guard wait hidden과 cadence suppression은 유지

owner:

- [consumer_check_state.py](C:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py)

### XAU3. Screenshot Recheck

다음 XAU screenshot에서 아래를 판단한다.

- lower recovery가 충분히 살아났는가
- second support가 2개 수준으로 읽히는가
- upper reject가 필요한 곳만 보이는가
- 남발이 생기지 않았는가

### XAU4. Second Pass if Needed

필요할 때만 아래를 추가 조정한다.

- upper mature continuation soft cap
- xau upper reject cadence 완화/강화
- middle anchor cadence의 문맥별 차등 처리

### XAU5. Entry / Wait Tie-in

chart acceptance가 어느 정도 닫힌 뒤에만 아래로 내려간다.

- entry acceptance
- wait / hold acceptance
- exit acceptance

## 3. 현재 상태

현재는 `XAU2 first pass 완료 + state-aware 2차 soft-cap 완료` 상태다.

구현 메모:

- [xau_product_acceptance_first_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_first_adjustment_implementation_memo_ko.md)
- [xau_product_acceptance_second_adjustment_implementation_memo_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\xau_product_acceptance_second_adjustment_implementation_memo_ko.md)

다음 active step은 `XAU3 screenshot recheck`다.
