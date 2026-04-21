# Wait Quality Replay Quickstart

## 언제 쓰나

이 문서는 `좋은 기다림 / 나쁜 기다림`을 실제 최근 `entry_decisions.csv` 기준으로 다시 보고 싶을 때 봅니다.

쉽게 말하면 아래 2가지를 확인하는 용도입니다.

- 기다렸더니 더 좋은 자리에서 들어갔는지
- 기다렸다가 기회를 놓쳤는지

## 실행 순서

1. 먼저 future bars를 새로 받습니다.

```powershell
python scripts/fetch_mt5_future_bars.py
```

2. 그다음 replay 보고서를 만듭니다.

```powershell
python scripts/entry_wait_quality_replay_report.py
```

3. 사람이 읽기 쉬운 요약은 이 파일을 봅니다.

- [entry_wait_quality_replay_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.md)

4. 원본 JSON이 필요하면 이 파일을 봅니다.

- [entry_wait_quality_replay_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.json)

## 터미널에서 뭘 보면 되나

`python scripts/entry_wait_quality_replay_report.py`를 실행하면 긴 원본 JSON 대신 핵심만 짧게 나옵니다.

주로 볼 항목은 이것뿐입니다.

- `status`
  - `covered`: 거의 다 붙음
  - `partial_overlap`: 대부분 붙었지만 tail 몇 개는 future bars가 부족함
  - `stale_before_waits`: future bars가 너무 오래돼서 지금 wait rows보다 뒤처짐

- `rows_valid`
  - 실제로 판정 가능한 wait row 수

- `better_entry_after_wait`
  - 기다린 게 도움이 된 케이스

- `missed_move_by_wait`
  - 기다리다 놓친 케이스

- `delayed_loss_after_wait`
  - 기다렸다가 더 나쁜 가격/더 늦은 손실로 간 케이스

- `insufficient_evidence`
  - 아직 판단 재료가 부족한 케이스

## 지금 기준 해석 예시

2026-04-03 기준 최근 시현에서는 아래처럼 나왔습니다.

- `bridged_row_count = 100`
- `rows_valid = 92`
- `better_entry_after_wait = 18`
- `missed_move_by_wait = 5`
- `delayed_loss_after_wait = 4`
- `neutral_wait = 65`
- `insufficient_evidence = 8`
- `status = partial_overlap`

즉 지금은 `WQ2 replay bridge`가 실제 최근 데이터에 붙었고,
아주 최신 tail 몇 개만 future bars가 부족한 상태로 보면 됩니다.

## 제일 짧은 운영 루틴

평소에는 이것만 기억하면 됩니다.

```powershell
python scripts/fetch_mt5_future_bars.py
python scripts/entry_wait_quality_replay_report.py
```

그다음 [entry_wait_quality_replay_latest.md](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/wait_quality/entry_wait_quality_replay_latest.md)만 읽으면 됩니다.

## 여기서 한 단계 더 가고 싶을 때

replay 보고서에서 끝내지 않고
이 결과를 실제 학습용 `trade_closed_history.csv`에도 붙이고 싶으면
[wait_quality_learning_seed_quickstart_ko.md](/C:/Users/bhs33/Desktop/project/cfd/wait_quality_learning_seed_quickstart_ko.md)를 보면 됩니다.
