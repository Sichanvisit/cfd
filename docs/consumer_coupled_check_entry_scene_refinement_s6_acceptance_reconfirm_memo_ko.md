# Consumer-Coupled Check / Entry Scene Refinement
## S6. Acceptance Reconfirm Memo

### 목적

이 문서는

- `BTC/NAS 재균형 reopen`
- `XAU visibility 2차 조정`

까지 반영한 뒤,
S6 acceptance를 다시 판단한 결과를 정리한다.

즉 초기 S6 memo 이후의
최신 재평가 문서다.

---

### 재평가 배경

초기 S6에서는:

- `BTC`는 너무 숨겨져 있었고
- `NAS`는 너무 많이 보였고
- `XAU`는 상대적으로 과표시였다

그래서 verdict는
`reopen S5 tuning`
이었다.

그 뒤 추가 조정:

1. `BTC/NAS` 재균형 reopen
2. `XAU upper reject family` 2차 조정

이 반영됐다.

이번 memo는 그 후 상태를 다시 본 결과다.

---

### 최신 immediate window

#### BTCUSD

최근 20 rows:

- 전부
  - `outer_band_reversal_support_required_observe`
  - `blocked_by=outer_band_guard`
  - `action_none_reason=probe_not_promoted`
  - `stage=OBSERVE`
  - `display=false`

해석:

- BTC는 과거처럼 과표시되지 않는다
- 하지만 현재 immediate window 기준으론 visible check가 없다

#### NAS100

최근 20 rows:

- 전부
  - `outer_band_reversal_support_required_observe`
  - `blocked_by=outer_band_guard`
  - `action_none_reason=probe_not_promoted`
  - `stage=OBSERVE`
  - `display=false`

해석:

- NAS도 현재 immediate window에선 visible check가 없다
- 직전의 과한 lower probe는 사라졌다

#### XAUUSD

최근 20 rows:

- `upper_reject_confirm / upper_reject_mixed_confirm`
- `blocked_by=barrier_guard`
- `action_none_reason=observe_state_wait`
- `stage=PROBE`
- `display=false`

해석:

- XAU의 직접 과표시 family는 실제로 숨겨졌다
- 즉 이번 2차 XAU 조정은 immediate window 기준 성공이다

---

### 최신 rolling recent window

최근 60 rows 기준:

- `BTCUSD: display_true=0 / display_false=56`
- `NAS100: display_true=0 / display_false=56`
- `XAUUSD: display_true=16 / display_false=40`

해석:

- 초기 S6 때의 극단적인 imbalance는 크게 줄었다
- 다만 지금은
  `BTC/NAS/XAU 전반이 hidden 쪽으로 다시 기운 상태`
에 가깝다

즉 문제 성격이

- `한 symbol만 과표시`

에서

- `전체적으로 다소 보수적`

으로 바뀌었다.

---

### wrong-ready / 구조 안정성

최신 recent summary 기준:

- `wrong_ready_count = 0`
- late blocked mismatch 재발 없음
- READY인데 entry_ready=false 재발 없음

해석:

- S4 contract 안정성은 계속 유지된다
- 이번 단계의 문제는 구조 버그가 아니라
  표시 보수성이다

---

### must-show / must-hide 재평가

#### must-hide

판정: `pass`

이유:

- XAU upper reject 과표시 family가 hidden으로 내려왔다
- BTC/NAS도 현재 leaking family가 없다
- wrong-ready 재발 없음

즉
`있으면 안 되는 강한 체크`
문제는 지금 기준으로 많이 잡혔다.

#### must-show

판정: `hold`

이유:

- current window에선 BTC/NAS가 거의 전부 hidden이다
- 즉 `있어야 할 약한 observe`가 너무 적게 보일 가능성이 남는다

즉 must-show는
완전 fail은 아니지만,
freeze하기엔 아직 조심스러운 상태다.

---

### symbol balance 재평가

판정: `hold`

이유:

- 초기 S6처럼 `BTC/NAS/XAU`가 극단적으로 엇갈리진 않는다
- 하지만 지금은
  `균형`이라기보다
  `전반적으로 눌린 균형`
에 가깝다

즉 이전처럼 `fail`은 아니지만,
아직 `accept and freeze`라고 말할 정도로 안정된 것도 아니다.

---

### 최종 verdict

최신 verdict:

- `hold and observe one more window`

이유:

1. 구조 버그는 없다
2. leaking family는 많이 잡혔다
3. symbol imbalance도 초기보다 완화됐다
4. 하지만 현재 immediate/rolling window는 전반적으로 너무 눌린 상태라
   must-show acceptance를 바로 pass로 주기엔 이르다

즉 지금은

- `reopen S4 contract`: 아님
- `reopen S5 tuning`: 당장 필수는 아님
- `accept and freeze`: 아직 이름

보다는

- `hold and observe one more window`

가 가장 맞다.

---

### 다음 단계

가장 자연스러운 다음 액션:

1. 한 윈도우 더 관찰
2. `BTC/NAS`에서 weak visible observe가 자연스럽게 다시 생기는지 확인
3. 그 뒤
   - 생기면 `accept and freeze`
   - 계속 전부 hidden이면 아주 작은 reopen

즉 지금 시점의 최종 판단은:

`scene refinement는 상당히 안정됐고, 이제는 과표시보다 과억제 여부를 한 윈도우 더 보고 닫는 단계`
라고 보면 된다.
