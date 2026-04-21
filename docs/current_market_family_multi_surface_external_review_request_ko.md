# Current Market-Family Multi-Surface External Review Request

## 목적

이 문서는 다른 언어모델/외부 리뷰어에게
현재 시스템 병목과 다음 설계 질문을
빠르게, 그러나 충분히 정확하게 전달하기 위한 요청서다.

핵심 질문은 이것이다.

> 지금 시스템을 "하나의 좋은 진입 점수" 방향으로 더 다듬는 것이 맞는가,
> 아니면 시장별/상황별로 다른 execution surface를 분리해서
> follow-through와 runner 보존까지 같이 배우게 만드는 것이 맞는가?

내부 판단은 후자다.

---

## 아주 짧은 한 줄 요약

지금 시스템은
`좋은 initial entry는 일부 열지만`,
그 이후 `follow-through / continuation / runner hold`를 과하게 차단하거나
너무 빨리 잘라내는 경향이 있다.

또한 이 문제는 시장별로 다르게 나타난다.

---

## 현재 상태 요약

기준 파일:

- [entry_decisions.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/entry_decisions.csv)
- [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

최근 240행 기준 entry 관찰:

- `NAS100`
  - 최근 80행 전부 `wait`
  - `blocked_by = ''`
  - `action_none_reason = observe_state_wait`
  - 대표 observe: `conflict_box_upper_bb20_lower_upper_dominant_observe`

- `BTCUSD`
  - 최근 80행 전부 `wait`
  - `action_none_reason = observe_state_wait`
  - 일부 `blocked_by = middle_sr_anchor_guard`
  - 대표 observe:
    - `conflict_box_upper_bb20_lower_upper_dominant_observe`
    - `middle_sr_anchor_required_observe`

- `XAUUSD`
  - 최근 80행 전부 `wait`
  - 전부 `blocked_by = outer_band_guard`
  - 전부 `action_none_reason = probe_not_promoted`
  - 대표 observe: `outer_band_reversal_support_required_observe`

즉 최근 관찰만 봐도,
세 시장이 같은 이유로 막히는 것이 아니다.

---

## XAU 사례가 특히 중요한 이유

사용자가 직접 본 차트에서는
XAU 진입 타점 자체는 좋았고,
그 뒤 가격이 더 크게 연장되었다.

실제 로그에서도 최근 XAU는 다음 두 건이 체결되었다.

- `2026-04-09 00:15:30` BUY entered
- `2026-04-09 00:29:12` BUY entered

둘 다:

- `setup_id = range_lower_reversal_buy`
- `observe_reason = outer_band_reversal_support_required_observe`
- `core_reason = core_shadow_probe_action`

그런데 두 번째 진입 이후:

- `2026-04-09 00:29:25`부터 `2026-04-09 00:47:44`까지
- 같은 계열 XAU row `131건`이 연속으로 `wait`
- 공통 이유:
  - `blocked_by = outer_band_guard`
  - `action_none_reason = probe_not_promoted`

즉 이건 "신호를 못 본다"라기보다,
`좋은 진입 뒤 follow-through 후보를 거의 전부 wait/observe로 누른다`에 가깝다.

---

## XAU entered vs blocked 비교

### entered rows 평균

- `pair_gap ≈ 0.2199`
- `candidate_support ≈ 0.4544`
- `action_confirm_score ≈ 0.2586`
- `confirm_fake_gap ≈ -0.0102`
- `wait_confirm_gap ≈ +0.0709`
- `same_side_barrier ≈ 0.5068`
- `structural_relief_applied = true`
- `ready_for_entry = true`

### 최근 blocked wait rows 평균

- `pair_gap ≈ 0.1957`
- `candidate_support ≈ 0.2986`
- `action_confirm_score ≈ 0.1347`
- `confirm_fake_gap ≈ -0.1533`
- `wait_confirm_gap ≈ -0.1021`
- `same_side_barrier ≈ 0.7877`
- `structural_relief_applied = false`
- `ready_for_entry = false`

즉 XAU는

- 좋은 initial entry는 열 수 있다
- 하지만 moderate-quality follow-through는
  `outer_band_guard + probe_not_promoted`로 거의 다 죽인다

---

## Exit 쪽 문제

기준: [trade_closed_history.csv](/C:/Users/bhs33/Desktop/project/cfd/data/trades/trade_closed_history.csv)

XAU 두 건은 진입은 맞았지만 청산이 빠르다.

- `2026-04-09 00:15:30` BUY
  - `2026-04-09 00:17:32` 종료
  - exit reason: `Target`
  - profit: `+2.58`
- `2026-04-09 00:29:12` BUY
  - `2026-04-09 00:31:12` 종료
  - exit reason: `Lock Exit ... hard_guard=profit_giveback`
  - profit: `+1.94`

사용자 관찰대로 이후 가격이 더 갔다면,
이건

- 진입 타점은 괜찮았지만
- `runner hold / continuation`을 너무 빨리 포기한 것

으로 읽을 수 있다.

---

## 핵심 내부 가설

### 가설 1. 단일 진입 점수 체계는 충분하지 않다

현재처럼 `좋은 진입 점수 하나`로 시스템을 몰면
아래를 모두 같은 문제로 취급하게 된다.

- initial entry
- follow-through
- pullback resume
- continuation hold
- protective exit

이렇게 되면 특정 "아주 좋은 첫 타점"만 배우고,
나머지 유용한 execution 정보는 다 묻히기 쉽다.

### 가설 2. 시장별로 서로 다른 blockage owner가 있다

- `NAS100`: observe/no-action 과다
- `BTCUSD`: middle-anchor + observe 정체
- `XAUUSD`: outer-band + probe promotion 과잉 차단

즉 글로벌 threshold 완화보다
`market-family bounded bridge`가 더 맞다.

### 가설 3. exit도 분리해야 한다

entry만 손보면 반쪽이다.

특히 XAU처럼
"진입은 맞는데 더 갈 수 있었던 장면"
에서는

- `continuation_hold_surface`
- `protective_exit_surface`

를 분리해서
runner를 남길지,
진짜 위험이라 자를지를 따로 봐야 한다.

### 가설 4. 사람이 체크/색으로 구분한 정보는 surface 라벨의 재료다

사용자는 차트에서
상황별 체크와 색깔을 나눠서 보고 있다.

이건 단순 설명 보조가 아니라,
서로 다른 execution state를 구분하는 약한 supervision이라고 본다.

즉 이걸

- `initial_break`
- `reclaim`
- `continuation`
- `pullback_resume`
- `runner_hold`
- `protect_exit`

같은 라벨로 올리는 게 맞다고 본다.

### 가설 5. 각 surface는 서로 다른 목적 함수를 가져야 한다

지금 단계에서 중요한 건
surface를 이름만 나누는 것이 아니라
무엇을 최적화하는지까지 나누는 것이다.

예:

- `initial_entry_surface`
  - 진입 후 일정 구간 `+EV`
- `follow_through_surface`
  - 이미 열린 방향의 추가 확장 가치
- `continuation_hold_surface`
  - 더 갈 확률 vs giveback 확률
- `protective_exit_surface`
  - 지금 안 자르면 손실 확대인지

### 가설 6. Do-Nothing도 action이다

현재 wait/observe가 많은 시스템이므로,
반드시 아래 비교가 필요하다고 본다.

- `do_nothing_ev`
- `enter_ev`
- `probe_ev`
- `runner_hold_ev`

즉 wait는 default가 아니라
선택 가능한 action이어야 한다.

### 가설 7. 시간 축이 없으면 follow-through와 hold를 못 배운다

breakout, follow-through, runner hold는 전부 시간 문제다.

그래서 최소한 아래가 필요하다고 본다.

- `time_since_breakout`
- `time_since_entry`
- `bars_in_state`
- `momentum_decay`

### 가설 8. 실패 케이스를 따로 학습해야 guard가 덜 굳는다

성공 케이스만 보면 시스템은 점점 보수적으로만 갈 수 있다.

그래서 최소 아래 실패 라벨이 필요하다고 본다.

- `failed_follow_through`
- `false_breakout`
- `early_exit_regret`

### 가설 9. 시장별 모델 완전 분리보다 market adapter가 낫다

NAS/BTC/XAU를 모델 자체로 쪼개기보다,

- 공통 surface
- 공통 목적 함수
- `market_family` feature / adapter

구조가 더 낫다고 본다.

---

## 내부 제안 구조

다음 4개 surface를 분리하려고 한다.

1. `initial_entry_surface`
2. `follow_through_surface`
3. `continuation_hold_surface`
4. `protective_exit_surface`

그리고 각 surface를
최소 `NAS100 / BTCUSD / XAUUSD` market-family 기준으로 나눠서 보려고 한다.

즉
`한 점수로 모든 시장/상황을 해결`이 아니라,
`시장별 + 상황별` 다중 surface 구조다.

---

## 이미 만들어진 관련 기반

- breakout runtime / overlay / canonical seed / preview export는 이미 있음
  - [breakout_event_runtime.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_event_runtime.py)
  - [breakout_aligned_training_seed.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_aligned_training_seed.py)
  - [breakout_shadow_preview_training_set.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/breakout_shadow_preview_training_set.py)
- authority integration AI1/AI2도 일부 진행됨
  - [current_execution_authority_integration_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_execution_authority_integration_design_ko.md)
  - [current_execution_authority_integration_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_execution_authority_integration_implementation_roadmap_ko.md)

즉 완전 새 구조를 처음부터 만드는 것이 아니라,
기존 자산을 `market-family + multi-surface` 방향으로 재정렬하는 상황이다.

---

## 다른 언어모델에게 묻고 싶은 핵심 질문

### 질문 1. 지금처럼 시장별/상황별 surface 분리로 가는 판단이 맞는가

즉 문제를
`좋은 진입 하나를 더 잘 찾자`
가 아니라
`initial / follow-through / hold / protect를 분리하자`
로 보는 게 맞는지 판단을 받고 싶다.

### 질문 2. 체크/색깔 기반 약한 supervision을 어떤 데이터 구조로 올리는 게 좋은가

예:

- discrete state label
- sequence label
- event tag + confidence
- ranking label

중 어떤 방향이 적합한지 궁금하다.

### 질문 3. XAU 같은 경우,
good initial entry 뒤 `outer_band_guard + probe_not_promoted`로 계속 막히는 follow-through를
어떤 bounded bridge로 여는 게 가장 안전한가

예:

- `WAIT_MORE -> WATCH -> PROBE_ENTRY -> ENTER_NOW`
같은 다단계 강등/승격 구조가 맞는지

### 질문 4. exit 쪽은 어떻게 나누는 게 좋은가

특히

- `Target`
- `Lock Exit`
- `profit_giveback`
- `Protect Exit`

를
`continuation_hold_surface`와 `protective_exit_surface`로 분리할 때
실무적으로 가장 깔끔한 기준이 궁금하다.

### 질문 5. 이 구조가 "특정 장면만 배우는 과적합"을 줄이는 데 실제로 도움이 되는가

즉 단일 점수 체계보다
market-family + multi-surface가
여러 시장에 대응하는 일반화에 더 유리한지 의견을 구하고 싶다.

---

## 바로 붙여넣기용 짧은 질문

아래 내용을 보고 조언해 주세요.

현재 시스템은 일부 좋은 initial entry는 열지만, follow-through / continuation / runner hold를 과하게 차단하거나 너무 빨리 청산하는 문제가 있습니다. 최근 entry 로그 기준으로 NAS100, BTCUSD, XAUUSD는 모두 최근 80행이 전부 wait였지만 막히는 이유가 서로 다릅니다. NAS100은 observe_state_wait, BTCUSD는 observe_state_wait + middle_sr_anchor_guard, XAUUSD는 outer_band_guard + probe_not_promoted가 지배적입니다.

특히 XAUUSD는 2026-04-09 00:15:30, 00:29:12 두 건의 BUY 진입은 실제로 열렸고 타점도 나쁘지 않았는데, 그 뒤 비슷한 장면 131행이 전부 outer_band_guard + probe_not_promoted로 wait 처리되었습니다. 게다가 두 진입 모두 비교적 빨리 Target 또는 Lock Exit / profit_giveback으로 종료되어, runner hold / continuation을 너무 빨리 포기한 것처럼 보입니다.

그래서 다음 구조를 고민 중입니다.

1. 시장을 NAS100 / BTCUSD / XAUUSD family로 분리
2. 실행 상황을 initial_entry / follow_through / continuation_hold / protective_exit 4개 surface로 분리
3. 사람이 차트에서 체크/색깔로 구분한 정보를 약한 supervision 라벨로 승격
4. XAU outer-band follow-through는 WAIT_MORE와 ENTER_NOW 사이에 WATCH / PROBE_ENTRY 같은 bounded 상태를 추가
5. exit도 continuation_hold_surface와 protective_exit_surface를 분리
6. 각 surface별 objective / EV proxy를 따로 둠
7. do-nothing도 action으로 두고 EV 비교에 넣음
8. breakout / hold / follow-through에 시간 축을 넣음
9. failure case를 별도 라벨로 축적
10. 종목별 모델 완전 분리 대신 market adapter를 사용

질문은 다음입니다.

- 이 방향이 단일 진입 점수 체계보다 맞는가
- 체크/색 정보를 어떤 라벨 구조로 올리는 게 좋은가
- XAU follow-through / runner hold 문제를 어떤 bounded bridge로 여는 게 좋은가
- exit를 continuation_hold와 protective_exit로 분리할 때 가장 실무적인 기준은 무엇인가
- 이런 multi-surface 구조가 특정 한 종류의 perfect entry에 몰리는 과적합을 줄이는 데 도움이 되는가
- surface별 objective / EV proxy를 어떤 수준에서 정의하는 게 실무적으로 적절한가
- do-nothing EV를 어떤 proxy로 시작하는 게 좋은가
- 분포 기반 gate를 절대 threshold와 어떻게 함께 써야 안정적인가
- market-family별 모델 분리보다 adapter 구조가 정말 더 적절한가

---

## 더 긴 질문용 참고 문서

- [current_market_family_multi_surface_execution_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_design_ko.md)
- [current_market_family_multi_surface_execution_implementation_roadmap_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_market_family_multi_surface_execution_implementation_roadmap_ko.md)
- [current_execution_authority_integration_design_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_execution_authority_integration_design_ko.md)
- [current_breakout_ai2_authority_external_review_request_ko.md](/C:/Users/bhs33/Desktop/project/cfd/docs/current_breakout_ai2_authority_external_review_request_ko.md)
