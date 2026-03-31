# Consumer-Coupled Check / Entry Scene Refinement
## S5 XAU Visibility Follow-up Memo

### 목적

이번 follow-up의 목적은
`XAU visibility balance`
를 한 번 더 낮춰보는 것이었다.

직전 상태에서:

- `BTC/NAS`는 재균형이 어느 정도 맞춰졌고
- `XAU`만 visible pressure가 상대적으로 높은 상태였다

따라서 이번 라운드는
`upper reject family`
를 대상으로 최소 suppression을 시도했다.

---

### 이번에 넣은 조정

대상 파일:

- `backend/services/consumer_check_state.py`
- `tests/unit/test_consumer_check_state.py`

#### 반영한 규칙

1. `upper_reject_mixed_confirm + forecast_guard + observe_state_wait`
   - weak `OBSERVE`로 downgrade

2. `upper_reject_confirm / upper_reject_mixed_confirm / upper_reject_probe_observe`
   - `forecast_guard / probe_promotion_gate`
   - `observe_state_wait / probe_not_promoted`
   조합에서 같은 signature가 연속 visible이면
   `xau_upper_reject_cadence_suppressed`
   로 숨기도록 추가

테스트:

- `pytest tests/unit/test_consumer_check_state.py -q`
  - `18 passed`
- 관련 회귀 묶음
  - `153 passed`

---

### runtime 결과

재시작 후 immediate recent window:

- `upper_reject_confirm + forecast_guard + observe_state_wait + OBSERVE + true`
  가 여전히 연속으로 반복되었다

예시:

- `2026-03-27T23:55:52`
- `2026-03-27T23:55:58`
- `2026-03-27T23:56:04`
- `2026-03-27T23:56:11`
- `2026-03-27T23:56:18`
- `2026-03-27T23:56:24`
- `2026-03-27T23:56:31`
- `2026-03-27T23:56:45`
- `2026-03-27T23:56:53`
- `2026-03-27T23:56:59`
- `2026-03-27T23:57:06`

추가 60-row snapshot:

- `BTCUSD: display_true=2 / display_false=58`
- `NAS100: display_true=0 / display_false=60`
- `XAUUSD: display_true=60 / display_false=0`

즉 결과는 분명하다.

- 이번에 의도한 `XAU visibility reduction`은
  runtime recent window 기준으로는 아직 성공하지 못했다

---

### 해석

현재 XAU overpressure의 직접 owner는
대체로 다음 family다.

- `observe_reason=upper_reject_confirm`
- `blocked_by=forecast_guard`
- `action_none_reason=observe_state_wait`
- `consumer_check_stage=OBSERVE`
- `consumer_check_display_ready=true`

즉 현재 문제의 핵심은
`upper_reject_confirm weak observe family`
가 너무 많이 visible로 남는다는 점이다.

이번 cadence suppression은
현재 runtime 경로에서 이 family를 충분히 줄이지 못했다.

---

### 현재 판단

이번 follow-up 결론:

- `BTC/NAS` 재균형은 유지됨
- `XAU`는 여전히 과표시
- 따라서 다음 직접 조정은
  `upper_reject_confirm + forecast_guard + observe_state_wait`
  family 자체를 더 직접적으로 줄이는 쪽이 맞다

즉 다음 후보는:

1. 이 family를 weak visible에서 `hidden`으로 내리기
2. 또는 cadence가 아니라 family-level hard reduce를 넣기

현재 상태로는 후자가 아니라
전자가 더 단순하고 예측 가능해 보인다.

---

### 다음 단계

가장 자연스러운 다음 액션은:

- `XAU upper_reject_confirm weak observe`
  를 한 단계 더 줄이는 2차 조정

즉:

- `forecast_guard + observe_state_wait`
- `upper_reject_confirm`

조합을 계속 weak visible로 둘지,
아니면 hidden으로 내릴지 결정하는 것이다.
