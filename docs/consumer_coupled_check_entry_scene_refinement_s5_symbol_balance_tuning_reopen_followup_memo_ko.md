# Consumer-Coupled Check / Entry Scene Refinement
## S5 Reopen Follow-up Memo

### 배경

S6 acceptance에서 아래 판정이 나왔다.

- `S4 contract`: reopen 불필요
- `S5 symbol balance`: reopen 필요

핵심 이유는

- `BTCUSD`가 너무 눌려서 recent window에서 거의 안 보였고
- `NAS100`은 반대로 lower rebound probe가 너무 많이 보였기 때문이다.

이번 reopen은 이 두 symbol의 immediate imbalance를 다시 맞추는 데 목적이 있었다.

---

### 이번 reopen에서 반영한 것

#### 1. BTC lower rebound late reopen

대상:

- `symbol=BTCUSD`
- `observe_reason=lower_rebound_probe_observe`
- `blocked_by in {barrier_guard, forecast_guard}`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=btc_lower_buy_conservative_probe`

반영:

- late block가 붙더라도 `PROBE -> OBSERVE` downgrade
- cadence suppression은 `forecast_guard` 반복에만 유지
- `barrier_guard` family는 약한 visible observe를 다시 허용

의도:

- BTC가 아예 안 보이는 상태를 풀고
- weak lower observe는 다시 보이게 만든다

#### 2. NAS lower rebound late downgrade

대상:

- `symbol=NAS100`
- `observe_reason=lower_rebound_probe_observe`
- `blocked_by in {barrier_guard, forecast_guard, probe_promotion_gate}`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=nas_clean_confirm_probe`

반영:

- late block 시 `PROBE -> OBSERVE` downgrade
- 반복 lower probe는
  `nas_lower_probe_cadence_suppressed`
  로 숨김

의도:

- NAS의 과한 lower rebound probe visible을 줄인다

---

### 테스트

추가/강화:

- `tests/unit/test_consumer_check_state.py`
  - `test_build_consumer_check_state_downgrades_nas_lower_rebound_probe_to_observe_under_barrier_guard`
  - `test_resolve_effective_consumer_check_state_late_downgrades_btc_lower_probe_to_observe`
  - `test_resolve_effective_consumer_check_state_late_downgrades_nas_lower_probe_to_observe`
  - `test_resolve_effective_consumer_check_state_keeps_btc_lower_probe_visible_under_barrier_guard`
  - `test_resolve_effective_consumer_check_state_suppresses_repeated_nas_lower_probe_observe`

결과:

- `pytest tests/unit/test_consumer_check_state.py -q`
  - `16 passed`
- `pytest tests/unit/test_entry_service_guards.py tests/unit/test_chart_painter.py tests/unit/test_entry_try_open_entry_probe.py tests/unit/test_entry_try_open_entry_policy.py -q`
  - `153 passed`

---

### Runtime 결과

#### 1. immediate recent row

BTC recent:

- `lower_rebound_probe_observe + barrier_guard + probe_not_promoted`
- `consumer_check_stage=OBSERVE`
- `consumer_check_display_ready=True`
  가 다시 나타남

예:

- `2026-03-27T22:53:30`
- `2026-03-27T22:56:26`
- `2026-03-27T22:56:37`
- `2026-03-27T22:56:47`

해석:

- BTC는 다시 weak observe가 살아났다

NAS recent:

- 기존의
  `lower_rebound_probe_observe + barrier_guard + probe_not_promoted + PROBE + True`
가 immediate latest window에서는 사라졌고,
- `lower_rebound_confirm + barrier/forecast + observe_state_wait + PROBE + False`
쪽으로 이동했다

해석:

- NAS는 lower probe 과표시가 immediate window 기준으로 줄었다

#### 2. current 60-row snapshot

최근 60 rows 기준:

- `BTCUSD: display_true=4, display_false=56`
- `NAS100: display_true=5, display_false=55`
- `XAUUSD: display_true=46, display_false=14`

해석:

- BTC/NAS는 reopen 목적대로 거의 비슷한 density로 수렴했다
- 현재 visible pressure는 오히려 XAU가 더 크다

---

### 운영 상태

재시작 직후 `verify`는 bootstrap race로 실패했지만,
잠시 뒤 수동 확인 기준:

- `/health` OK
- `/trades/summary` OK

즉 이번 reopen은 runtime에 정상 반영된 것으로 본다.

---

### 현재 판단

이번 reopen으로:

- `BTC too hidden`
- `NAS too visible`

문제는 immediate / short rolling window에서 많이 완화됐다.

현재 다음 균형 문제는:

- `XAU family visibility`가 상대적으로 높다는 점이다

즉 이번 reopen은
`BTC/NAS 재균형`
에는 성공했고,
다음 acceptance나 tuning에서의 직접 대상은
`XAU side balance`
가 될 가능성이 높다.

---

### 다음 단계

가장 자연스러운 다음 선택지는 두 가지다.

1. `S6 acceptance`를 다시 짧게 재평가
2. `XAU visibility balance`를 다음 S5 follow-up으로 한 번 더 본다

현재로서는
`BTC/NAS reopen 목적은 달성`
으로 보는 것이 맞다.
