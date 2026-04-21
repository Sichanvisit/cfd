# Teacher-Label State25 Labeled Row Acquisition 실행 로드맵
## 목표

Step 8 이후 Step 9로 넘어가기 전에
`teacher_pattern_* labeled row`
를 실제로 확보하는 실행 순서를 정리한다.

## 기본 원칙

- 기본 전략은 `hybrid`
- runtime accumulation은 유지
- backfill은 bounded seed부터 시작
- Step 8 QA gate를 매 단계마다 다시 돈다

## Step L0. 범위 고정

고정할 것:

- source dataset: [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
- runtime source: 현재 open snapshot -> close carry 경로
- 1차 seed 목표: `1K labeled rows`
- overwrite 금지: 기존 non-empty `teacher_pattern_*`는 덮지 않음

## Step L1. runtime accumulation baseline 확인

목표:

- 지금 runtime 경로에서 새 close row가 실제로 teacher-pattern을 carry하는지 확인

owner:

- [trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger_open_snapshots.py)
- [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py)

산출물:

- fresh close row 샘플 확인
- Step 8 QA report에 runtime-labeled row가 들어오는지 확인

## Step L2. bounded backfill dry-run

목표:

- 최근 `1K~2K` closed row에 대해
- 실제 write 없이 몇 row가 backfill 가능한지 미리 본다

owner 후보:

- 새 service 또는 script
- 권장 파일: `backend/services/teacher_pattern_backfill.py`
  또는 `scripts/backfill_teacher_pattern_labels.py`

산출물:

- candidate rows
- skipped rows
- already-labeled rows
- predicted label distribution
- provenance plan

## Step L3. bounded backfill apply

목표:

- dry-run이 괜찮으면 최근 bounded window에만 실제 적용

규칙:

- existing non-empty teacher fields는 유지
- source/review status는 backfill 전용 값 사용
- write target은 canonical closed-history

권장 시작:

- recent `1K`
- 이후 `2K`

## Step L4. Step 8 QA re-run

목표:

- backfill 후 QA gate를 다시 돌려
  - `labeled_rows > 0`
  - provenance 분리
  - watchlist pair 분포
  - rare pattern 경고
  를 확인

통과 기준:

- hard fail 없음
- labeled row 확보
- provenance 누락 없음

## Step L5. Step 9 handoff seed 확정

목표:

- Step 9에 넘길 첫 dataset seed를 확정

권장 초기 seed:

- backfill recent window + fresh runtime row 합본
- 1차 기준: `1K labeled rows`
- 2차 기준: `3K~5K`
- 3차 기준: `10K`

## 추천 실제 운영 순서

1. runtime accumulation 유지
2. recent 1K dry-run
3. recent 1K bounded apply
4. Step 8 QA re-run
5. 필요 시 recent 2K 확장
6. Step 9 experiment tuning 시작

## 이 로드맵의 의미

이 문서는 `full backlog를 한 번에 밀어붙이자`가 아니라
`seed를 작게, provenance는 분리해서, QA를 통과시키며 늘려가자`
는 운영 원칙을 고정하는 문서다.
