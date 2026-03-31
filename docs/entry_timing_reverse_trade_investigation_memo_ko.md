# Entry Timing Reverse-Trade Investigation Memo

## 1. 목적

이 문서는 최근 사용자가 체감한

- 들어간 직후 바로 반대로 가는 진입
- 차트상으로는 그럴듯했는데 실제 체결 품질이 낮은 진입

을 기준으로, 실제 자동 청산 이력에서 어떤 family가 반복되는지 정리하고
다음 수정 방향을 고정하기 위한 메모다.

이 문서는 `chart check` 문제가 아니라 `entry timing quality` 문제를 다룬다.

---

## 2. 이번 확인에서 본 데이터 범위

주로 본 파일:

- `c:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv`
- `c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv`

참고 사항:

- 현재 최신 `entry_decisions.csv` recent window에는 실제 자동 진입 row가 거의 없고,
  `action=''`, `consumer_effective_action=NONE` 상태가 대부분이다.
- 즉 현재 즉시 재현 가능한 live auto-entry보다,
  직전까지 쌓인 실제 자동 청산 이력을 기준으로 공통 family를 먼저 잡는 것이 더 유효했다.

---

## 3. 핵심 관찰 결과

### 3-1. 가장 강한 문제 family는 BTC/NAS의 lower reversal buy

실제 auto closed trade 기준으로 최근 짧은 보유/역행 케이스를 보면,
가장 반복되는 family는 아래다.

- `BTCUSD BUY range_lower_reversal_buy`
- `NAS100 BUY range_lower_reversal_buy`

대표 특징:

- 보유 시간이 매우 짧다
- 손실 또는 매우 작은 수익 후 청산된다
- `Protect Exit / Emergency Stop / hard_guard=adverse`가 자주 붙는다
- exit reason에 반복적으로 아래가 보인다
  - `Structure: H1 bear stack`
  - `Flow: trend spread down`
  - `TopDown 1D: bearish`
  - `TopDown 4H: bearish`

즉 해석하면:

- entry는 `하단 반등 후보`로 열리는데
- exit은 거의 즉시 `상위 하락 구조가 강하다`고 말하고 있다

이는 현재 lower reversal buy가
`하락 말단 반등 관찰`에서 `실제 진입 허용`으로 너무 빨리 넘어간다는 뜻이다.

### 3-2. NAS lower reversal buy는 특히 “너무 이른 반등 매수” 성격이 강함

대표 케이스:

- `2026-03-27 19:35:57 close`
- `2026-03-27 19:13:56 close`
- `2026-03-27 19:12:47 close`
- `2026-03-27 18:04:44 close`
- `2026-03-27 17:36:14 close`

공통 특징:

- `entry_setup_id = range_lower_reversal_buy`
- entry reason은 대체로
  - `BB lower edge`
  - `box lower zone`
  - `RSI divergence up`
  - `RSI low`
- 그런데 exit은 거의 바로
  - `H1 bear stack`
  - `trend spread down`
  - `TopDown bearish`
  - `hard_guard=adverse`

즉 NAS는
`lower edge + RSI signal`만으로는 아직 entry를 열면 안 되는 문맥이 반복되고 있다.

### 3-3. BTC lower reversal buy도 같은 문제를 보이지만 NAS보다 약간 덜 심함

대표 케이스:

- `2026-03-27 19:01:11 close`
- `2026-03-27 19:08:52 close`
- `2026-03-27 19:12:09 close`

공통 특징:

- `entry_setup_id = range_lower_reversal_buy`
- entry reason은 NAS와 유사
  - `BB lower edge`
  - `box lower zone`
  - `RSI divergence up`
  - `H1 RSI oversold`
- exit은 역시
  - `H1 bear stack`
  - `trend spread down`
  - `TopDown 1D bearish`

즉 BTC도 lower reversal buy가 동일한 방향의 timing 문제를 가진다.
다만 NAS보다 noise와 반등 폭이 커서 결과가 조금 덜 나쁘게 보이는 경우가 있다.

### 3-4. XAU는 다른 축의 문제다

XAU는 최근 auto adverse 케이스가 주로:

- `range_upper_reversal_sell`
- 일부 `BUY` generic family

에서 나온다.

하지만 성격은 BTC/NAS lower buy와 조금 다르다.

- BTC/NAS는 `하락 중 반등 매수`가 너무 빨리 열린다
- XAU는 `upper reject / reversal sell`이 과도하게 반복되거나 churn되는 성격이 있었다

즉 XAU는 이미 scene refinement 쪽에서 많이 다뤘고,
지금 실제 timing quality의 1순위는 BTC/NAS lower reversal buy다.

---

## 4. 현재 문제를 한 문장으로 요약하면

현재 entry timing의 핵심 문제는:

`lower reversal buy family가 아직도 상위 하락 구조(H1 bear stack, bearish topdown, trend spread down) 안에서 너무 일찍 진입 허용되고 있다`

이다.

---

## 5. 왜 이런 문제가 생기는가

### 5-1. 반등 신호와 추세 지속 신호가 동시에 있을 때 반등 쪽이 너무 쉽게 통과됨

현재 entry reason은 주로

- `BB lower edge`
- `box lower zone`
- `RSI divergence up`
- `RSI low`

를 보고 lower reversal buy를 연다.

하지만 실제 exit reason은 거의 즉시

- `H1 bear stack`
- `trend spread down`
- `TopDown bearish`

를 더 강하게 보고 있다.

즉 entry 측과 exit 측의 “누가 더 강한 문맥인가” 판정이 어긋난다.

### 5-2. 관찰(display)과 진입(entry)이 완전히 같은 기준은 아님

scene refinement로 chart check는 많이 정리됐지만,
실제 문제는 이제 `보여주는 것`이 아니라 `들어가게 하는 것`이다.

그래서 지금은:

- display는 약한 observe로 남겨도 됨
- entry는 한 단계 더 늦춰야 함

이라는 분리가 필요하다.

### 5-3. lower family는 must-show일 수 있어도 entry-eligible은 아닐 수 있음

이게 가장 중요하다.

현재 lower rebound / lower reversal family는

- 차트에서 약한 observe는 보여줄 가치가 있지만
- 실제 entry는 더 강한 confirm이 오기 전까지 막아야 하는 장면

이 많다.

즉 앞으로는
`must-show`와 `entry-eligible`를 더 분리해서 봐야 한다.

---

## 6. 어떻게 고쳐야 하는가

### 방향 A. BTC/NAS lower reversal buy는 entry를 한 단계 늦춘다

가장 우선적인 수정 방향이다.

추천 방식:

1. 아래 조합이면 `display는 허용`, `entry는 차단`
   - `range_lower_reversal_buy`
   - `H1 bear stack`
   - `trend spread down`
   - `TopDown 1D bearish` 또는 `TopDown 4H bearish`

2. 아래 중 하나가 추가되기 전까진 실제 entry 금지
   - `BB20 mid reclaim`
   - `side separation` 개선
   - `candidate_support` 강화
   - `pair_gap` 개선
   - `confirm` 한 단계 추가

3. `RSI low / divergence up` 단독으로는 더 이상 entry 이유가 되지 않게 한다

즉 lower family를 완전히 없애는 게 아니라,
`관찰용 family`와 `실제 진입 가능 family`를 분리하는 방식이다.

### 방향 B. adverse history가 강한 family는 “entry delay family”로 내린다

후속 확장 방식:

- 최근 closed trade 기준으로
  - 짧은 보유
  - 반복 손실
  - `hard_guard=adverse`
  - 같은 `setup_id`

가 반복되는 family는,
일시적으로 `entry delay` 또는 `display only`로 강등하는 방식도 가능하다.

즉 replay/closed-trade 결과를
scene eligibility 조정에 간접적으로 반영하는 것이다.

### 방향 C. painter가 아니라 entry owner에서 고친다

절대 우선순위:

1. `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py`
2. `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py`
3. `c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py`

즉:

- timing 품질 문제는 `entry_service.py`
- late block / late reconciliation은 `entry_try_open_entry.py`
- display는 `consumer_check_state.py`

로 처리해야 한다.

---

## 7. 바로 다음 작업 순서

새 스레드에서도 아래 순서가 가장 안전하다.

1. `trade_closed_history.csv`에서
   - 최근 auto adverse / short-hold 사례 재추출
2. `range_lower_reversal_buy` 중심으로
   - BTC / NAS 케이스를 우선 정리
3. `entry_service.py`에서
   - lower reversal buy entry eligibility를 강화
4. unit test 추가
5. 재시작 후
   - immediate window
   - rolling window
   - 새 closed trade
   까지 확인

---

## 8. 결론

현재 가장 먼저 고쳐야 할 건:

- `BTC/NAS lower reversal buy가 하락 지속 문맥에서 너무 일찍 entry 허용되는 문제`

다.

따라서 다음 수정의 중심은:

- chart 표시를 더 만지는 것보다
- `range_lower_reversal_buy`의 entry gate를 강화하고
- display와 entry를 더 분리하는 것

이어야 한다.
