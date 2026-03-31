# R4 Allowlist Expansion Candidate Memo

## 1. 목적

이 문서는 R4 운영 판단에서
`BTCUSD 다음에 어떤 심볼을 allowlist 확장 후보로 볼지`
를 현재 runtime / chart / rollout 근거로 좁히기 위한 memo이다.

이번 문서의 목표는 바로 allowlist를 바꾸는 것이 아니라,

- 현재 추천 action이 왜 아직 `stay_threshold_only`인지
- 그 상태에서도 `다음 후보 순서`를 어떻게 볼지
- `expand_allowlist`를 실제로 시도할 때 어떤 순서와 조건을 붙일지

를 고정하는 것이다.

## 2. 입력 근거

- preview audit latest: [semantic_preview_audit_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_preview_audit_latest.json)
- shadow compare healthy baseline: [semantic_shadow_compare_report_20260326_200401.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\semantic_v1\semantic_shadow_compare_report_20260326_200401.json)
- runtime status: [runtime_status.json](c:\Users\bhs33\Desktop\project\cfd\data\runtime_status.json)
- chart flow distribution latest: [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json)
- chart flow rollout latest: [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json)
- runtime reason casebook: [refinement_r4_runtime_reason_casebook_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_runtime_reason_casebook_ko.md)
- promotion action matrix: [refinement_r4_promotion_action_matrix_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_promotion_action_matrix_ko.md)
- rollback / kill switch contract: [refinement_r4_rollback_kill_switch_contract_ko.md](c:\Users\bhs33\Desktop\project\cfd\docs\refinement_r4_rollback_kill_switch_contract_ko.md)

## 3. 현재 운영 baseline

### semantic 운영 상태

- `promotion_gate.status = pass`
- `promotion_gate.warning_issues = []`
- `shadow_compare.status = healthy`
- runtime live mode는 여전히 `threshold_only`
- current allowlist는 `BTCUSD` 단일 심볼

즉 semantic preview / shadow는 건강하지만,
운영 단계는 아직 `bounded live 확장 직전`이 아니라
`threshold_only 관찰 + 확장 후보 정리` 단계로 보는 것이 맞다.

### chart rollout 상태

현재 [chart_flow_rollout_status_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_rollout_status_latest.json) 기준:

- `overall_status = hold`
- `recommended_action = hold`
- `Stage B = hold`
- `Stage E = hold`
- summary = `all tracked symbols are in extreme imbalance state`

즉 chart-side 기준으로도
`지금 바로 다심볼 운영 확장`을 밀어붙일 상황은 아니다.

## 4. 최근 runtime reason 요약

`semantic_rollout_state.recent` entry 기준 최근 surface는 다음과 같다.

### BTCUSD

- rows: `14`
- fallback reason: `baseline_no_action = 14`
- trace quality: `fallback_heavy = 14`
- baseline action: 전부 빈 값

해석:

- 이미 allowlist 안에 있으므로 `확장 후보`가 아니라 `현재 운영 기준 anchor`다.
- 지금 병목은 allowlist가 아니라 `baseline no action`이다.

### NAS100

- rows: `13`
- fallback reason: `symbol_not_in_allowlist = 13`
- trace quality: `fallback_heavy = 13`
- baseline action: 전부 빈 값

최신 signal 기준:

- `observe_side = BUY`
- `observe_reason = outer_band_reversal_support_required_observe`
- `blocked_by = outer_band_guard`
- `probe_scene_id = nas_clean_confirm_probe`
- `probe_candidate_active = true`
- `probe_plan_ready = false`
- `probe_plan_reason = probe_barrier_blocked`

해석:

- semantic 쪽은 들어갈 의지가 있지만
- 운영상 allowlist가 막고 있고
- chart 쪽은 `BUY probe / BUY wait`가 반복되지만 아직 barrier에 눌린다.

### XAUUSD

- rows: `13`
- fallback reason: `symbol_not_in_allowlist = 13`
- trace quality: `fallback_heavy = 13`
- baseline action: 전부 빈 값

최신 signal 기준:

- `observe_side = SELL`
- `observe_reason = upper_reject_probe_observe`
- `blocked_by = ""`
- `probe_scene_id = xau_upper_sell_probe`
- `probe_candidate_active = true`
- `probe_plan_ready = false`
- `probe_plan_reason = probe_against_default_side`

해석:

- XAU는 allowlist 때문에 막혀 있는 점은 NAS와 같지만
- 최신 runtime 방향은 `BUY`가 아니라 `SELL` 쪽이고
- probe plan도 `default side`와 어긋난 상태다.

즉 현재 시점은 `열면 바로 BUY로 이어질 것 같은 상태`라기보다
`방향 전환 / 충돌을 더 관찰해야 하는 상태`에 가깝다.

## 5. chart flow 근거

현재 [chart_flow_distribution_latest.json](c:\Users\bhs33\Desktop\project\cfd\data\analysis\chart_flow_distribution_latest.json) 기준 최근 16캔들 요약:

### BTCUSD

- `BUY_WAIT 2`
- `BUY_PROBE 3`
- `BUY_READY 1`
- `WAIT 10`
- blocked top:
  - `outer_band_guard 10`
  - `probe_promotion_gate 3`
  - `energy_soft_block 2`
- probe scene top:
  - `btc_lower_buy_conservative_probe 13`

### NAS100

- `BUY_WAIT 2`
- `BUY_PROBE 5`
- `WAIT 9`
- blocked top:
  - `outer_band_guard 9`
  - `probe_promotion_gate 5`
  - `energy_soft_block 2`
- probe scene top:
  - `nas_clean_confirm_probe 14`

### XAUUSD

- `BUY_WAIT 9`
- `BUY_READY 3`
- `WAIT 4`
- blocked top:
  - `outer_band_guard 12`
- probe scene top:
  - `xau_second_support_buy_probe 6`
  - `xau_upper_sell_probe 1`

해석:

- chart window만 보면 `XAUUSD`가 가장 directional buy 비중이 강하다.
- 그러나 runtime latest는 `upper sell probe`로 돌아서 있다.
- `NAS100`은 buy ready는 아직 없지만, runtime latest와 chart scene이 둘 다 `BUY clean confirm probe`로 비교적 일관된다.

## 6. 후보 우선순위

현재 기준 추천 순서는 아래와 같다.

### 1순위 후보: NAS100

이유:

- runtime latest가 `BUY` 방향이다.
- scene이 `nas_clean_confirm_probe`로 반복 surface 된다.
- allowlist blocker를 제외하면 semantic reason이 일관적이다.
- chart 쪽도 `BUY_PROBE 5`, `BUY_WAIT 2`로 같은 방향을 말하고 있다.
- 즉 `allowlist를 열었을 때 실제 관찰하고 싶은 상태`가 가장 명확하다.

주의:

- 여전히 `outer_band_guard`, `probe_promotion_gate`가 세다.
- 따라서 첫 확장은 `partial_live`가 아니라
  `threshold_only + allowlist expansion` 성격이어야 한다.

### 2순위 후보: XAUUSD

이유:

- chart window는 buy family가 가장 강하다.
- `BUY_WAIT 9`, `BUY_READY 3`로 directional presence 자체는 좋다.

보류 이유:

- latest runtime는 `SELL` 쪽이다.
- `xau_upper_sell_probe`와 `xau_second_support_buy_probe`가 함께 남아 있다.
- 즉 관측 윈도우 전체는 buy-heavy지만,
  현재 순간의 runtime decision은 방향 일관성이 떨어진다.

정리:

- XAU는 `좋아 보이는 후보`이긴 하지만
  `다음 즉시 확장 후보`라기보다 `한 윈도우 더 관찰 후 판단`이 맞다.

### 유지 대상: BTCUSD

- BTC는 현재 allowlist 안에 있는 기준 심볼이다.
- expansion candidate가 아니라
  `current threshold_only 운영 기준 anchor`로 본다.

## 7. 현재 추천 action

현재 추천 action은 여전히 `stay_threshold_only`이다.

이유:

- preview/shadow는 pass이지만
- chart rollout은 여전히 `overall hold`
- `Stage B`, `Stage E`도 hold
- allowlist 확장 후보는 보이지만
  아직 `즉시 확장`을 정당화할 만큼 chart/runtime 동시 안정화가 닫히지 않았다.

## 8. 다음 확장 조건

`expand_allowlist`를 실제로 시도한다면 다음 순서와 조건을 붙이는 것이 맞다.

### 순서

1. `NAS100`
2. `XAUUSD`

### NAS100 조건

- latest runtime가 최소 한 관찰 윈도우 동안 계속 `BUY` 방향 유지
- `nas_clean_confirm_probe` scene 유지
- `symbol_not_in_allowlist` 외의 unexpected fallback 증가 없음
- kill switch / rollback reason 없음

### XAUUSD 조건

- latest runtime가 `BUY / SELL` 사이에서 흔들리지 않을 것
- `xau_second_support_buy_probe` 또는 `xau_upper_sell_probe` 중 한 방향 우세가 더 분명해질 것
- `probe_against_default_side`가 반복 관측되지 않을 것

## 9. 결론

현재 R4 운영 판단은 이렇게 읽는 것이 가장 맞다.

- `semantic quality`: pass
- `runtime expansion readiness`: 아직 보수 유지
- `next allowlist candidate`: `NAS100`
- `observation-first candidate`: `XAUUSD`
- `current anchor`: `BTCUSD`

즉 지금은
`BTC 다음에 무엇을 열지 모르는 상태`는 아니고,
`바로 열지는 않되 NAS -> XAU 순으로 후보를 잠가둘 수 있는 상태`
라고 정리할 수 있다.
