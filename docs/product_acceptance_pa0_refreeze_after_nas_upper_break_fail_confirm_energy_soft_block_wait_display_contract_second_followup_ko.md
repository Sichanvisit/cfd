# Product Acceptance PA0 Refreeze After NAS Upper-Break-Fail Confirm Energy Soft-Block Wait Display Contract Second Follow-Up

작성일: 2026-04-01 (KST)

## 1. 목적

이 문서는
`NAS100 + upper_break_fail_confirm + energy_soft_block + execution_soft_blocked +`
family에 대해 user가 요청한 `live exact row 한 번 더 확인` 시도와,
그 이후 PA0 latest에서 `must_block 12 -> 0`이 실제로 닫혔는지를 기록한다.

## 2. live 재확인 결과

재시작 로그:

- [cfd_main_restart_20260401_125318.out.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_125318.out.log)
- [cfd_main_restart_20260401_125318.err.log](C:\Users\bhs33\Desktop\project\cfd\logs\cfd_main_restart_20260401_125318.err.log)

watch cutoff:

- `2026-04-01T12:54:13`

결과:

- fresh exact NAS energy row: `0`
- fresh wait-contract NAS energy row: `0`
- latest persisted row time: `2026-04-01T01:49:24`

원인 로그:

- `MT5 connection unavailable` 반복 재시도

즉 이번 재확인에서는 live fresh exact row 자체는 다시 못 잡았다.

## 3. PA0 refreeze 결과

before snapshot:

- [product_acceptance_pa0_baseline_snapshot_20260401_014137.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_snapshot_20260401_014137.json)

after latest:

- [product_acceptance_pa0_baseline_latest.json](C:\Users\bhs33\Desktop\project\cfd\data\analysis\product_acceptance\product_acceptance_pa0_baseline_latest.json)

delta:

- `must_show 0 -> 0`
- `must_hide 0 -> 0`
- `must_block 12 -> 0`

## 4. 해석

1. fresh exact row 재발은 이번에도 없었다.
2. 하지만 persisted recent window turnover가 진행되면서 NAS energy backlog는 PA0 must-block queue에서 완전히 빠졌다.
3. 따라서 이 축은 이제 `live exact 재발 pending`이 아니라, `PA0 queue 기준으로는 닫힘 확인` 상태로 보아도 된다.
