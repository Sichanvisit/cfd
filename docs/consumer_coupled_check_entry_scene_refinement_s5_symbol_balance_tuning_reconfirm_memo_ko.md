# Consumer-Coupled Check / Entry Scene Refinement
## S5. Symbol Balance Tuning Reconfirm Memo

### 목적

S5의 목적은
`consumer_check_state_v1 + late reconciliation + 7-stage display`
구조는 유지한 채,
`BTCUSD / NAS100 / XAUUSD`의 최근 scene family 노출 밀도를
더 자연스럽게 맞추는 것이었다.

이번 라운드는 새 체계를 추가하지 않고,
`downgrade + cadence suppression`
만으로 최근 imbalance를 줄이는 데 집중했다.

---

### 이번에 반영한 규칙

#### 1. BTC lower rebound probe downgrade

대상 family:

- `symbol=BTCUSD`
- `observe_reason=lower_rebound_probe_observe`
- `blocked_by in {barrier_guard, forecast_guard}`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=btc_lower_buy_conservative_probe`

반영:

- `PROBE -> OBSERVE` downgrade

의도:

- 계속 하락 중인 장면에서 `BUY PROBE`가 너무 공격적으로 보이던 체감을 줄인다
- 구조적 의미는 남기되, 실제 진입에 가까운 표기로 과장되지 않게 한다

#### 2. BTC lower rebound probe cadence suppression

대상 family:

- 위 BTC lower rebound probe family
- 동일 signature가 recent runtime row에 이미 visible로 존재할 때

반영:

- late reconciliation에서 `display_ready=false`
- `blocked_display_reason=btc_lower_probe_cadence_suppressed`

의도:

- 같은 하락 말단 buy observe가 시도때도 없이 반복 표기되는 문제를 줄인다

#### 3. NAS structural observe cadence suppression

대상 family:

- `symbol=NAS100`
- `observe_reason=outer_band_reversal_support_required_observe`
- `blocked_by=outer_band_guard`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=nas_clean_confirm_probe`
- `stage=OBSERVE`

반영:

- 동일 signature가 recent runtime row에 이미 visible이면
- late reconciliation에서 `display_ready=false`
- `blocked_display_reason=nas_structural_cadence_suppressed`

의도:

- NAS의 structural observe가 같은 시그니처로 과도하게 이어질 때 화면 도배를 줄인다

---

### 테스트 결과

추가/강화된 테스트:

- `tests/unit/test_consumer_check_state.py`
  - `test_build_consumer_check_state_downgrades_btc_lower_rebound_probe_to_observe`
  - `test_resolve_effective_consumer_check_state_suppresses_repeated_btc_lower_probe_observe`
  - `test_resolve_effective_consumer_check_state_suppresses_repeated_nas_structural_observe`

회귀 결과:

- `pytest tests/unit/test_consumer_check_state.py -q`
  - `11 passed`
- `pytest tests/unit/test_entry_service_guards.py tests/unit/test_chart_painter.py tests/unit/test_entry_try_open_entry_probe.py tests/unit/test_entry_try_open_entry_policy.py -q`
  - `153 passed`

---

### Runtime 재관측

재시작과 verify 이후:

- `manage_cfd.bat verify`
  - `/health` OK
  - `/trades/summary` OK
  - `/trades/closed_recent` OK

#### BTCUSD

재시작 직후 이전 window에는
`lower_rebound_probe_observe + barrier_guard + probe_not_promoted + PROBE + display=true`
row가 남아 있었지만,
새 row부터는 아래처럼 내려왔다.

- `2026-03-27T22:34:54`
- `2026-03-27T22:35:47`
- `2026-03-27T22:35:53`
- `2026-03-27T22:35:58`
- `2026-03-27T22:36:04`
- `2026-03-27T22:36:11`

공통 상태:

- `observe_reason=lower_rebound_probe_observe`
- `blocked_by=barrier_guard`
- `action_none_reason=probe_not_promoted`
- `consumer_check_stage=OBSERVE`
- `consumer_check_display_ready=false`

해석:

- BTC의 buy-side leakage는 이번 라운드에서 실제 recent window 기준으로 내려왔다

#### NAS100

재시작 이전 window에서는
`outer_band_reversal_support_required_observe + outer_band_guard + probe_not_promoted + OBSERVE + display=true`
가 많이 보였지만,
재시작 이후 immediate window에서는 main family가 아래로 이동했다.

- `lower_rebound_confirm`
- `blocked_by=barrier_guard`
- `action_none_reason=observe_state_wait`
- `consumer_check_stage=PROBE`
- `consumer_check_display_ready=false`

해석:

- NAS structural observe spam은 post-restart immediate window에서 더 이상 표면 main family가 아니었다
- cadence suppression contract는 direct test로 잠겼고,
  runtime에서는 family surface가 이미 hidden/blocked 쪽으로 이동한 상태를 확인했다

#### XAUUSD

이번 라운드에서 XAU 전용 추가 rule은 넣지 않았다.

post-restart immediate window:

- `observe_reason=conflict_box_upper_bb20_lower_lower_dominant_observe`
- `action_none_reason=observe_state_wait`
- `display=false`

해석:

- XAU는 이번 S5에서 별도 악화 없이 기존 hidden/conflict 상태를 유지했다
- 이번 라운드의 직접 대상은 BTC/NAS balance였다

---

### 현재 판단

이번 S5는 아래를 달성했다.

- BTC의 하락 말단 buy probe 과다를 줄였다
- NAS structural observe 반복 노출을 late contract 차원에서 막았다
- XAU는 추가 imbalance 없이 유지했다
- 공통 ladder(`70 / 80 / 90`, `1 / 2 / 3 repeat`)는 그대로 유지했다

즉 S5는
`scene contract 이후 symbol-level balance tuning`
을 최소 수정으로 한 번 닫은 단계로 볼 수 있다.

---

### 아직 남은 것

#### 1. NAS next-window 확인

이번 post-restart immediate window에서는
NAS main family가 structural observe에서 hidden lower confirm 쪽으로 이동했다.

즉,
`nas_structural_cadence_suppressed`
가 live에서 여러 번 반복되는 장면을 한 윈도우 더 보면 더 좋다.

#### 2. XAU family balance 재평가

이번 라운드에서는 XAU를 적극적으로 더 건드리지 않았다.
다음 단계에서 acceptance를 볼 때
`upper reject / middle anchor / outer band`
family balance를 다시 점검하는 것이 좋다.

---

### 다음 단계

다음 active step은 `S6 acceptance`가 맞다.

S5 이후에는

- tri-symbol imbalance가 다시 과도하게 재발하는지
- chart 체감과 runtime reason이 계속 맞는지
- 추가 symbol-specific tuning이 필요한지

를 acceptance 기준으로 판단하면 된다.
