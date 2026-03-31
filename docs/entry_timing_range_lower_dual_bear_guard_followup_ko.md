# Entry Timing Follow-up: Range Lower Dual-Bear Guard

## 목적

최근 auto adverse trade 조사 결과를 바탕으로,
`BTCUSD / NAS100 range_lower_reversal_buy`가
상위 하락 문맥에서 너무 일찍 진입 허용되던 문제에 대해
적용한 수정과 현재 확인 상태를 정리한다.

---

## 조사 근거

`trade_closed_history.csv` 기준으로 최근 adverse / short-hold auto trade를 확인했을 때,
다음 패턴이 반복됐다.

- `symbol in {BTCUSD, NAS100}`
- `entry_setup_id = range_lower_reversal_buy`
- `entry_h1_gate_pass = 0`
- `entry_topdown_gate_pass = 0`
- exit 쪽은 반복적으로
  - `H1 bear stack`
  - `trend spread down`
  - `TopDown bearish`
  - `hard_guard=adverse`

즉 global gate mode가 `soft`라서,
원래라면 걸러졌어야 하는 dual-bear 문맥의 lower reversal buy가
실제로 entry까지 허용되고 있었다.

---

## 적용한 수정

대상 파일:

- `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py`

핵심 변경:

- `_should_block_range_lower_buy_dual_bear_context(...)` helper 추가
- 아래 조건이면 soft mode와 무관하게 skip:
  - `symbol in {BTCUSD, NAS100}`
  - `action == BUY`
  - `setup_id == range_lower_reversal_buy`
  - `entry_h1_gate_pass == False`
  - `entry_topdown_gate_pass == False`

skip reason:

- `range_lower_buy_dual_bear_context_blocked`

즉 차트/관찰 family는 유지될 수 있어도,
실제 entry는 이제 dual-bear 문맥에서 바로 열리지 않게 바뀌었다.

---

## 테스트

추가/수정 테스트:

- `c:\Users\bhs33\Desktop\project\cfd\tests\unit\test_entry_try_open_entry_probe.py`

검증 결과:

- `test_entry_try_open_entry_probe.py` → `18 passed`
- `test_entry_try_open_entry_policy.py + test_entry_service_guards.py + test_chart_painter.py` → `139 passed`

즉 helper와 주변 회귀는 모두 통과했다.

---

## 런타임 확인 상태

재시작 후:

- `/health` 수동 확인 OK
- 프로세스 정상 기동 확인

다만 현재 최신 `entry_decisions.csv` recent window에는
새로운 `range_lower_reversal_buy` auto-entry 사례가 바로 재발하지 않았다.

즉 현재 상태는:

- 코드 수정: 완료
- 회귀 테스트: 완료
- API 재기동: 완료
- live family 재발 기준 직접 확인: 대기

---

## 다음 확인 포인트

다음 live/recent window에서 아래를 우선 확인한다.

1. `BTCUSD / NAS100`
2. `setup_id = range_lower_reversal_buy`
3. `entry_h1_gate_pass = false`
4. `entry_topdown_gate_pass = false`

이 조합에서:

- 더 이상 `entered`가 나오지 않는지
- `blocked_by = range_lower_buy_dual_bear_context_blocked`로 남는지

를 보면 된다.

만약 여전히 진입한다면,
다음 후보는:

- `h1=false, topdown=true`
- `h1=true, topdown=false`

중 어느 쪽도 성능이 나쁜지 다시 확인해서
lower reversal buy gating을 한 단계 더 강화해야 한다.
