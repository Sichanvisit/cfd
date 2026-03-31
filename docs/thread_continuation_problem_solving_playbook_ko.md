# CFD Scene / Entry Timing Problem-Solving Playbook

## 1. 문서 목적

이 문서는 새 스레드에서 작업을 다시 시작할 때,

- 지금까지 무엇을 구축했는지
- 현재 실제 문제는 무엇인지
- 왜 그런 문제가 생기는지
- 어떤 방식으로 조사하고 고쳐야 하는지
- 무엇을 건드리면 되고 무엇은 건드리지 말아야 하는지

를 한 번에 이어받기 위한 실전용 플레이북이다.

핵심 목적은 `차트 체크 표기 문제`와 `실제 진입 품질 문제`를 섞지 않고,
현재 남은 핵심 과제인 `들어가자마자 바로 반대로 가는 진입`을
실제 체결 기준으로 해결하는 것이다.

---

## 2. 지금까지 구축된 큰 구조

### 2-1. refinement 본선

이미 정리된 큰 트랙은 아래와 같다.

- `R0`: reason / key 정합성
- `R1`: Stage E 미세조정
- `R2`: storage / export / replay / dataset 정합성
- `R3`: semantic ML refinement + shadow compare / source cleanup
- `R4`: acceptance / promotion-ready / allowlist 운영 정리

즉 지금은 기반이 없는 상태가 아니라,
`runtime / export / replay / semantic ML / rollout`의 큰 배관은 이미 연결된 상태다.

### 2-2. consumer-coupled check / entry 구조

최근 별도 트랙으로 아래를 구축했다.

- `consumer_check_state_v1`
- `display_score`
- `display_repeat_count`
- chart 7단계 display 체계
- `chart_painter`가 raw reason보다 `consumer_check_state_v1`를 우선 번역하는 구조
- late blocked mismatch 제거

핵심 owner 파일:

- `c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py`
- `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py`
- `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py`
- `c:\Users\bhs33\Desktop\project\cfd\backend\trading\chart_painter.py`

즉 현재 구조는:

1. router / entry 쪽이 의미를 만든다
2. consumer_check_state가 chart용 pre-entry state를 만든다
3. try_open_entry가 late block를 반영한다
4. chart_painter는 그 상태를 그린다

---

## 3. 지금까지 해결된 것

### 3-1. 해결된 구조 문제

- `blocked인데 READY처럼 보이는 문제`
- `late blocked mismatch`
- `wrong_ready`
- XAU upper reject family 과표시
- BTC / NAS / XAU 표기 계약이 서로 완전히 따로 놀던 문제

현재 중요한 구조 안정성 지표:

- `wrong_ready_count = 0`
- late blocked mismatch 재발 없음

즉 `표시와 실제 entry 상태가 구조적으로 엇갈리는 버그`는 많이 정리된 상태다.

### 3-2. scene refinement 진행 상태

`S0~S6`까지는 이미 정리됐다.

- `S0`: baseline snapshot
- `S1`: must-show scene casebook
- `S2`: must-hide scene casebook
- `S3`: visually similar scene alignment audit
- `S4`: contract refinement
- `S5`: symbol balance tuning
- `S6`: acceptance

현재 최신 판정은 `freeze`가 아니라:

- `hold and observe one more window`

이유는 `과표시`는 많이 줄었지만,
지금은 반대로 `과억제` 가능성도 있기 때문이다.

---

## 4. 지금 남은 진짜 문제

현재 가장 중요한 문제는 이것이다.

### 문제 A. 실제 진입이 들어간 직후 바로 반대로 가는 현상

사용자 체감 기준 핵심 이슈:

- 진입한 타점에 들어갔는데 곧바로 역행
- 차트상으로는 buy/sell 가능성이 높아 보였는데 실제로는 계속 반대로 감
- 특히 `BTC / NAS`에서 하락 중 lower rebound 계열이 너무 낙관적으로 열리는 느낌

이건 더 이상 단순 `차트 표기 문제`가 아니다.
지금부터는 `실제 체결 / 실제 청산 / 진입 직전 entry_decisions row`를 묶어 봐야 한다.

### 문제 B. scene display와 entry timing의 마지막 연결 품질

현재 구조는 연결되어 있지만 아직 완전히 같은 축으로 잠기진 않았다.

즉:

- 차트에 떠야 할 체크는 어느 정도 정리됨
- 숨겨야 할 체크도 어느 정도 정리됨
- 하지만 실제 entry gate가 어떤 scene을 통과시키는지가
  사용자의 체감과 아직 완전히 일치하진 않음

그래서 이제부터의 초점은:

`check를 어떻게 그릴까`가 아니라
`어떤 family가 실제 진입을 통과하고, 그 진입이 왜 바로 깨지는가`

이다.

---

## 5. 왜 이런 문제가 생기는가

현재까지 드러난 원인은 크게 네 가지다.

### 5-1. lower rebound family가 실제 하락 지속과 겹치는 경우

BTC / NAS에서 많이 보인 패턴:

- `lower_rebound_probe_observe`
- `lower_rebound_confirm`
- `outer_band_reversal_support_required_observe`

이 family는 원래 “하락 말단 반등 후보”를 잡는 장면이지만,
실제론 계속 내려가는 중간에도 약하게 반복 생성될 수 있다.

즉 구조적으로는 그럴듯하지만,
실전 체결 기준으로는 아직 너무 이른 시점일 수 있다.

### 5-2. guard가 차단은 하지만, family 자체는 계속 유지되는 경우

예:

- `barrier_guard`
- `forecast_guard`
- `probe_not_promoted`
- `observe_state_wait`

이런 guard가 붙어도 family는 살아 있고,
어떤 경우에는 늦게 풀리거나 다음 봉에서 다시 시도되면서
실제 timing 품질이 나빠질 수 있다.

### 5-3. symbol temperament 차이

동일해 보이는 장면도 심볼마다 다르게 해석된다.

- BTC: lower buy family가 자주 살아남음
- NAS: lower family와 outer band family가 과하게 surface될 수 있음
- XAU: upper reject / conflict family가 과하게 surface되던 적이 있었음

즉 단순히 캔들 모양만 비슷하다고 같은 진입 품질을 기대하면 안 된다.

### 5-4. display tuning과 entry tuning은 다르다

이전에는 차트 표기 문제를 많이 손봤지만,
지금 남은 건 `표시가 과한가`보다 `entry gate가 너무 이른가`에 가깝다.

따라서 지금부터는 painter가 아니라
실제 진입 owner를 다시 봐야 한다.

---

## 6. 앞으로 해결하는 방식

이제부터는 아래 순서로 해결해야 한다.

### Step 1. 최근 실제 손실 / 짧은 보유 청산을 먼저 뽑는다

주 대상:

- `c:\Users\bhs33\Desktop\project\cfd\data\trades\trade_closed_history.csv`
- 필요 시 `trade_history.csv`

여기서 먼저 찾아야 하는 건:

- 최근 진입 후 짧은 시간 안에 청산된 거래
- 바로 손실 또는 미미한 수익 후 역행한 거래
- symbol별 반복 family

### Step 2. 그 거래의 직전 entry_decisions row를 매칭한다

주 대상:

- `c:\Users\bhs33\Desktop\project\cfd\data\trades\entry_decisions.csv`
- 필요 시 `entry_decisions.detail.jsonl`

봐야 할 핵심 필드:

- `symbol`
- `time`
- `setup_id`
- `observe_reason`
- `blocked_by`
- `action_none_reason`
- `consumer_check_stage`
- `consumer_check_display_ready`
- `consumer_effective_action`
- `core_reason`
- `probe_scene_id`
- `entry_stage`
- `entry_wait_state`
- `semantic_live_reason`

즉 `실제 체결`과 `그 직전의 의사결정 row`를 1:1로 묶는 것이 먼저다.

### Step 3. 공통 family를 분류한다

반드시 이렇게 묶어야 한다.

- `lower rebound buy`
- `outer band structural buy`
- `upper reject sell`
- `middle anchor wait`
- `conflict family`

그 다음 각 family를 아래 중 하나로 판정한다.

- `must tighten`
- `must delay`
- `must downgrade`
- `display only, no entry`
- `keep as is`

### Step 4. entry owner에서 수정한다

핵심 원칙:

- painter로 해결하지 않는다
- display만 손보지 않는다
- 실제 진입을 여는 owner에서 조정한다

우선순위 owner:

1. `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_service.py`
2. `c:\Users\bhs33\Desktop\project\cfd\backend\services\entry_try_open_entry.py`
3. `c:\Users\bhs33\Desktop\project\cfd\backend\services\consumer_check_state.py`

정리하면:

- entry timing 문제는 `entry_service.py`
- late guard / late reconciliation 문제는 `entry_try_open_entry.py`
- chart stage / display 조정은 `consumer_check_state.py`

### Step 5. 수정은 작게 한다

수정 방식은 아래 네 가지 중 하나로 고정하는 것이 좋다.

- `hide`
- `downgrade`
- `delay`
- `require one more confirmation`

가급적 피해야 할 것:

- 한 번에 큰 재설계
- 심볼 전체를 통째로 열거나 닫기
- painter에서 억지로 체감만 맞추기

### Step 6. 테스트와 관찰을 같이 본다

순서는 항상 이렇다.

1. unit test
2. restart
3. immediate window 확인
4. rolling recent window 확인
5. 실제 체결 후속 관찰

즉 `테스트 통과 = 해결`이 아니다.
현재 문제는 실제 체결 품질이므로,
반드시 runtime / closed trade까지 같이 봐야 한다.

---

## 7. 어떤 방식으로 고쳐야 하는가

현재 기준으로 가장 현실적인 해결 방식은 아래 두 축이다.

### 축 A. lower rebound buy 진입을 더 늦춘다

대상:

- BTC lower rebound buy
- NAS lower rebound buy

가능한 방법:

- `barrier_guard` 상태에서는 display만 남기고 entry는 더 보수적으로
- `probe_not_promoted`가 반복되는 family는 entry 재시도 완화
- `forecast_guard` 또는 `execution_soft_blocked`가 붙은 lower family는
  `confirm`이 하나 더 붙어야 entry 허용
- `display_score`는 유지하되 `entry gate`만 한 단계 더 높임

즉 차트에서 관찰은 하되,
실제 진입은 지금보다 한 박자 늦게 여는 방식이다.

### 축 B. conflict / weak structural family는 entry에서 분리한다

대상:

- XAU upper reject / conflict 계열
- BTC/NAS structural observe 계열 중 약한 family

가능한 방법:

- `display only, no entry` family로 분리
- `weak OBSERVE`는 보여주되 entry_ready는 절대 true로 안 감
- scene family별로 `must-show`와 `entry-eligible`를 분리

즉 앞으로는

- `보여야 하는 체크`
- `진짜 들어가도 되는 체크`

를 같은 체인 안에서 연결하되, 완전히 동일하게 두지 않는 게 핵심이다.

---

## 8. 새 스레드에서 바로 할 수 있는 실전 액션

새 스레드에서는 아래 순서대로 들어가면 된다.

### 8-1. 조사

1. 최근 손실 / 짧은 보유 청산 거래 추출
2. 해당 거래의 직전 entry_decisions row 매칭
3. symbol별 공통 family 분류

### 8-2. 판정

각 family를 아래 중 하나로 고른다.

- `entry too early`
- `display acceptable but entry not acceptable`
- `late guard insufficient`
- `exit too slow`
- `family should not enter at all`

### 8-3. 수정

다음 우선순위대로 간다.

1. `entry_service.py`
2. `entry_try_open_entry.py`
3. `consumer_check_state.py`

### 8-4. 검증

- 관련 unit tests
- restart
- immediate window
- rolling 60 window
- closed trade follow-up

---

## 9. 지금 건드리지 않는 것이 좋은 것

지금은 아래를 먼저 건드리지 않는 게 좋다.

- `chart_painter.py`만으로 체감 보정
- semantic ML threshold만으로 해결하려는 접근
- Stage E / rollout 전체 재설계
- allowlist / bounded live를 다시 크게 건드리는 것

이유는 현재 핵심 문제가
`차트 표기`나 `promotion 상태`가 아니라
`실제 진입 타이밍 품질`이기 때문이다.

---

## 10. 현재 최종 정리

현재 프로젝트 상태는 이렇게 보는 게 가장 정확하다.

- 기반 구조는 이미 충분히 구축됨
- chart / consumer / entry 연결도 많이 정리됨
- scene refinement도 `S0~S6`까지 한 바퀴 돌았음
- 남은 핵심은 `진입이 왜 너무 이르게 열리는지`를 실제 체결 기준으로 잡는 것

즉 다음 문제 해결의 중심은:

`최근 역행 진입 사례를 뽑아 family를 특정하고, entry gate를 더 늦추거나 family를 display-only로 내리는 것`

이다.

새 스레드에서 이 문서를 기준으로 시작하면,
다시 처음부터 chart 표시 문제로 되돌아가지 않고
바로 `실제 entry timing 문제`를 조사하는 흐름으로 들어갈 수 있다.
