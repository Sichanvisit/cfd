# Teacher-Label State25 Labeled Row Acquisition 메모

## 메모

- Step 8에서 QA gate는 닫혔지만, full backlog는 여전히 unlabeled일 수 있다.
- 이건 QA gate 실패가 아니라 `라벨 부착 시점이 backlog보다 늦은 상태`라는 뜻이다.
- 그래서 Step 9 전에는 반드시 `labeled row acquisition`이 필요하다.

## 왜 hybrid를 기본으로 두는가

- runtime accumulation만 기다리면 가장 안전하지만 느리다
- full backfill을 바로 하면 빠르지만 provenance가 거칠어질 수 있다
- 최근 bounded backfill + fresh runtime 조합이 속도와 안정성의 균형이 가장 좋다

## 이번 단계에서 절대 지킬 것

- 이미 채워진 `teacher_pattern_*`는 backfill이 덮지 않는다
- runtime source와 backfill source를 섞지 않는다
- full backlog를 처음부터 무조건 재기록하지 않는다
- 매 단계 뒤 Step 8 QA gate를 다시 돈다

## 다음 구현 owner

- 라벨러 재사용: [teacher_pattern_labeler.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeler.py)
- schema/normalize: [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)
- QA gate: [teacher_pattern_labeling_qa.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_labeling_qa.py)
- 예상 신규 owner:
  - `backend/services/teacher_pattern_backfill.py`
  - 또는 `scripts/backfill_teacher_pattern_labels.py`

## 다음 자연스러운 구현 순서

1. backfill 상세/구현 로드맵 고정
2. backfill service/script 구현
3. dry-run
4. bounded apply
5. Step 8 QA re-run
6. Step 9 handoff

## 현재 구현 상태

- [teacher_pattern_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_backfill.py) 에 bounded backfill service를 추가했다.
- [backfill_teacher_pattern_labels.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/backfill_teacher_pattern_labels.py) 에 dry-run/apply CLI를 추가했다.
- recent 1K dry-run에서는 `841`건이 라벨 부착 후보로 잡혔다.
- recent 1K bounded apply도 실제로 실행했고 `841`건이 backfill되었다.
- 이어서 recent 2K bounded apply까지 실행했고 총 `labeled_rows = 1767` 까지 확보했다.
- Step 8 QA re-run 결과는 `PASS_WITH_WARNINGS`, `labeled_rows = 1767`, `unlabeled_rows = 6818` 이다.
- 즉 현재는 1차 handoff 기준인 `1K labeled rows`를 넘긴 상태라 Step 9를 시작할 수 있다.
- 남은 경고는:
  - unlabeled backlog가 아직 많음
  - rare pattern이 아직 안 잡힘
  - low-confidence review target이 남아 있음
- 따라서 Step 9는 `시작 가능`, 다만 `초기 seed 실험`으로 보는 것이 맞다.
