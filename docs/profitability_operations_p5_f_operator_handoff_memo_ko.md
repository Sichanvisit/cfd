# Profitability / Operations P5-F Operator Handoff Memo

작성일: 2026-03-30 (KST)

기준 산출물:
- [profitability_operations_p5_casebook_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.json)
- [profitability_operations_p5_casebook_latest.md](C:\Users\bhs33\Desktop\project\cfd\data\analysis\profitability_operations\profitability_operations_p5_casebook_latest.md)

## 1. 현재 casebook 요약

현재 P5 latest 기준 scene summary는 아래와 같다.

- `scene_row_count`: 75
- `worst_scene_count`: 15
- `strength_scene_count`: 3
- `tuning_candidate_count`: 10

즉 이제는 관측만 하는 단계가 아니라,
실제로 다음 review와 개선 입력으로 넘길 queue가 열린 상태다.

## 2. 지금 가장 먼저 볼 caution scene

1. `NAS100 / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
   - avg_pnl이 크게 음수고
   - high alert가 붙어 있으며
   - symbol delta도 최근 악화 쪽이다

2. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / LOW_LIQUIDITY`
   - fast adverse close가 같이 붙은 caution scene이다

3. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / UNKNOWN`
   - legacy blind 성격이 강하고 attribution 복원 우선순위가 높다

## 3. 지금 보존해야 할 strength scene

1. `XAUUSD / legacy_trade_without_setup_id::SELL::balanced / LOW_LIQUIDITY`
2. `XAUUSD / legacy_trade_without_setup_id::BUY::balanced / RANGE`
3. `BTCUSD / legacy_trade_without_setup_id::SELL::balanced / NORMAL`

즉 모든 scene이 다 나쁜 것이 아니라,
유지하거나 보호해야 할 strength scene도 분리해서 보기 시작한 상태다.

## 4. tuning candidate 해석

지금 top candidate type은 아래 둘이다.

- `legacy_bucket_identity_restore`
- `entry_exit_timing_review`

이 말은 현재 개선 본선이 아래라는 뜻이다.

1. legacy bucket을 explicit identity에 더 가깝게 복원하기
2. XAU 계열 fast adverse / cut pressure scene의 진입-청산 타이밍 재검토

## 5. 다음 단계 handoff

P5 이후 가장 자연스러운 다음 단계는 `P6 meta-cognition / health / drift / sizing`이다.

다만 지금 시점에서 P6로 올라가더라도,
P5 queue는 계속 살아 있는 운영 backlog로 유지하는 것이 맞다.
