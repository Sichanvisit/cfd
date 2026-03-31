# Profitability / Operations P6-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p6_health_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.json)
- [profitability_operations_p6_health_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p6_health_latest.md)

## 1. 현재 health 요약

현재 P6 latest 기준으로 system은 `overall_drift_state = worsening`이고, `global_size_multiplier = 0.417`이다.

symbol health 분포는 아래와 같다.

- `healthy`: 0
- `watch`: 1
- `stressed`: 2

즉 지금은 공격적 확대보다 `방어적 운영 + 원인 정리 우선`이 맞는 국면으로 읽힌다.

## 2. 심볼별 운영 액션

### XAUUSD

- 현재 상태: `stressed`
- advisory size: `0.25`
- action: `hard_reduce`
- top alert: `fast_adverse_close_alert`
- top candidate: `legacy_bucket_identity_restore`

운영 해석:
- XAU는 현재 가장 먼저 줄여야 하는 심볼이다.
- 단순 정보 공백보다 `실제 fast adverse close pressure`가 더 강하게 보인다.

즉시 우선 작업:
- `entry_exit_timing_review`
- `legacy_bucket_identity_restore`

완화 조건:
- 다음 P4/P5/P6 rerun에서 `fast_adverse_close_alert` 계열 pressure가 완화될 것
- `worst_scene_count`가 줄어들 것
- `size_action`이 `hard_reduce -> reduce` 이상으로 완화될 것

### NAS100

- 현재 상태: `stressed`
- advisory size: `0.43`
- action: `hard_reduce`
- top alert: `zero_pnl_information_gap_alert`
- top candidate: `legacy_bucket_identity_restore`

운영 해석:
- NAS도 강한 축소가 맞다.
- 다만 성격은 XAU와 다르게 `정보 공백 + legacy pressure` 쪽이 더 크다.

즉시 우선 작업:
- `legacy_bucket_identity_restore`
- `pnl_lineage / attribution 보강 확인`

완화 조건:
- `zero_pnl_information_gap_alert`가 상단 queue에서 내려갈 것
- legacy bucket의 identity 회복이 진행될 것
- 다음 rerun에서 `health_score`가 watch 구간으로 회복될 것

### BTCUSD

- 현재 상태: `watch`
- advisory size: `0.57`
- action: `reduce`
- top alert: `blocked_pressure_alert`
- top candidate: `legacy_bucket_identity_restore`

운영 해석:
- BTC는 완전 정지보다 `보수적 reduce` 정도가 맞다.
- 현재 위험은 즉시 붕괴보다는 `blocked pressure / 운영 마찰` 쪽에 더 가깝다.

즉시 우선 작업:
- blocked / skip pressure 패턴 관찰
- `legacy_bucket_identity_restore`의 BTC 기여도 재확인

완화 조건:
- `blocked_pressure_alert` delta가 줄어들 것
- `active_alert_delta`가 완화될 것
- `size_action`이 `reduce -> hold_small` 이상으로 회복될 것

## 3. setup proxy 해석

setup_key proxy 기준으로는 아래가 가장 약하다.

- `legacy_trade_without_setup_id::BUY::balanced`
- `legacy_trade_without_setup_id::SELL::balanced`

즉 현재 weakest archetype proxy는 `legacy balanced family`다.

이건 단순히 특정 진입 규칙이 나쁘다는 뜻보다, 현재 profitability / attribution surface가 여전히 `legacy identity 공백`의 영향을 크게 받고 있다는 뜻으로 읽는 것이 맞다.

## 4. 즉시 우선 작업 큐

현재 P6 기준 immediate priority는 아래 순서로 잡는 것이 맞다.

1. `legacy_bucket_identity_restore`
2. `XAU entry_exit_timing_review`
3. `NAS zero-pnl / attribution pressure 완화`
4. `BTC blocked pressure 추세 관찰`

즉 P6는 단순 size 축소 지시가 아니라, `무엇을 먼저 고쳐야 advisory가 완화될지`까지 보여주는 operator queue로 써야 한다.

## 5. 재평가 트리거

다음 P4/P5/P6 rerun에서 아래 변화가 보이면 advisory 완화를 검토할 수 있다.

- `active_alert_delta` 감소
- `worst_scene_count` 감소
- `legacy_bucket_identity_restore`가 top candidate 자리에서 내려옴
- `zero_pnl_information_gap_alert` 상단 집중 완화
- XAU의 `fast_adverse_close_alert` 완화
- BTC의 `blocked_pressure_alert` delta 완화

반대로 아래가 보이면 P6 advisory를 더 보수적으로 읽어야 한다.

- stressed symbol 수 유지 또는 증가
- `global_size_multiplier` 추가 하락
- `critical` 계열 alert 재출현

## 6. 다음 단계 handoff

P6 이후 가장 자연스러운 다음 단계는 `P7 controlled counterfactual / selective adaptation`이다.

다만 P7에 들어가더라도 이번 P6 advisory는 바로 live auto-change가 아니라 `review and guarded application` 전제로 다루는 것이 맞다.

즉 현재 단계의 올바른 해석은 아래다.

- P6는 `자동 적응 엔진`이 아니다.
- P6는 `지금 어디를 줄이고, 왜 줄이며, 무엇이 풀리면 완화할지`를 말해주는 운영 해석 계층이다.
