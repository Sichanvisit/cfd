# Current SA2.5 Transition Watchlist Refinement

## 목적

이번 보강의 목적은 transition audit를 `allowed / watchlist / unexpected` 3단계로 나누는 것이다.

기존에는 전이쌍이 두 종류뿐이었다.

- `allowed`
- `unexpected`

하지만 CFD에서는 어떤 전이가

- 완전히 정상 전이는 아니고
- 그렇다고 단순 버그나 오염으로 보기에도 아까운

경우가 있다.

대표 예가 아래다.

- `breakout_retest_hold -> trend_exhaustion`

이 전이는 late leg에서 실제로 나올 수도 있지만,
CFD 특성상 “잔잔한 척하다가 후반에 뒤집히는 위험 전이”일 가능성도 있다.

그래서 이번 단계에서는 이 전이를 정식 허용으로 올리지 않고,
감시 대상인 `watchlist transition`으로 분리한다.

---

## 분류 원칙

## 1. allowed

정상 전이로 본다.

의미:

- audit에서 문제로 세지 않음
- scene sequence의 자연스러운 흐름으로 취급

## 2. watchlist

정상으로 풀어주지는 않지만, 계속 감시해야 하는 전이로 본다.

의미:

- `unexpected`처럼 버그/오염 취급은 하지 않음
- 별도 count로 계속 보이게 유지
- `recommended_next_action`도 watchlist 감시 모드로 유도

## 3. unexpected

아직 정상 전이로 보기 어려운 전이다.

의미:

- heuristic 오염
- surface/scene mismatch
- path grouping 오류
- 혹은 아직 이해되지 않은 장면 전이

가능성을 열어두고 계속 조사한다.

---

## 이번 단계에서 watchlist로 두는 전이

- `breakout_retest_hold -> trend_exhaustion`

이 전이를 지금 당장 `allowed`로 올리지 않는 이유:

- late leg 후반부의 위험 신호일 수 있다
- CFD에서 “정상 continuation”처럼 풀어주면 경계가 약해질 수 있다
- 아직 데이터가 충분히 많지 않다

즉 이 전이는

> 정상 전이로 승격하지 않고, 위험 전이 감시 목록으로 유지한다.

---

## 구현 변경

대상 파일:

- [path_checkpoint_scene_sanity.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_scene_sanity.py)
- [test_path_checkpoint_scene_sanity.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_path_checkpoint_scene_sanity.py)

핵심 변경:

- `_WATCHLIST_TRANSITION_PAIRS` 추가
- summary에 `watchlist_transition_pair_counts` 추가
- symbol row에 `watchlist_transition_count` 추가
- `recommended_next_action`
  - unexpected가 있으면 `inspect_unexpected_scene_transitions_before_sa3`
  - unexpected는 없고 watchlist만 있으면 `keep_watchlist_transition_monitoring_before_sa3`

---

## 기대 효과

1. CFD 특유의 “후반 위험 전이”를 normal pair로 너무 빨리 풀어주지 않는다.
2. 그렇다고 단순 오염처럼 unexpected에 몰아넣지도 않는다.
3. `SA3` 전까지 계속 눈에 띄게 감시할 수 있다.

---

## 한 줄 결론

이번 보강은
`breakout_retest_hold -> trend_exhaustion`을
정상 전이로 허용하지 않고,
CFD late-risk 장면으로 계속 감시하는 중간 단계 장치다.
