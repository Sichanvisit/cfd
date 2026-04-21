# Teacher-Label State25 Step 9 상세 기준서
## 목표

Step 9의 목적은
`확보된 labeled seed를 실제 실험 가능한 입력으로 정리하고`
그 위에서 calibration / QA / baseline / confusion tuning을 시작하는 것이다.

이번 단계는 곧바로 execution으로 가는 단계가 아니다.

- Step 8에서 붙은 라벨이 QA gate를 통과했는지 보고
- 현재 seed가 몇 행인지 확인하고
- 자산/패턴/편향 분포를 읽고
- Step E1~E5 중 어디서부터 시작할지 정한다

즉 Step 9의 첫 구현은
`experiment seed report`
를 만드는 것이다.

## 왜 seed report가 먼저 필요한가

지금은 이미

- labeled row 확보
- Step 8 QA gate

까지 끝났다.

하지만 Step 9에서 바로 baseline 모델로 들어가면
현재 seed가

- 충분한지
- 어느 자산에 쏠렸는지
- 어떤 패턴이 과대표집인지
- low-confidence review가 얼마나 남았는지

를 숫자로 먼저 봐야 한다.

그래서 Step 9 첫 owner는 seed report다.

## Step 9 첫 구현 범위

### 1. seed readiness

- `labeled_rows`
- `unlabeled_rows`
- `min_seed_rows`
- `seed_ready`
- `shortfall_rows`

### 2. 분포 요약

- symbol distribution
- primary pattern distribution
- group distribution
- source distribution
- review status distribution
- entry / wait / exit bias distribution

### 3. confidence 요약

- mean
- median
- p10
- p90
- min
- max

### 4. Step 8 gate bridge

- `qa_gate_status`
- `qa_failures`
- `qa_warnings`
- `watchlist_pairs`
- `rare_pattern_warnings`
- `low_confidence_review`

## 구현 owner

- [teacher_pattern_experiment_seed.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_experiment_seed.py)
- [teacher_pattern_experiment_seed_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_experiment_seed_report.py)
- [test_teacher_pattern_experiment_seed.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_teacher_pattern_experiment_seed.py)

## 이번 단계 완료 기준

- seed report builder 추가
- CLI 리포트 추가
- Step 8 QA report와 연결
- `seed_ready` 여부를 바로 판단 가능
- Step 9의 실제 시작점이 `감`이 아니라 `리포트`가 됨

## 다음 단계 연결

이 단계가 닫히면 곧바로

- Step E1 1K 자산별 캘리브레이션
- Step E2 10K full labeling QA

로 내려갈 수 있다.
