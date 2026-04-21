# Product Acceptance Learning-Ready Trade Outcome Scoring Implementation Memo

## owner

- [trade_csv_schema.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/trade_csv_schema.py)

## implementation

- added columns:
  - `learning_entry_score`
  - `learning_wait_score`
  - `learning_exit_score`
  - `learning_total_score`
  - `learning_total_label`
- formula:
  - entry edge from `entry_score - contra_score_at_entry`
  - wait quality from `wait_quality_score`
  - exit quality from `loss_quality_score + pnl + signed_exit_score`
  - total reward from weighted entry/wait/exit blend

## verification

- [test_loss_quality_wait_behavior.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_loss_quality_wait_behavior.py) -> `5 passed`
- [test_trade_logger_open_snapshots.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_trade_logger_open_snapshots.py) -> `3 passed`

## runtime evidence

- normalized runtime closed-history rows already expose:
  - `learning_entry_score`
  - `learning_wait_score`
  - `learning_exit_score`
  - `learning_total_score`
  - `learning_total_label`

## next

- trainer/ML은 이제 `trade_closed_history.csv`만 읽어도 supervised/reward seed를 바로 만들 수 있음
