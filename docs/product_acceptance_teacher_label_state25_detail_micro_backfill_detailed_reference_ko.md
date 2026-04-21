# State25 Detail Micro Backfill 상세 기준

## 목적
- `teacher_pattern_*`가 이미 붙은 closed-history seed에 `micro_*` source/semantic payload를 가능한 범위에서 실제 detail JSONL로 보강한다.
- future runtime close는 `entry_try_open_entry -> trade_logger.log_entry` 경로에서 micro payload를 그대로 carry 하도록 맞춘다.

## 구현 범위
- runtime carry fix:
  - [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
  - `entered_row`의 `micro_*`를 [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py) `log_entry(...)` 인자로 전달
- richer detail backfill:
  - [teacher_pattern_detail_micro_backfill.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/teacher_pattern_detail_micro_backfill.py)
  - [backfill_teacher_pattern_detail_micro.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/backfill_teacher_pattern_detail_micro.py)

## 데이터 원천
- closed compact:
  - [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
- detail JSONL:
  - [entry_decisions.detail.jsonl](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.detail.jsonl)
  - `entry_decisions.detail.rotate_*.jsonl`

## 보강 규칙
- strong key만 사용:
  - `decision_row_key`
  - `trade_link_key`
- `runtime_snapshot_key`, top-level `row_key`는 현재 dataset에서 충돌/과매칭 위험이 커서 rich apply 키로 쓰지 않는다.
- numeric micro source:
  - `micro_body_size_pct_20`
  - `micro_doji_ratio_20`
  - `micro_same_color_run_current`
  - `micro_same_color_run_max_20`
  - `micro_range_compression_ratio_20`
  - `micro_volume_burst_ratio_20`
  - `micro_volume_burst_decay_20`
  - `micro_gap_fill_progress`
- semantic micro state:
  - `micro_breakout_readiness_state`
  - `micro_reversal_risk_state`
  - `micro_participation_state`
  - `micro_gap_context_state`

## 단위 보정
- `s_body_size_pct_20`가 raw point처럼 큰 값일 수 있어서, `entry_request_price / entry_fill_price / s_current_price` 기준으로 `%` 정규화를 시도한다.

## provenance 규칙
- row가 이미 `teacher_pattern_*`를 갖고 있으면 teacher provenance는 유지
- row가 unlabeled이고 detail 기반 merged candidate로 라벨이 가능하면:
  - `teacher_label_source = rule_v2_detail_backfill`
  - `teacher_label_review_status = backfilled_unreviewed`

## 실데이터 점검 결과
- recent `2K` dry-run 결과:
  - `target_rows = 40`
  - `matched_rows = 0`
  - `micro_enriched_rows = 0`
- 해석:
  - 현재 labeled seed `1767` 중 대부분은 strong key 자체가 없음
  - key가 있는 recent row도 retained detail JSONL strong key와 직접 일치하지 않음
  - 따라서 richer backfill 구현은 완료됐지만, 현재 데이터 보존 상태에서는 immediate apply 효과가 `0`

## 결론
- 지금 실제 보강축은 two-track 이다.
  - `runtime carry fix`로 future close부터 micro payload 확보
  - `detail richer backfill`은 strong-key retained 구간이 생길 때 bounded apply
