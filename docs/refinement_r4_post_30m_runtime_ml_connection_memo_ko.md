# R4 Post-30m Runtime / ML Connection Memo

## 1. 목적

이 문서는 NAS100 allowlist 확장 후 약 30분 관찰 기준으로

- 현재 runtime 운영 상태
- NAS100 관찰 결과
- XAUUSD 후보 상태
- semantic ML runtime 연결 상태

를 한 번 더 확인한 메모다.

## 2. 기준 입력

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)
- [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- [semantic_canary_rollout_BTCUSD_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_canary\semantic_canary_rollout_BTCUSD_latest.json)

## 3. 현재 runtime 상태

현재 [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json) 기준:

- `updated_at = 2026-03-26T22:49:42+09:00`
- mode = `threshold_only`
- allowlist = `BTCUSD,NAS100`
- kill_switch = `false`

recent runtime recent entry 기준:

- `BTCUSD`: `baseline_no_action`
- `NAS100`: `baseline_no_action`
- `XAUUSD`: `symbol_not_in_allowlist`

즉 NAS100 allowlist 확장은 실제로 유지되고 있고,
XAUUSD만 아직 allowlist 밖이다.

## 4. NAS100 관찰 결과

### runtime

- latest runtime side: `BUY`
- recent fallback: 전부 `baseline_no_action`
- latest semantic reason:
  - `mode=threshold_only, trace=fallback_heavy, timing≈0.981, entry_quality≈0.940, fallback=baseline_no_action`

### signal / probe

- latest signal은 `conflict_box_lower_bb20_upper_upper_dominant_observe`
- `probe_candidate_inactive`
- `probe_plan_ready = false`

### chart distribution

- `BUY_WAIT 3`
- `BUY_PROBE 5`
- `WAIT 8`
- blocked top:
  - `outer_band_guard 7`
  - `probe_promotion_gate 5`
  - `energy_soft_block 3`

해석:

- NAS100은 allowlist gate는 풀렸다
- 하지만 지금은 `baseline_no_action`과 `conflict observe`가 병목이다
- 즉 다음 조정 owner는 allowlist가 아니라 baseline / chart-side flow 쪽이다

## 5. XAUUSD 후보 재확인

### runtime

- latest runtime side: `SELL`
- latest observe reason: `upper_reject_probe_observe`
- recent fallback: 전부 `symbol_not_in_allowlist`

### signal / probe

- `probe_scene_id = xau_upper_sell_probe`
- `probe_plan_ready = false`
- `probe_plan_reason = probe_forecast_not_ready`
- `bb_state = UPPER_EDGE`

### chart distribution

- `BUY_WAIT 3`
- `SELL_PROBE 8`
- `WAIT 5`
- probe scene top:
  - `xau_upper_sell_probe 9`
  - `xau_second_support_buy_probe 3`

해석:

- 30분 뒤 기준으로 XAU는 buy-heavy 관찰보다 sell probe 쪽이 더 분명해졌다
- 즉 지금은 `확장 후보 유지`보다 `확장 보류` 쪽으로 더 기울어 있다

## 6. ML 연결 확인

현재 ML / semantic runtime 연결은 살아 있다.

근거:

- preview audit:
  - [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
  - `promotion_gate.status = pass`
  - `shadow_compare.status = healthy`
- runtime rows:
  - `semantic_shadow_available = 1`
  - `semantic_live_rollout_mode = threshold_only`
  - `semantic_live_reason` populated
  - `semantic_shadow_trace_quality = fallback_heavy`

즉 지금 문제는 `ML이 안 붙었다`가 아니라
`ML은 붙어 있는데 운영 모드가 threshold_only이고 fallback-heavy 조건에서 보수적으로 동작한다`
로 보는 것이 맞다.

## 7. chart rollout 상태

[chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json) 기준:

- `overall_status = hold`
- `Stage A = advance`
- `Stage B = advance`
- `Stage C = advance`
- `Stage D = advance`
- `Stage E = hold`

summary:

- `micro calibration targets identified: BTCUSD, NAS100, XAUUSD`

해석:

- chart flow 기준으로도 아직 전체 운영 확장을 밀어붙일 시점은 아니다

## 8. 결론

30분 관찰 후 현재 상태는 아래처럼 읽는 것이 맞다.

- `NAS100`
  - allowlist 확장은 정상 유지
  - 하지만 현재 병목은 allowlist가 아니라 `baseline_no_action / conflict observe`
- `XAUUSD`
  - 다음 확장 후보로 밀기보다 당분간 보류가 맞음
  - 현재는 `SELL probe` 쪽이 더 분명함
- `ML 연결`
  - 정상 연결됨
  - 다만 운영 모드는 여전히 `threshold_only`
- `현재 운영 action`
  - `threshold_only 유지`
  - `BTCUSD/NAS100 allowlist 유지`
  - `XAUUSD 확장 보류`
  - `partial_live 보류`
