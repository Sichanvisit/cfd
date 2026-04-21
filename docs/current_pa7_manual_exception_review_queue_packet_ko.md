# Current PA7 Manual Exception Review Queue Packet

## 목적

PA7에서 필요한 것은
manual exception이 많다는 사실 자체가 아니라,
어떤 family와 action 조합이 review 우선순위가 높은지 바로 보이는 review packet이다.

이 packet은 다음 질문에 답하기 위해 만든다.

- 어떤 symbol이 manual exception을 가장 많이 만들고 있는가
- 어떤 surface/checkpoint/family 조합이 반복적으로 review에 걸리는가
- baseline action과 hindsight best action이 어디서 가장 자주 어긋나는가

## 입력

- `checkpoint_dataset_resolved.csv`

## 출력

- `checkpoint_pa7_review_queue_packet_latest.json`

## packet 구조

- `summary`
  - 전체 resolved row 수
  - manual exception row 수
  - top symbol
  - top hindsight label
- `group_rows`
  - review 우선순위 group
  - 각 group의 row 수
  - hold/partial/full_exit 관련 평균 score
  - 대표 sample row 3개

## review 우선순위 해석

- row 수가 많고
- scene confidence가 높고
- hindsight와 baseline action이 반복적으로 엇갈리면
  우선 review 대상이다

## 운영 원칙

- PA7은 사람 검토를 위한 packet이다
- SA8 live adoption 판단과는 분리한다
- SA8은 scene disagreement와 preview-only 상태가 더 줄어야 진행한다
