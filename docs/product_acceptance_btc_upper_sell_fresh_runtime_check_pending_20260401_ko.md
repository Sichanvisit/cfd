# Product Acceptance BTC Upper-Sell Fresh Runtime Check Pending 2026-04-01

작성일: 2026-04-01 (KST)

## 1. 확인 목적

다음 BTC upper-sell residue가 fresh runtime row로 실제 기록됐는지 확인한다.

- `upper_reject_confirm + forecast_guard + observe_state_wait`
- `upper_break_fail_confirm + forecast_guard + observe_state_wait`
- `upper_reject_probe_observe + forecast_guard + probe_not_promoted + btc_upper_sell_probe`
- `upper_reject_probe_observe + preflight_action_blocked + preflight_blocked + btc_upper_sell_probe`
- `upper_reject_confirm + preflight_action_blocked + preflight_blocked`

## 2. 확인 결과

- `entry_decisions.csv` latest row time: `2026-04-01T01:49:24`
- 현재 row count: `2225`
- fresh row 증가: `없음`
- current `main.py` pid: `13908`

## 3. live 상태

runtime log:

- [cfd_main_restart_20260401_132056.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_132056.err.log)

지속 상태:

- `MT5 connection unavailable`
- retry attempt가 계속 증가 중

즉 현재는 코드 문제가 아니라 live source 연결 문제로 fresh runtime 확인이 막혀 있다.

## 4. 결론

이번 체크 시점에서는 BTC upper-sell 계열의 PA0 actual cleanup을 새 row 기준으로 검증할 수 없다.

다음 확인 조건은 단순하다.

1. `entry_decisions.csv` 마지막 시간이 다시 증가할 것
2. 그 뒤 PA0 refreeze를 다시 돌릴 것
3. BTC upper-sell residue `9 / 4 / 2 / 10 / 2`가 실제로 줄어드는지 확인할 것
