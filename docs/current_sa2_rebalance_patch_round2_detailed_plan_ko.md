# Current SA2 Rebalance Patch Round 2 Detailed Plan

## 목적

이번 2차 패치의 목적은 두 가지다.

1. `time_decay_risk`가 너무 잠겨서 late unresolved row 일부도 못 잡는 문제를 아주 작게 완화한다.
2. `BTCUSD / NAS100`에서 `trend_exhaustion`이 healthy runner 일부까지 과도하게 먹는 문제를 한 번 더 줄인다.

이번 패치는 `SA2`를 다시 설계하는 작업이 아니다.
기존 heuristic seed를 조금 더 균형 있게 만드는 소규모 조정이다.

---

## 직전 SA2.5 결과에서 확인된 문제

기준 artifact:

- [checkpoint_scene_sanity_latest.json](/C:/Users/bhs33/Desktop/project/cfd/data/analysis/shadow_auto/checkpoint_scene_sanity_latest.json)

직전 주요 수치:

- `trend_exhaustion = 692`
- `low_edge_state = 13`
- `time_decay_risk = 0`

핵심 해석:

- `low_edge_state`는 0에서 벗어나 실제로 열렸다.
- `trend_exhaustion`은 1080에서 692까지 줄었지만, 아직 `BTC/NAS exit_manage_runner` healthy runner 일부를 많이 먹는다.
- `time_decay_risk`는 반대로 너무 보수적으로 잠겨서 실제 late flat stalled row조차 거의 못 잡는다.

---

## 이번 2차 패치에서 잠그는 원칙

## 원칙 1. `time_decay_risk`는 "조금만" 다시 연다

이번엔 `OPEN_LOSS` late row를 다시 time-decay로 넓히지 않는다.

대신 아래 계열만 다시 열어준다.

- `checkpoint_type in {LATE_TREND_CHECK, RUNNER_CHECK}`
- `unrealized_pnl_state = FLAT`
- `runner_secured = false`
- `hold_quality`, `partial_exit`, `continuation`이 모두 중간 이하
- 실제로 거의 안 움직인 stalled row

즉 이번 패치는

> `late flat stalled row` 몇 개를 다시 `time_decay_risk`로 복구하는 패치다.

---

## 원칙 2. `trend_exhaustion`은 healthy runner에 더 엄격하게 막는다

지금 `BTC/NAS`에서 많이 잡히는 문제 row는 대부분 아래 특징을 가진다.

- `source = exit_manage_runner`
- `unrealized_pnl_state = OPEN_PROFIT`
- `runner_secured = true`
- `continuation`이 매우 높음
- `reversal`이 낮음
- `giveback_ratio`가 매우 낮음
- 실제론 runner가 아직 건강한 상태

이런 row는 late checkpoint라고 해도 `trend_exhaustion`으로 가면 안 된다.

그래서 이번엔 아래 healthy-runner guard를 추가한다.

- `runner_secured = true`
- `continuation >= 0.885`
- `reversal <= 0.49`
- `giveback_ratio <= 0.12`
- `current_profit`이 `mfe_since_entry`에 거의 붙어 있음

이 조합이면 `trend_exhaustion`에서 제외한다.

---

## 원칙 3. reason token은 보조 근거로만 쓴다

직전 규칙은 `runner`, `late`, `lock`, `partial` 같은 reason token만 있어도
late-pressure 근거로 작동하는 면이 있었다.

이번엔 이걸 더 보수적으로 바꾼다.

- reason token 단독으로는 부족
- 최소한 `giveback_ratio >= 0.12` 같은 실제 late-pressure 신호가 같이 있어야 한다

즉:

> 문자열 힌트만으로 scene을 바꾸지 않고, 실제 숫자 압력이 같이 있을 때만 scene을 바꾼다.

---

## 구현 대상 파일

- [path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_tagger.py)
- [test_path_checkpoint_scene_tagger.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_scene_tagger.py)

---

## 구체 수정 내용

## 1. `time_decay_risk` 완화

완화 방향:

- `hold_quality <= 0.42`
- `partial_exit <= 0.50`
- `continuation <= 0.60`
- `FLAT` stalled row는 허용
- `OPEN_PROFIT`는 여전히 보수적으로 유지
  - 아주 작은 수익
  - 작은 MFE
  - giveback 충분

기대 효과:

- `time_decay_risk = 0`에서 벗어난다
- 하지만 `OPEN_LOSS protective row`가 time-decay로 다시 흘러가지는 않는다

---

## 2. `trend_exhaustion` 축소

축소 방향:

- `partial_exit` 최소 기준을 소폭 올린다
- `continuation - reversal` 허용 폭을 조금 더 줄인다
- `reason token`은 보조로만 쓴다
- healthy runner guard를 추가한다

기대 효과:

- `BTC/NAS exit_manage_runner`의 건강한 runner 일부가 unresolved로 남는다
- `trend_exhaustion`은 실제 late pressure가 보이는 row에 더 집중된다

---

## 테스트 포인트

1. healthy runner row가 더 이상 `trend_exhaustion`으로 태깅되지 않는가
2. late flat stalled row가 다시 `time_decay_risk`로 잡히는가
3. 기존 `breakout_retest_hold`, `liquidity_sweep_reclaim`, `low_edge_state` 테스트는 깨지지 않는가
4. SA2.5 artifact에서
   - `time_decay_risk > 0`
   - `trend_exhaustion` 감소
   - `unexpected_transition_pair_counts = 0`
   가 유지되는가

---

## 완료 기준

- `time_decay_risk`가 완전히 0이 아닌 상태로 복구된다
- `trend_exhaustion`가 직전보다 더 줄어든다
- `BTCUSD / NAS100`의 healthy runner 일부가 unresolved로 빠진다
- scene sanity artifact가 다시 안정적으로 생성된다

---

## 한 줄 결론

이번 2차 패치는
`time_decay_risk`를 크게 넓히는 작업이 아니라
late stalled row 몇 개를 다시 살리고,
healthy runner가 `trend_exhaustion`으로 과잉 분류되는 것을 한 번 더 줄이는
작은 균형 조정 패치다.
