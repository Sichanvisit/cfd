# State25 Detail Micro Backfill 메모

## 이번 턴 요약
- future close에 `micro_*`가 안 실리던 직접 원인은 [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py) 에서 [trade_logger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/trading/trade_logger.py) `log_entry(...)`로 micro payload를 넘기지 않던 점이었다.
- 이 경로는 helper 기반으로 수정했고 테스트로 잠갔다.
- historical seed 보강용 richer detail backfill도 구현했다.

## 중요 발견
- current labeled seed `1767`행 중 `decision_row_key / trade_link_key`가 살아 있는 row는 극히 적다.
- recent `2K` dry-run 기준 strong-key target row는 `40`, 실제 match는 `0`
- 즉 지금 bottleneck은 code 부재가 아니라 historical source retention 부재다.

## 운영 의미
- immediate seed 강화는 제한적
- 하지만 지금부터 생성되는 fresh close는 runtime carry fix 덕분에 `micro_*`와 함께 닫힐 수 있다
- richer detail backfill은 앞으로 key retention이 살아 있는 bounded window에 대해서는 바로 재사용 가능하다

## 다음 액션
- runtime fresh labeled close가 실제로 쌓이는지 확인
- 그다음 [teacher_pattern_asset_calibration_report.py](/C:/Users/bhs33/Desktop/project/cfd/scripts/teacher_pattern_asset_calibration_report.py) 로 `micro_payload_zero` 경고가 줄기 시작하는지 본다
- 이후 Step 9 experiment tuning 계속 진행
## 2026-04-02 ATR proxy follow-up
- `entry_atr_ratio_flat` root cause was the runtime/default path leaving `entry_atr_ratio=1.0`.
- Runtime carry now falls back to `regime_volatility_ratio` only when the direct ATR ratio is still default-like.
- Detail micro backfill now applies the same ATR proxy fallback for recent closed rows when direct ATR payload is missing.
- After bounded `recent 100` apply, Step 9 asset calibration no longer reports `entry_atr_ratio_flat:*`.
