# Current Countertrend Continuation Candidate External Review Request

## 목적

이 문서는 다른 언어모델/리뷰어에게
`XAU 하락 지속 구간에서 반등 BUY를 막는 것`
을 넘어서,
현재의 SELL bootstrap을
`direction-agnostic continuation candidate`
구조로 어떻게 일반화할지
조언을 받기 위한 상세 요청서다.

핵심 질문은 이것이다.

> 현재 시스템은 XAU 하락 지속 장면에서 BUY를 막기 시작했고
> 일부 SELL bootstrap candidate까지 surface에 올리기 시작했다.
> 하지만 이 구조를 SELL 전용으로 굳히지 않고,
> `anti_long / anti_short / pro_up / pro_down`
> 과
> `UP/DOWN WATCH -> PROBE -> ENTER`
> 상태기계로 일반화하려면
> 어떤 migration 설계가 맞는가?

---

## 핵심 진단 한 줄

현재 문제는 단순히
`XAU BUY가 너무 빨리 열린다`
가 아니라,

`계속 내려갈 가능성을 알고도 그 정보를
direction-agnostic continuation candidate 언어로 충분히 쓰지 못한다`
는 쪽에 더 가깝다.

즉:

- `사지 마`는 일부 알기 시작했음
- 하지만 아직
  `그럼 DOWN continuation을 봐야 한다`
  까지는 구조가 덜 닫힘

---

## 새 외부 조언 반영 포인트

최근 외부 조언의 핵심은 이렇다.

- 현재 구조는 XAU 하락 continuation 쪽 bootstrap으로는 유효하다
- 하지만 그대로 두면 `SELL/down bias`에 고정될 위험이 있다
- 따라서
  - `anti-buy / pro-sell`
    에 머물지 말고
  - `anti_long / anti_short / pro_up / pro_down`
    으로 일반화해야 한다
- 또한 상태도
  - `SELL_WATCH / SELL_PROBE / SELL_ENTER`
    보다
  - `DO_NOTHING / UP_WATCH / DOWN_WATCH / UP_PROBE / DOWN_PROBE / UP_ENTER / DOWN_ENTER`
    로 가는 것이 맞다

즉 지금 XAU 경로는
최종 구조가 아니라
`DOWN bootstrap`
으로 보고,
fresh runtime 검증과 dual-write migration을 먼저 해야 한다는 조언을 받았다.

---

## 현재 운영 맥락

기준 파일:

- [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)
- [market_family_entry_audit_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/market_family_entry_audit_latest.json)
- [failure_label_harvest_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/failure_label_harvest_latest.json)

최근 market-family audit 기준:

- `NAS100`
  - 최근 80행 중 `entered 2 / wait 78`
  - 주요 blocker:
    - `preflight_action_blocked 29`
    - `forecast_guard 16`
    - `middle_sr_anchor_guard 16`
  - focus: `inspect_nas_conflict_observe_decomposition`

- `BTCUSD`
  - 최근 80행 전부 `wait`
  - 주요 blocker:
    - `middle_sr_anchor_guard 45`
    - blank blocked_by + `observe_state_wait 35`
  - focus: `inspect_btc_middle_anchor_probe_relief`

- `XAUUSD`
  - 최근 80행 전부 `wait`
  - 주요 blocker:
    - `outer_band_guard 67`
    - `middle_sr_anchor_guard 13`
  - action_none:
    - `probe_not_promoted 69`
    - `observe_state_wait 11`
  - focus: `inspect_xau_outer_band_follow_through_bridge`

즉 XAU는
`신호를 전혀 못 보는 문제`보다
`follow-through / continuation을 과하게 막는 문제`
가 더 크게 보인다.

---

## 실제 사용자 관찰

사용자 관찰:

- XAU가 계속 아래로 가는 장면인데
- 시스템이 상방 반등 가능성이 있다고 보이게 만들었고
- 실제로 그 신호를 믿고 진입했다가 손실이 났다

사용자 요구는 단순하다.

> `사지 마`로 끝내지 말고,
> `이건 오히려 반대 방향 candidate로 봐야 한다`
> 는 표기를 남겨야 한다.

이 요구는 타당하다.

현재 같은 장면에서 필요한 것은
`BUY veto`
만이 아니라
`DOWN continuation candidate bootstrap`
이다.

다만 이 bootstrap을
곧바로 SELL execution owner로 만들기보다,
나중에 `UP/DOWN` 대칭 구조로 확장 가능한 형태로 두고 싶다.

---

## 최근 XAU 문제의 구체 형태

최근 손실/취약 XAU BUY 구간은 대체로:

- `setup_id = range_lower_reversal_buy`
- `setup_reason = shadow_lower_rebound_probe_observe_bounded_probe_soft_edge`
  또는 `shadow_outer_band_reversal_support_required_observe`
- `bb_state = LOWER_EDGE / MID`
- `box_state = LOWER / BELOW`

그런데 entry row 안에 이미 이런 경고가 같이 있었다.

- `forecast_state25_overlay_reason_summary = wait_bias_hold|wait_reinforce`
- `belief_action_hint_reason_summary = fragile_thesis|reduce_risk`
- `barrier_action_hint_reason_summary = wait_block|unstable`

즉 시스템 내부 증거는 이미:

- 기다려라
- thesis가 약하다
- barrier가 불안하다

를 말하고 있었다.

문제는 이 증거를
`BUY veto`
이상으로 쓰지 못하고 있었다는 점이다.

---

## 지금까지 실제로 구현된 것

관련 코드:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
- [entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)
- [entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_engines.py)
- [entry_service.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_service.py)
- [storage_compaction.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/storage_compaction.py)

### 1. XAU countertrend warning veto 추가

현재는 XAU BUY lower-rebound / outer-band follow-through 경로에서
다음 3종 경고가 겹치면 bounded relief를 막는다.

- forecast:
  - `wait_bias_hold`
  - `wait_reinforce`
- belief:
  - `fragile_thesis`
  - `reduce_risk`
- barrier:
  - `wait_block`
  - `unstable`

2개 이상 겹치면:

- `xau_countertrend_warning_veto`
또는
- `xau_follow_through_countertrend_veto`

로 차단된다.

### 2. countertrend continuation signal 생성

이번에 추가한 helper:

- [entry_try_open_entry.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_try_open_entry.py)
  - `_build_countertrend_continuation_signal_v1(...)`

현재 이 helper는
XAU BUY lower-reversal family에서 경고가 2개 이상 겹치면:

- `enabled = true`
- `signal_state = down_continuation_bias`
- `signal_action = SELL`
- `signal_confidence`
- `warning_count`
- `reason_summary`

를 만든다.

중요:

- 이건 아직 최종 SELL owner가 아니라
  `DOWN bootstrap`
  용 signal로 보고 있다.

### 3. candidate bridge 연결

현재 이 signal은
[entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/entry_candidate_bridge.py)
에서
`countertrend_candidate`
로 surface에 올라간다.

샘플 확인 결과:

- `entry_candidate_bridge_source = countertrend_candidate`
- `entry_candidate_bridge_action = SELL`
- `entry_candidate_surface_family = follow_through_surface`
- `entry_candidate_surface_state = continuation_follow`

이렇게 나온다.

현재 해석:

- `countertrend_candidate`
  는 SELL-specific owner로 고정하려는 것이 아니라
- 일단 DOWN bootstrap을 담는 임시 owner이며,
  이후 direction-agnostic continuation owner로 바꾸는 것이 목표다

### 4. 로그 필드 확장

현재 추가된 scalar/detail 필드:

- `countertrend_continuation_enabled`
- `countertrend_continuation_state`
- `countertrend_continuation_action`
- `countertrend_continuation_confidence`
- `countertrend_continuation_reason_summary`
- `countertrend_continuation_warning_count`
- `countertrend_continuation_surface_family`
- `countertrend_continuation_surface_state`
- `countertrend_candidate_action`
- `countertrend_candidate_confidence`
- `countertrend_candidate_reason`
- `countertrend_continuation_signal_v1` detail payload

### 5. 테스트 상태

관련 테스트:

- [test_entry_try_open_entry_probe.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_try_open_entry_probe.py)
- [test_entry_candidate_bridge.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_candidate_bridge.py)
- [test_entry_engines.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_engines.py)
- [test_entry_service_guards.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_entry_service_guards.py)

현재 회귀:

- `148 passed`

---

## 아직 안 닫힌 부분

중요:

코드는 들어갔지만,
아직 실제 fresh runtime row에서
아래 필드가 live로 찍히는지 확인은 안 했다.

- `countertrend_continuation_*`
- `countertrend_candidate_action = SELL`

즉 지금 상태는:

- 구조는 붙음
- 테스트는 통과함
- 샘플 helper 실행 결과도 맞음
- 하지만 아직 live fresh row 재확인은 미완료

그리고 더 큰 구조 문제도 남아 있다.

- 아직 evidence가
  `anti-buy / pro-sell`
  수준에 머물러 있다
- 아직 상태가
  `SELL candidate`
  수준에 머물러 있다
- 아직 `UP` 대칭 경로가 없다

---

## 왜 더 상세한 조언이 필요한가

지금 상태로는
`BUY 하면 안 된다`
는 쪽은 일부 잡기 시작했지만,
`그래서 DOWN continuation을 어떻게 안전하게 승격할지`
그리고
`이 구조를 어떻게 UP/DOWN 대칭으로 일반화할지`
를 운영 가능한 규칙으로 닫기엔 아직 부족하다.

특히 아래 구분이 아직 약하다.

### 1. anti-buy evidence vs pro-sell evidence

이 둘은 다르다.

- anti-buy evidence
  - 지금 BUY thesis가 약하다
  - 불안정하다
  - 기다리는 게 낫다

- pro-sell evidence
  - 실제로 하락 continuation이 강하다
  - SELL 쪽이 더 높은 EV다

현재 구현은 첫 번째를 잘 잡기 시작한 상태이고,
두 번째는 아직 초기 상태다.

추가로,
이제는 아래 질문까지 같이 풀고 싶다.

- `anti-buy / pro-sell`
  을 그대로 확장할지
- 아니면
  `anti_long / anti_short / pro_up / pro_down`
  으로 바로 바꿔야 하는지

### 2. WATCH / PROBE / ENTER 분기 미정

현재는 SELL bootstrap candidate를 만들 수 있게는 됐지만,
이걸 어떤 단계에서 승격해야 하는지가 정리되지 않았다.

필요한 것은 최소 다음 분기다.

- `WATCH`
  - BUY는 금지
  - SELL은 아직 관찰
- `PROBE`
  - 하락 continuation 증거가 의미 있게 누적
  - 작은 size 허용
- `ENTER`
  - continuation 구조 + guard + 위험 대비가 모두 맞을 때

추가로 이 상태들을
SELL-specific으로 둘지,
아니면
`DOWN_WATCH / DOWN_PROBE / DOWN_ENTER`
부터 시작해
나중에
`UP_WATCH / UP_PROBE / UP_ENTER`
를 붙일지
조언이 필요하다.

### 3. do-nothing과 SELL candidate 비교가 아직 없음

현재는 SELL candidate를 만들 수는 있지만,
아직
`아무것도 안 하는 것`
과
`DOWN_WATCH`
와
`DOWN_PROBE`
를 같은 판 위에서 비교하지 않는다.

---

## 외부 리뷰어에게 묻고 싶은 핵심 질문

### 질문 1. `anti-buy / pro-sell`를 유지할지, `anti_long / anti_short / pro_up / pro_down`로 바로 바꿀지

현재 구현은 XAU 하락 continuation bootstrap이라
`anti-buy + SELL candidate`
형태로 먼저 들어갔다.

그런데 외부 조언은
이 구조를 SELL/down 편향으로 두지 말고
방향 독립 구조로 바꾸라고 한다.

질문:

- 지금 단계에서 바로
  `anti_long / anti_short / pro_up / pro_down`
  dual-write를 시작하는 것이 맞는가
- 아니면 먼저 XAU DOWN bootstrap을 검증한 뒤
  다음 단계에서 일반화하는 것이 맞는가

### 질문 2. anti-buy evidence와 pro-sell evidence를 어떻게 분리하는 것이 맞는가

현재 XAU 하락 continuation 문제에서
아래 3종 경고를 쓰고 있다.

- forecast wait-bias
- belief fragile thesis / reduce risk
- barrier wait-block / unstable

이 3종은 분명 `사지 마` 근거는 되는데,
이것만으로 `SELL 진입`까지 올려도 되는지,
아니면 추가적인 continuation 증거가 더 필요한지 조언이 필요하다.

### 질문 3. WATCH / PROBE / ENTER를 어떤 bounded rule로 나누는 것이 맞는가

현재 생각하는 구조는:

- `DOWN_WATCH`
  - anti-buy 강함
  - 하지만 pro-sell은 아직 약함
- `DOWN_PROBE`
  - anti-buy 강함
  - plus 하락 continuation 구조 일부 확인
- `DOWN_ENTER`
  - anti-buy + pro-sell + 기존 guard 통과

이 3단계 bounded 승격 구조가 맞는지,
맞다면 어떤 피처를 각 단계의 핵심 기준으로 삼아야 하는지 묻고 싶다.

또한 이 상태명을
처음부터
`UP/DOWN_WATCH/PROBE/ENTER`
로 잡는 것이 더 좋은지도 궁금하다.

### 질문 4. XAU countertrend BUY family를 DOWN continuation family로 뒤집을 때 어떤 피처가 더 필요할까

현재는 주로:

- forecast wait bias
- belief fragile thesis
- barrier unstable

를 사용한다.

그런데 진짜 SELL continuation으로 올리려면
예를 들어 다음 같은 추가 피처가 필요한지 궁금하다.

- M1/M5 하락 연속성
- recent lower low / lower high 구조
- BB20 mid reclaim 실패
- same-side follow-through strength
- breakout / continuation time-axis
- volume/participation fade

그리고 같은 피처의 상승 대칭인

- recent higher high / higher low
- BB20 mid reject failure
- same-side upside follow-through strength

도 함께 설계해야 하는지 묻고 싶다.

### 질문 5. candidate는 어느 owner 계층에 놓는 것이 맞는가

현재 system architecture는:

- baseline / probe / breakout / state25 / semantic / shadow / candidate bridge

가 공존한다.

여기서 XAU 하락 continuation bootstrap은:

- breakout candidate의 일종으로 볼지
- 별도 `countertrend_candidate`로 둘지
- follow_through_surface 전용 continuation owner로 둘지

어느 방향이 더 안정적인지 조언이 필요하다.

특히 지금처럼
`countertrend_candidate`
를 임시로 유지하되,
장기적으로는 direction-agnostic owner로 일반화하는 것이 맞는지 궁금하다.

### 질문 6. fresh runtime 검증에서 무엇을 성공 기준으로 봐야 하는가

이제 실제로 보고 싶은 것은:

- fresh XAU row에서 `countertrend_continuation_enabled = true`
- 같은 row에서 `countertrend_candidate_action = SELL`
- 그 장면이 실제 차트상 하락 continuation 장면과 맞는지

인데, 이 외에 운영적으로 어떤 지표를 함께 봐야 하는지 묻고 싶다.

예:

- false positive rate
- same family repeated fire rate
- watch -> probe 승격률
- probe -> actual enter 전환률
- subsequent drawdown / giveback

### 질문 7. 지금은 SELL candidate만 남기고 live는 안 여는 것이 맞는가

현 단계에서 가장 안전한 방향이:

- 먼저 fresh runtime에서 `SELL candidate` 기록
- 그다음 `WATCH`
- 이후 `PROBE`
- `ENTER`는 마지막

이 맞는지,
아니면 일부 family에서는 더 빠르게 bounded probe를 열어도 되는지 판단을 묻고 싶다.

### 질문 8. 현재 XAU DOWN bootstrap을 어떻게 UP/DOWN 대칭 구조로 옮기는 것이 가장 안전한가

내가 현재 생각하는 migration은:

1. fresh runtime에서 현재
   `countertrend_continuation_*`
   materialization 확인
2. dual-write로
   `anti_long / anti_short / pro_up / pro_down`
   추가
3. 현재 XAU path를
   `DOWN_WATCH / DOWN_PROBE / DOWN_ENTER`
   로 먼저 매핑
4. 이후 상승 continuation 대칭 경로를 추가
5. 마지막에 execution layer에서만
   `UP_ENTER -> BUY`, `DOWN_ENTER -> SELL`

이 순서가 안전한지 조언이 필요하다.

---

## 내가 현재 생각하는 임시 방향

현재 내 가설은 이렇다.

1. 지금 단계에서 가장 먼저 해야 할 것은 fresh runtime 검증이다.
   - field가 실제로 찍히는지
   - 얼마나 자주 뜨는지
   - 정말 하락 continuation 장면과 맞는지

2. 그 다음에야 bounded 승격을 열어야 한다.

3. `anti-buy evidence`만으로는 `ENTER SELL`까지 올리면 위험하다.

4. 따라서 현 순서는:
   - `current bootstrap logging`
   - `DOWN_WATCH`
   - `DOWN_PROBE`
   - 마지막에만 `DOWN_ENTER`

5. 장기 구조는
   - `DO_NOTHING`
   - `UP_WATCH / DOWN_WATCH`
   - `UP_PROBE / DOWN_PROBE`
   - `UP_ENTER / DOWN_ENTER`
   를 같은 continuation surface 위에 두는 것이다

6. 실행층에서만
   - `UP_ENTER -> BUY`
   - `DOWN_ENTER -> SELL`
   로 바꾸는 편이 더 낫다고 본다

---

## 바로 붙여넣기용 짧은 질문

아래 내용을 보고 조언해 주세요.

현재 CFD 시스템에서 XAU 하락 continuation 장면을 더 잘 다루기 위해, 기존 `range_lower_reversal_buy` / `outer_band_reversal_support_required_observe` 계열 BUY 경로에 대해 `forecast wait-bias`, `belief fragile_thesis`, `barrier wait_block/unstable`가 2개 이상 겹치면 `countertrend_continuation_signal_v1`를 만들고 bootstrap 형태의 `SELL candidate`를 남기도록 구현했습니다. 지금은 `BUY veto`는 일부 되지만, 아직 이 구조를 SELL 전용으로 둘지, 아니면 `anti_long / anti_short / pro_up / pro_down`와 `UP/DOWN WATCH -> PROBE -> ENTER` 상태기계로 일반화할지 판단이 필요합니다.

질문은 다음입니다.

1. 이런 bootstrap 경로를 SELL 전용으로 유지하지 않고 `UP/DOWN` 대칭 구조로 일반화하는 가장 안전한 migration 순서는 무엇일까요?
2. `사지 마` 근거와 `지금 down continuation을 봐도 된다` 근거를 어떻게 분리하는 것이 맞을까요?
3. XAU DOWN continuation candidate를 `DOWN_WATCH / DOWN_PROBE / DOWN_ENTER` 3단계로 나눈다면 각 단계의 핵심 피처는 무엇이 되어야 할까요?
4. 현재의 forecast/belief/barrier 경고 외에 어떤 continuation 증거를 더 넣어야 안전할까요? 그리고 같은 피처의 상승 대칭은 어떻게 정의하는 것이 좋을까요?
5. 이 candidate는 breakout candidate의 일부로 다루는 게 맞을까요, 아니면 별도 direction-agnostic continuation owner로 두는 게 맞을까요?
6. 실제 fresh runtime row에서 어떤 지표를 성공 기준으로 확인해야 다음 bounded step으로 넘어가는 것이 안전할까요?

---

## 참고 문서

- [current_market_family_multi_surface_execution_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_design_ko.md)
- [current_market_family_multi_surface_execution_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_implementation_roadmap_ko.md)
- [current_execution_authority_integration_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_execution_authority_integration_design_ko.md)
- [current_breakout_ai2_authority_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_breakout_ai2_authority_external_review_request_ko.md)
