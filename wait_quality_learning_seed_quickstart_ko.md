# Wait Quality Learning Seed Quickstart

## 이 문서는 언제 보나

이 문서는 `좋은 기다림 / 나쁜 기다림` 판정을
실제 `trade_closed_history.csv` 학습용 표본에 붙이고 싶을 때 봅니다.

쉽게 말하면 아래 질문에 답할 때 쓰는 문서입니다.

- replay 보고서에서 본 `better_entry_after_wait`를 학습 데이터에도 남기고 싶다
- 지금 state25 seed에 `entry_wait_quality_*`가 얼마나 붙어 있는지 보고 싶다
- WQ4가 실제 CSV까지 반영됐는지 확인하고 싶다

## 제일 짧은 실행 순서

1. 먼저 wait replay 보고서를 최신으로 만듭니다.

```powershell
python scripts/fetch_mt5_future_bars.py
python scripts/entry_wait_quality_replay_report.py
```

2. 그다음 closed history에 학습용 컬럼을 붙입니다.

```powershell
python scripts/backfill_entry_wait_quality_learning_seed.py
```

3. 마지막으로 seed 보고서를 다시 만듭니다.

```powershell
python scripts/teacher_pattern_experiment_seed_report.py
```

4. pilot baseline 쪽 연결 상태도 보고 싶으면 이 명령을 돌립니다.

```powershell
python scripts/teacher_pattern_pilot_baseline_report.py
```

## 각 명령이 하는 일

### 1. `entry_wait_quality_replay_report.py`

이 명령은 최근 wait row를 다시 읽어서
`좋은 기다림 / 나쁜 기다림`을 먼저 판정합니다.

사람이 읽을 요약은 이 파일에 생깁니다.

- [entry_wait_quality_replay_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.md)

원본 JSON은 이 파일입니다.

- [entry_wait_quality_replay_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.json)

### 2. `backfill_entry_wait_quality_learning_seed.py`

이 명령은 방금 만든 replay 결과를 읽어서
`trade_closed_history.csv`에 아래 세 컬럼을 붙입니다.

- `entry_wait_quality_label`
- `entry_wait_quality_score`
- `entry_wait_quality_reason`

처음 적용할 때는 backup도 같이 남깁니다.

예:

- [trade_closed_history.backup_entry_wait_quality_enrichment.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.backup_entry_wait_quality_enrichment.csv)

먼저 미리보기만 보고 싶으면 이렇게 씁니다.

```powershell
python scripts/backfill_entry_wait_quality_learning_seed.py --dry-run
```

### 3. `teacher_pattern_experiment_seed_report.py`

이 명령은 state25 seed 보고서를 다시 만들고,
`entry_wait_quality_*`가 실제 labeled seed에 얼마나 붙었는지 보여줍니다.

지금은 아래 항목을 보면 됩니다.

- `entry_wait_quality_distribution`
- `entry_wait_quality_coverage`

### 4. `teacher_pattern_pilot_baseline_report.py`

이 명령은 state25 baseline 보고서를 다시 만들고,
wait quality가 pilot baseline에 실제로 어떻게 연결돼 있는지 보여줍니다.

지금은 아래 두 곳만 보면 됩니다.

- `wait_quality_integration`
- `tasks.wait_quality_task`

읽는 법은 간단합니다.

- `wait_quality_integration.ready = true`
  - wait quality auxiliary target을 실제로 학습해볼 준비가 됨

- `wait_quality_integration.ready = false`
  - 구조는 붙었지만 아직 표본이 부족함

- `tasks.wait_quality_task.skipped = true`
  - 아직 label class가 충분히 안 모였음

- `tasks.wait_quality_task.skipped = false`
  - 이제 entry-time feature로 좋은 기다림 / 나쁜 기다림을 예측하는 auxiliary task가 실제로 열림

## 지금 기준으로 어떻게 읽으면 되나

2026-04-03 기준 최근 확인에서는
seed 보고서에 아래처럼 잡혔습니다.

- `rows_with_entry_wait_quality = 3`
- `valid_rows = 3`
- label 분포:
  - `better_entry_after_wait = 1`
  - `delayed_loss_after_wait = 1`
  - `neutral_wait = 1`

즉 WQ4는 지금
`보고서에서 끝나는 단계`가 아니라
`closed history와 experiment seed report까지 연결된 상태`로 보면 됩니다.

WQ5는 지금
`pilot baseline과의 auxiliary 연결까지는 끝난 상태`로 보면 됩니다.
다만 현재 실제 seed는 적어서
`wait_quality_task`는 아직 열리지 않은 상태입니다.

## 제일 짧은 운영 루틴

정말 바쁠 때는 이것만 기억하면 됩니다.

```powershell
python scripts/entry_wait_quality_replay_report.py
python scripts/backfill_entry_wait_quality_learning_seed.py
python scripts/teacher_pattern_experiment_seed_report.py
python scripts/teacher_pattern_pilot_baseline_report.py
```

그다음
- [entry_wait_quality_replay_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.md)
- seed report 터미널 출력
- pilot baseline 터미널 출력

이 세 개만 보면 됩니다.
