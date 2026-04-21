# BTC Upper Sell Fresh Runtime Check After MT5 Recovery

## 목적
- `BTC upper sell` 계열 wait-display contract가 live fresh row 기준으로 실제 queue cleanup까지 이어지는지 다시 확인한다.
- user가 MT5 재연결을 수행한 뒤 `PA0 actual cleanup`이 가능한 상태로 넘어갔는지 확인한다.

## 확인 시각
- 확인 기준 시각: `2026-04-01T13:42:56`
- 작업 위치: `C:\Users\bhs33\Desktop\project\cfd`

## 런타임 확인 결과
- [cfd_main_restart_20260401_132056.err.log](/C:/Users/bhs33/Desktop/project/cfd/logs/cfd_main_restart_20260401_132056.err.log) 기준 `2026-04-01 13:39:38`에 `MT5 connection recovered after 72 attempts`가 기록됐다.
- [runtime_status.json](/C:/Users/bhs33/Desktop/project/cfd/data/runtime_status.json) `LastWriteTime`은 `2026-04-01 13:39:28`로 갱신됐다.
- 즉 runtime loop 자체는 다시 돌기 시작한 것으로 본다.

## fresh row 확인 결과
- [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv) row count는 `2225`로 그대로였다.
- 마지막 row `time`도 여전히 `2026-04-01T01:49:24`였다.
- recent 360-row 기준 `chart_event_kind_hint / chart_display_mode / chart_display_reason`는 모두 빈 값이었다.
- 따라서 `BTC upper sell` 계열의 새 wait-contract row는 아직 CSV에 기록되지 않았다.

## PA0 refreeze 결과
- [product_acceptance_pa0_baseline_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/product_acceptance/product_acceptance_pa0_baseline_latest.json) `generated_at`은 `2026-04-01T13:42:56`으로 갱신됐다.
- baseline summary는 그대로였다.
  - `must_show_missing_count = 15`
  - `must_hide_leakage_count = 15`
  - `must_block_candidate_count = 12`

## BTC upper sell target residue
- `must_hide`
  - `BTCUSD + upper_reject_confirm + forecast_guard + observe_state_wait` = `9`
  - `BTCUSD + upper_break_fail_confirm + forecast_guard + observe_state_wait` = `4`
  - `BTCUSD + upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe` = `2`
- `must_block`
  - `BTCUSD + upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe` = `10`
  - `BTCUSD + upper_reject_confirm + preflight_action_blocked + preflight_blocked` = `2`

## 해석
- MT5 recovery 로그는 확인됐지만, `entry_decisions.csv`에는 아직 fresh runtime row가 들어오지 않았다.
- 그래서 이번 refreeze는 `9/4/2/10/2 -> 0` 확인이 아니라, `recovery 이후에도 target residue가 그대로 남아 있음`을 재확인한 단계다.
- 현 시점 결론은 `PA0 actual cleanup pending` 유지다.

## 다음 체크포인트
- [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv) 마지막 `time`이 `2026-04-01T01:49:24`를 넘기기 시작하는지 먼저 본다.
- fresh BTC row가 실제로 들어온 뒤, 같은 묶음에 대해 PA0 refreeze를 다시 실행해 `9/4/2/10/2 -> 0`을 확인한다.
