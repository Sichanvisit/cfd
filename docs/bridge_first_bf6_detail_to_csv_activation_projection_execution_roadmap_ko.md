# BF6 Detail-to-CSV Activation Projection Execution Roadmap

작성일: 2026-03-31 (KST)

## 1. 목적

이 문서는 BF6를 실제 실행 가능한 순서로 쪼갠다.

상세 기준은 아래 문서를 따른다.

- [bridge_first_bf6_detail_to_csv_activation_projection_detailed_reference_ko.md](C:\Users\bhs33\Desktop\project\cfd\docs\bridge_first_bf6_detail_to_csv_activation_projection_detailed_reference_ko.md)

## 2. 실행 순서

```text
BF6-A. projection contract freeze
-> BF6-B. detail row sampler / matcher
-> BF6-C. activation slice projection
-> BF6-D. section value projection
-> BF6-E. latest report / memo
-> BF7. close-out and handoff
```

## 3. BF6-A. projection contract freeze

해야 할 일:

1. `value owner = CSV row`
2. `activation / usage owner = detail trace`
3. match 순서를 `decision_row_key -> replay_row_key -> time tuple`로 고정

완료 기준:

- projection contract가 코드와 문서에서 같은 말로 고정된다.

## 4. BF6-B. detail row sampler / matcher

해야 할 일:

1. detail source sample loader 구현
2. CSV normalized row loader 재사용
3. exact / fallback / unmatched 분류 구현

완료 기준:

- match coverage와 unmatched reason이 latest report에 남는다.

## 5. BF6-C. activation slice projection

해야 할 일:

1. detail derived `advanced_input_activation_state`를 CSV value row에 projection
2. order_book state도 projection
3. metric slice rows 생성

완료 기준:

- activation slice projection latest가 나온다.

## 6. BF6-D. section value projection

해야 할 일:

1. detail grouped usage를 section flag로 투영
2. branch/section별 separation delta surface 생성

완료 기준:

- `transition_branch / trade_management_branch` 둘 다 section value projection row가 나온다.

## 7. BF6-E. latest report / memo

해야 할 일:

1. JSON/CSV/MD 산출물 생성
2. BF6 memo 작성
3. 실데이터 기준 latest 해석 고정

완료 기준:

- BF6 latest report와 implementation memo가 함께 남는다.

## 8. 현재 상태

BF6는 구현 완료 상태다.

latest 기준:

- `sampled_detail_rows = 3695`
- `matched_projection_rows = 3664`
- `projection_match_ratio = 0.9916`
- `recommended_next_step = BF7_close_out_and_handoff`

즉 현재 active step은 BF6 자체가 아니라 `BF7 close-out and handoff`다.
