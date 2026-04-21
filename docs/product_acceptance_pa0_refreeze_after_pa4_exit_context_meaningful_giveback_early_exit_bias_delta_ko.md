# Product Acceptance PA0 Refreeze After PA4 Exit Context Meaningful Giveback Early Exit Bias Delta

## baseline

기준 artifact:

- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json)

latest `generated_at`:

- `2026-04-01T20:19:56`

## summary

이번 refreeze 기준:

- `must_hold = 1`
- `must_release = 10`
- `bad_exit = 10`

즉 숫자는 즉시 줄지 않았다.

## why unchanged

이번 PA4-2는 `closed-trade retrospective filter`를 바꾼 게 아니라
future close 시점의 `profit-path utility bias`를 조정한 패치다.

그래서 이미 저장된 closed history queue는 그대로 남고,
효과 확인은 다음 fresh close artifact가 들어온 뒤에 가능하다.

## next check

다음 follow-up은 아래를 보면 된다.

- fresh close row에서 `meaningful_giveback_exit_pressure` 축이 실제로 더 이른 close로 정리되는지
- `Exit Context + meaningful peak + giveback` family가 `must_release / bad_exit` 상단에서 줄어드는지
