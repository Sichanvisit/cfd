# Teacher-Label Micro-Structure Top10 Step 1 OHLCV Helper 체크리스트

## 목표

이 문서는 `Step 1. 1분봉 집계 helper 추가` 구현 체크리스트다.

## Checklist

### A. helper 위치 확정

- [ ] owner를 [trading_application.py](/C:/Users/bhs33/Desktop/project/cfd/backend/app/trading_application.py) 로 고정했다
- [ ] helper 이름과 반환 shape를 정했다
- [ ] 기존 fetch 흐름과 충돌하지 않게 위치를 정했다

### B. 입력 범위 고정

- [ ] recent 1분봉 OHLCV lookback을 고정했다
- [ ] 기본 window `20`, 보조 window `50` 사용 여부를 고정했다
- [ ] session metadata 재사용 범위를 정했다
- [ ] gap anchor 후보를 정했다

### C. 1차 5개 계산

- [ ] `body_size_pct_20`
- [ ] `doji_ratio_20`
- [ ] `direction_run_stats`
- [ ] `range_compression_ratio_20`
- [ ] `volume_burst_decay_20`

위 5개가 helper에서 안정적으로 계산된다.

### D. 나머지 5개 shape/fallback 고정

- [ ] `upper_wick_ratio_20`
- [ ] `lower_wick_ratio_20`
- [ ] `swing_high_retest_count_20`
- [ ] `swing_low_retest_count_20`
- [ ] `gap_fill_progress`

위 5개는 key/fallback/anchor 처리 규칙이 고정된다.

### E. 상태 플래그

- [ ] `data_state`를 둔다
- [ ] `anchor_state`를 둔다
- [ ] insufficient bars 처리 규칙을 둔다
- [ ] gap anchor missing 처리 규칙을 둔다

### F. 테스트 준비

- [ ] 정상 20봉 이상 케이스
- [ ] bars 부족 케이스
- [ ] volume flat 케이스
- [ ] doji 비중 높은 케이스
- [ ] gap anchor 없는 케이스

## 완료 기준

- [ ] `micro_structure_v1` dict가 반환된다
- [ ] 런타임 전체를 깨지 않는 null-safe 규칙이 있다
- [ ] Step 2 state 편입에 바로 넘길 수 있다
