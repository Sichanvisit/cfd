# Profitability / Operations P7-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p7_counterfactual_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.json)
- [profitability_operations_p7_counterfactual_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p7_counterfactual_latest.md)

## 1. 현재 P7 한 줄 요약

현재 P7 latest는 `guarded apply 가능한 것은 size reduction`, `scene-level counterfactual은 대부분 review-only 또는 no-go`로 읽힌다.

즉 P7은 지금 단계에서 공격적 자동 적응이 아니라 `보수적 적용 후보 분리기`로 동작한다.

## 2. proposal 분포

- `guarded_apply_candidate`: 3
- `review_only`: 3
- `no_go`: 12

top proposal type은 `legacy_identity_restore_first`다.

즉 지금 worst scene의 다수는 아직 `counterfactual 실험`보다 `identity restore`가 먼저다.

## 3. 지금 바로 guarded apply 가능한 것

현재 guarded apply queue는 전부 `size_overlay_guarded_apply`다.

### XAUUSD

- action: `hard_reduce`
- size target: `0.25`
- rationale: `health_score=0.0`, `fast_adverse_close_alert` pressure, worst scene 다수

### NAS100

- action: `hard_reduce`
- size target: `0.43`
- rationale: `zero_pnl_information_gap_alert` + legacy pressure, stressed 상태

### BTCUSD

- action: `reduce`
- size target: `0.57`
- rationale: `blocked_pressure_alert` 중심의 watch 상태

즉 현재 P7에서 바로 guarded apply로 읽을 수 있는 것은 `size reduction overlay`뿐이다.

## 4. review-only로 남겨야 하는 것

현재 review-only는 주로 XAU의 `entry_delay_review`다.

대표 scene:

- `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
- `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / NORMAL`
- `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / RANGE`

이 scene들은 `entry timing을 늦추는 가설`은 성립하지만, 현재 symbol health가 `stressed`라서 바로 적용 후보로 올리기보다 review-only가 맞다.

## 5. no-go로 묶인 것

현재 no-go는 대부분 `identity_first_gate`다.

대표 scene:

- `NAS100 / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
- `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / UNKNOWN`
- `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / NORMAL`
- `BTCUSD / legacy_trade_without_setup_id::BUY::balanced / NORMAL`

즉 이 queue는 `무엇을 바꾸기 전에 먼저 legacy identity 공백을 줄여야 한다`는 뜻이다.

## 6. 운영상 결론

지금 시점에서 가장 맞는 운영 해석은 아래다.

1. `size overlay guarded apply`는 후보로 유지
2. XAU timing review는 실험 후보로 적어두되 live 적용은 보류
3. legacy balanced family는 counterfactual보다 identity restore를 먼저 진행

## 7. 다음 rerun에서 볼 것

아래 변화가 보이면 P7 proposal을 한 단계 더 올릴 수 있다.

- `legacy_identity_restore_first` 비중 감소
- XAU timing review scene가 stressed에서 watch로 완화
- guarded apply queue에 size 외 entry/exit proposal이 추가

반대로 아래가 보이면 더 보수적으로 읽어야 한다.

- stressed symbol 유지 또는 증가
- no-go queue 확대
- identity-first scene가 더 늘어남
