# R4 NAS Post-Expansion / XAU Candidate Follow-up Memo

## 1. 목적

이 문서는

- `NAS100 allowlist expansion` 이후 실제 관찰 결과
- `XAUUSD`를 다음 확장 후보로 볼 수 있는지에 대한 재판단

을 한 장으로 묶는 follow-up memo다.

## 2. 기준 입력

- [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- [entry_decisions.csv](c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv)
- [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)
- [refinement_r4_allowlist_expansion_reconfirm_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_reconfirm_memo_ko.md)
- [refinement_r4_allowlist_expansion_candidate_memo_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_allowlist_expansion_candidate_memo_ko.md)

## 3. NAS100 post-expansion 관찰

### 운영 설정 상태

현재 allowlist는:

- `BTCUSD`
- `NAS100`

이다.

### runtime recent 변화

최근 runtime recent entry 기준 NAS100은:

- 이전: `symbol_not_in_allowlist`
- 현재: `baseline_no_action`

으로 바뀌었다.

즉 NAS100은 실제로 allowlist gate를 통과했고,
현재 병목은 allowlist가 아니라 baseline / probe promotion 쪽이다.

### latest signal 해석

현재 latest signal 기준 NAS100은:

- `observe_side = BUY`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `probe_scene_id = nas_clean_confirm_probe`
- `probe_plan_ready = false`
- `probe_plan_reason = probe_forecast_not_ready`

이다.

해석:

- 방향은 여전히 `BUY`
- scene도 `nas_clean_confirm_probe`로 일관적
- 하지만 `outer_band_guard`와 `forecast / promotion readiness`가 아직 진입 전 승격을 막고 있다

### chart flow 근거

현재 chart distribution 기준 NAS100은:

- `BUY_WAIT 2`
- `BUY_PROBE 5`
- `WAIT 9`
- blocked top:
  - `outer_band_guard 9`
  - `probe_promotion_gate 5`
  - `energy_soft_block 2`

정리:

- NAS100 확장은 잘 적용됐다
- 하지만 아직 `observe -> probe -> ready`가 충분히 풀린 상태는 아니다
- 따라서 현재 NAS100은 `확장 성공, 추가 관찰 필요` 상태다

## 4. XAUUSD 후보 재판단

### runtime recent 상태

최근 runtime recent entry 기준 XAUUSD는 여전히:

- `symbol_not_in_allowlist`

이다.

즉 운영상 gate는 아직 allowlist다.

### latest signal 해석

현재 latest signal 기준 XAUUSD는:

- `observe_side = SELL`
- `observe_reason = upper_reject_probe_observe`
- `probe_scene_id = xau_upper_sell_probe`
- `probe_plan_ready = false`
- `probe_plan_reason = probe_against_default_side`
- `bb_state = UPPER_EDGE`
- `probe_candidate_support = 0.138...`

이다.

해석:

- 지금 현재 순간의 runtime 방향은 `BUY`가 아니라 `SELL`
- `probe_against_default_side`가 여전히 surface 된다
- support도 낮아, 다음 확장 후보로 바로 올리기엔 방향 일관성이 약하다

### chart flow 근거

현재 chart distribution 기준 XAUUSD는:

- `BUY_WAIT 8`
- `BUY_READY 3`
- `SELL_PROBE 2`
- `WAIT 3`
- blocked top:
  - `outer_band_guard 9`
- probe scene:
  - `xau_second_support_buy_probe 4`
  - `xau_upper_sell_probe 3`

정리:

- chart window만 보면 여전히 buy family presence가 강하다
- 하지만 runtime latest는 sell probe 쪽으로 기울어 있다
- 즉 `관측 윈도우 전체`와 `현재 순간 runtime`이 아직 완전히 한 방향으로 수렴하지 않았다

## 5. 현재 판단

### NAS100

- 상태: `확장 적용 완료`
- 해석: `allowlist blocker 해소`
- 다음: `추가 관찰`

### XAUUSD

- 상태: `후보 유지`
- 해석: `즉시 확장 보류`
- 다음: `방향 일관성 재확인`

## 6. 운영 결론

현재 R4 follow-up 결론은 아래가 맞다.

- current allowlist:
  - `BTCUSD`
  - `NAS100`
- NAS100:
  - 확장은 정상 반영
  - 지금은 allowlist가 아니라 `outer_band_guard / probe_not_promoted`가 병목
- XAUUSD:
  - 아직 다음 확장 후보로 남아 있지만
  - `지금 바로` 열기보다는 한 윈도우 더 관찰하는 쪽이 맞다

즉 다음 실제 후보 순서는 여전히:

1. `NAS100 관찰 지속`
2. `XAUUSD 재판단`

이다.
