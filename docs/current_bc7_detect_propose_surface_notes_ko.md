# BC7 `/detect -> /propose` surface 메모

## 현재 기준으로 `/detect`에서 보이는 것

BC7이 반영된 뒤에는 `candle/weight detector`에서 아래 후보가 surface될 수 있다.

- `state25 context bridge weight review 후보`
- `state25 context bridge threshold review 후보`

즉 state25 context bridge가 단순 runtime trace에만 머무르지 않고, detector review 후보로 같이 보이기 시작한다.

## 현재 기준으로 `/propose`에서 보이는 것

`/propose` 본문에는 기존 섹션과 함께 threshold review 섹션이 추가될 수 있다.

- `state25 context bridge threshold review 후보:`

여기에는 보통 아래 정보가 함께 붙는다.

- requested / effective threshold points
- context summary
- reason keys
- decision counterfactual (`without -> with`)
- failure / guard

## 해석

- `weight review 후보`
  - state25 weight pair를 어떻게 log-only로 옮길지 보는 backlog
- `threshold review 후보`
  - state25 threshold harden이 어떤 장면에서 의미가 있는지 보는 backlog

## 운영 팁

가장 읽기 좋은 순서는 여전히 같다.

1. `/detect`
2. `/propose`

이 순서로 보면 detector에서 surface된 state25 bridge 후보가 proposal backlog에서 어떤 review 후보로 정리되는지 이어서 읽을 수 있다.
