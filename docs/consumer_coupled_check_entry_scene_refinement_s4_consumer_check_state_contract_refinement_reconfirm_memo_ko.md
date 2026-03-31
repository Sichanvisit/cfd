# Consumer-Coupled Check/Entry Scene Refinement
## S4. Consumer Check State Contract Refinement Reconfirm Memo

### 요약

S4의 핵심은 S1/S2/S3에서 분류한 casebook을
실제 `consumer_check_state_v1`와 late reconciliation contract로 내리는 것이었다.

이번 변경으로 아래 4개 축이 코드에 반영됐다.

- `BTC lower structural observe suppression`
- `NAS lower rebound probe downgrade`
- `XAU middle anchor cadence reduction`
- `XAU upper reject family reconciliation`

---

### 변경된 contract

#### 1. BTC lower structural observe suppression

대상 family:

- `BTCUSD`
- `outer_band_reversal_support_required_observe`
- `blocked_by=outer_band_guard`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=btc_lower_buy_conservative_probe`

변경:

- 같은 signature가 연속 runtime row에서 반복되면
  late reconciliation에서 `display_ready=false`로 내린다.
- stage는 `OBSERVE`로 유지하고,
  cadence만 줄인다.

직접 owner:

- `backend/services/consumer_check_state.py`
- `backend/services/entry_try_open_entry.py`

#### 2. NAS lower rebound probe downgrade

대상 family:

- `NAS100`
- `lower_rebound_probe_observe`
- `action_none_reason=probe_not_promoted`
- `probe_scene_id=nas_clean_confirm_probe`
- `blocked_by in {"", "probe_promotion_gate", "forecast_guard"}`

변경:

- `PROBE -> OBSERVE`
- `display_score`는 OBSERVE band로 내려간다
- `display_repeat_count`는 1회로 수렴한다

직접 owner:

- `backend/services/consumer_check_state.py`

#### 3. XAU middle anchor cadence reduction

대상 family:

- `XAUUSD`
- `middle_sr_anchor_required_observe`
- `blocked_by=middle_sr_anchor_guard`
- `action_none_reason=observe_state_wait`

변경:

- 첫 surface는 유지
- 같은 signature 연속 반복은 late reconciliation에서 숨긴다

직접 owner:

- `backend/services/consumer_check_state.py`
- `backend/services/entry_try_open_entry.py`

#### 4. XAU upper reject family reconciliation

대상 family:

- `XAUUSD`
- `upper_reject_confirm`
- `blocked_by=forecast_guard`
- `action_none_reason=observe_state_wait`

변경:

- 완전 hidden 대신 `weak observe`로 남길 수 있게 contract를 열었다
- `upper_break_fail_confirm`의 반복 suppression과는 분리했다

직접 owner:

- `backend/services/consumer_check_state.py`

---

### 테스트 결과

직접 테스트:

- `pytest tests/unit/test_consumer_check_state.py -q`
- 결과: `8 passed`

회귀 묶음:

- `pytest tests/unit/test_entry_service_guards.py tests/unit/test_chart_painter.py tests/unit/test_entry_try_open_entry_probe.py tests/unit/test_entry_try_open_entry_policy.py -q`
- 결과: `153 passed`

---

### Runtime 재관측

#### 확인된 것

- API verify는 재시작 직후 bootstrap delay가 있었지만 재시도에서 정상 통과했다.
- `BTCUSD outer_band_reversal_support_required_observe`는 실제 recent row에서
  반복 surface가 `display=false`로 내려간 case가 확인됐다.
  - 예: `2026-03-27T22:15:40`
- `NAS100`는 재시작 후 latest window에서 family가 `lower_rebound_probe_observe`보다
  `outer_band_reversal_support_required_observe` 쪽으로 더 많이 표면화돼서,
  이번 window에서는 downgrade 대상 family가 많이 재발하지 않았다.
- `XAUUSD upper_reject_confirm + forecast_guard + observe_state_wait`는
  direct test로는 보장되지만, 재시작 후 latest window에서는 같은 exact path가 다시 많이 나타나지 않았다.

#### 해석

- `BTC cadence suppression`은 runtime에서도 확인됐다.
- `NAS downgrade`, `XAU reconciliation`은 contract와 direct test는 닫혔고,
  runtime latest window에서는 exact family 재발이 제한적이었다.

---

### 남은 이슈

이번 S4로 해결한 것은 `contract mismatch`다.

아직 남는 것은 주로 `scene balance` 쪽이다.

- `BTC lower_rebound_probe_observe`는 여전히 PROBE 비중이 높다
- `NAS100`은 restart 이후 lower probe보다 structural observe family가 더 자주 뜬다
- `XAUUSD`는 upper reject family와 outer-band family의 체감 균형이 추가로 필요하다

즉 다음 단계는 S5다.

- symbol balance tuning
- must-show / must-hide contract가 반영된 뒤 남는 장면 밀도 미세조정

---

### 최종 판정

S4는 다음 의미에서 완료로 본다.

- S1/S2/S3 casebook이 실제 contract rule로 내려갔다
- late reconciliation 경계에 cadence suppression이 반영됐다
- regression test가 잠겼다
- runtime에서 BTC suppression까지는 직접 확인됐다

단,

- `NAS downgrade`
- `XAU upper reject reconciliation`

은 latest runtime window에서 exact family 재관측이 더 쌓이면 한 번 더 확인하는 것이 좋다.
