# Consumer-Coupled Check / Entry Scene Refinement
## S5 XAU Visibility Second Adjustment Memo

### 목적

이 문서는
`XAU visibility balance`
2차 조정의 결과를 정리한다.

1차 follow-up에서는
`forecast_guard`
기준으로만 upper reject family를 줄이려 했지만,
runtime recent window를 보니 실제 dominant owner는

- `upper_reject_confirm`
- `upper_reject_mixed_confirm`
- `blocked_by=barrier_guard`
- `action_none_reason=observe_state_wait`

조합이었다.

즉 문제는
`forecast_guard`가 아니라
`barrier_guard + observe_state_wait` 경로였다.

---

### 이번 2차에서 반영한 것

대상 파일:

- `backend/services/consumer_check_state.py`
- `tests/unit/test_consumer_check_state.py`

#### 반영한 규칙

1. `upper_reject_confirm`
2. `upper_reject_mixed_confirm`

위 두 family에 대해:

- `symbol=XAUUSD`
- `side=SELL`
- `blocked_by in {forecast_guard, barrier_guard}`
- `action_none_reason=observe_state_wait`

이면

- build 단계에서 `display=false`
- late `PROBE/OBSERVE` 단계에서도 다시 `display=false`
- `blocked_display_reason=xau_upper_reject_guard_wait_hidden`

이 되도록 맞췄다.

즉,
`weak visible observe`
가 아니라
`hidden blocked family`
로 내린 것이다.

---

### 테스트

강화된 테스트:

- `test_build_consumer_check_state_hides_xau_upper_reject_confirm_under_barrier_wait`
- `test_build_consumer_check_state_hides_xau_upper_reject_mixed_confirm_under_barrier_wait`
- `test_resolve_effective_consumer_check_state_hides_xau_upper_reject_confirm_under_barrier_wait`

결과:

- `pytest tests/unit/test_consumer_check_state.py -q`
  - `21 passed`
- 관련 회귀 묶음
  - `153 passed`

---

### runtime 결과

재시작 후 XAU recent window:

- `upper_reject_mixed_confirm + barrier_guard + observe_state_wait`
- `upper_reject_confirm + barrier_guard + observe_state_wait`

가 여전히 `consumer_check_stage=PROBE`로 남아 있지만,
이제 전부

- `consumer_check_display_ready=false`

로 내려왔다.

즉 stage는 남겨도,
차트상 visible check는 사라진 상태다.

대표 row:

- `2026-03-28T00:07:37`
- `2026-03-28T00:07:41`
- `2026-03-28T00:07:45`
- `2026-03-28T00:08:08`
- `2026-03-28T00:08:12`
- `2026-03-28T00:08:16`

공통 상태:

- `observe_reason in {upper_reject_confirm, upper_reject_mixed_confirm}`
- `blocked_by=barrier_guard`
- `action_none_reason=observe_state_wait`
- `consumer_check_side=SELL`
- `consumer_check_stage=PROBE`
- `consumer_check_display_ready=false`

해석:

- XAU의 핵심 과표시 family는 이번 2차에서 실제로 숨겨졌다

---

### 60-row snapshot

최근 60 rows 기준:

- `BTCUSD: display_true=0 / display_false=39`
- `NAS100: display_true=0 / display_false=39`
- `XAUUSD: display_true=16 / display_false=23`

해석:

- 직전 상태의
  `XAU display_true=60 / display_false=0`
에서
  상당히 내려왔다
- 현재는 XAU도 hidden mix가 생겨서,
  더 이상 한 family가 그대로 화면을 도배하는 상태는 아니다

---

### 현재 판단

이번 2차 조정은 성공으로 본다.

이유:

- 직접 owner였던
  `upper_reject_confirm / mixed_confirm + barrier_guard + observe_state_wait`
  family가 runtime에서 실제로 hidden으로 내려왔다
- 테스트와 runtime recent row가 같은 결론을 준다

즉
`XAU overpressure`
는 이번 라운드에서 많이 완화된 상태다.

---

### 남은 것

현재 immediate recent snapshot만 보면:

- `BTC`도 다시 거의 hidden 쪽으로 내려왔고
- `NAS`도 hidden 쪽 비중이 높다

즉 다음 단계는 다시

- `S6 acceptance`

를 짧게 재평가해서
이제 freeze 가능한지,
아니면 관찰 한 윈도우가 더 필요한지 보는 것이 맞다.

---

### 다음 단계

가장 자연스러운 다음 액션:

1. `S6 acceptance` 재평가
2. tri-symbol current 60-row / 100-row snapshot 재확인
3. `pass / hold / reopen` 최종 판정
