# BF7 Close-Out and Handoff Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 BF7을 실제 실행 가능한 순서로 정리한다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf7_close_out_handoff_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_bf7_close_out_handoff_detailed_reference_ko.md)

## 2. 실행 순서

```text
BF7-A. BF1~BF6 inventory freeze
-> BF7-B. SF6 + BF6 evidence synthesis
-> BF7-C. close-out summary
-> BF7-D. handoff lanes fix
-> next. product_acceptance_common_state_aware_display_modifier_v1
```

## 3. BF7-A. inventory freeze

해야 할 일:

1. BF1~BF6가 실제로 구현됐는지 inventory row로 고정
2. 각 bridge의 target_area / output_surface / handoff_role을 남김

## 4. BF7-B. evidence synthesis

해야 할 일:

1. SF6 close-out latest를 읽음
2. BF6 projection latest를 읽음
3. projection match ratio와 next action evidence를 같이 묶음

## 5. BF7-C. close-out summary

해야 할 일:

1. implemented bridge count 고정
2. broad raw add defer 판단 재확인
3. BF 트랙이 BF6까지 닫혔음을 공식화

## 6. BF7-D. handoff lanes fix

해야 할 일:

1. product acceptance next action 고정
2. forecast re-review next action 고정
3. collector follow-up을 좁게 제한

## 7. 현재 상태

BF7은 구현 완료 상태다.

기준 산출물:

- [bridge_first_bf7_close_out_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\state_forecast_validation\bridge_first_bf7_close_out_latest.json)

현재 recommended next step:

- `product_acceptance_common_state_aware_display_modifier_v1`
