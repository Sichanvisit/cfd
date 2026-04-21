# Current Position-Side Checkpoint Backfill Detailed Plan

## 목적

이 문서는 `PA5 dataset`을 실제 position-side row로 살찌우기 위한 open-trade backfill 계획이다.

현재 문제는 checkpoint 파이프라인은 열렸지만,
저장된 row 대부분이 `bootstrap flat row`라는 점이다.

그래서 이번 보강의 목표는 아래 하나다.

> `runtime_status.detail.json`의 최신 signal row와 `trades.db(open_trades)`를 결합해서,
> 실제 open position을 반영한 checkpoint row를 offline/log-only로 추가 생성하기

---

## 왜 이 보강이 필요한가

지금 `PA5 checkpoint_action_eval_latest.json`은

- `position_side_row_count = 0`
- `WAIT = 3`

으로 나왔다.

즉 파이프라인은 맞게 열렸지만,
`HOLD / PARTIAL / FULL_EXIT / REBUY`를 배울 수 있는 active position row가 부족하다.

이 상태에서 바로 `PA6 resolver`를 올리면 구조는 맞아도 실제 데이터가 너무 빈다.

---

## 구현 방식

### 입력 3개

- `data/runtime_status.detail.json`
  - symbol별 최신 signal row
- `data/trades/trades.db`
  - `open_trades`
- `data/runtime/checkpoint_rows.csv`
  - 기존 checkpoint state continuity

### 출력

- `checkpoint_rows.csv`에 `source=open_trade_backfill` row append
- `checkpoint_rows.detail.jsonl`에 detail append
- `data/analysis/shadow_auto/checkpoint_open_trade_backfill_latest.json`

### 핵심 규칙

- live action은 전혀 바꾸지 않는다
- 기존 row를 수정하지 않고 새 row만 append한다
- 같은 `(source, ticket, runtime_snapshot_key)` 조합은 중복 append하지 않는다
- leg / checkpoint continuity는 기존 `checkpoint_rows.csv` 마지막 상태를 이어받는다

---

## 기대 효과

- `position_side_row_count`가 0에서 벗어난다
- PA5 resolved dataset에 `WAIT` 말고 다른 hindsight 후보가 생길 수 있다
- PA6 resolver를 bootstrap 기준으로 올려도 덜 비게 된다

---

## 완료 기준

- open trade가 있을 때 `open_trade_backfill` row가 생성된다
- 새 row는 `position_side != FLAT`를 가진다
- PA5 dataset/eval을 다시 빌드하면 `position_side_row_count`가 증가한다
