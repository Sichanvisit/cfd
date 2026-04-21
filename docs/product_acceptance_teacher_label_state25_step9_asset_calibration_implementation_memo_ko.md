# Teacher-Label State25 Step E1 메모

## 메모

- Step 9 seed report 다음 첫 하위축은 자산별 캘리브레이션이 맞다.
- 현재 compact dataset에는 raw ATRP_20/10 전체 시계열은 없지만, `entry_atr_ratio`, `regime_volatility_ratio`, `micro_*` proxy는 이미 있다.
- 따라서 이번 E1은 `current compact seed 기준의 실용 캘리브레이션`으로 본다.

## 왜 이 구현이 필요한가

- 현재 labeled seed는 `1`, `14`, `9` 패턴에 치우쳐 있다.
- 전체 분포만 보면 자산별 왜곡이 잘 안 보인다.
- Step E2 / E3 전에 자산별 skew와 watchlist pair 빈도를 먼저 봐야 한다.

## 다음 자연스러운 순서

1. asset calibration report 실행
2. 자산별 skew / insufficient row 확인
3. Step E2 10K full labeling QA
4. baseline model

즉 Step 9는 `seed report -> asset calibration -> 10K QA -> baseline` 순서로 가는 것이 맞다.

## 이번 실행에서 확인된 핵심

- `labeled_rows = 1767` 기준으로 E1 report는 정상 동작한다.
- 세 자산 모두 `min_rows_per_symbol = 200`는 넘겼다.
- 그러나 현재 backfill seed는 세 자산 모두 `group_skew:A` 경고가 뜬다.
- `entry_atr_ratio`는 세 자산 모두 flat 1.0으로 관측되어 현재 seed에서는 ATR proxy 분별력이 낮다.
- `micro_*` 주요 값(`body/doji/compression/volume`)은 세 자산 모두 0으로 관측되어 현재 backfill seed에서는 micro payload가 비어 있다.

즉 E1의 결론은 `자산별 표본 수는 충분하지만, 현재 seed는 A그룹 편향 + flat ATR proxy + zero micro payload 상태라 바로 threshold tuning으로 가기보다 labeled seed 품질 보강이 먼저`라는 것이다.
## 2026-04-02 seed normalization update
- Recent bounded ATR proxy backfill was applied after the richer detail micro backfill.
- `entry_atr_ratio_flat:BTCUSD`, `entry_atr_ratio_flat:XAUUSD`, and `entry_atr_ratio_flat:NAS100` warnings are now cleared in the current Step 9 report.
- Remaining Step 9 warnings are now distribution skew focused (`group_skew:*`) rather than payload-flatness focused.
