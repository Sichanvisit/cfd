# Current A6 Checkpoint Improvement Watch Heavy Cycle Detailed Plan

## 목적

`A6`의 목적은 `checkpoint_improvement_watch`가
가벼운 `light_cycle`과 `governance_cycle`만 도는 상태를 넘어서,

- `PA7 review processor`
- `PA78 review packet`
- `scene disagreement audit`
- `trend exhaustion scene bias preview`

를 주기적으로 다시 태우는 `heavy review axis`를 갖게 만드는 것이다.

핵심은 watch가 새 분석 로직을 직접 품는 것이 아니라,
이미 있는 무거운 refresh chain을 `heavy_cycle`로 조율하는 것이다.

---

## 이번 단계에서 하는 것

이번 `v0`에서는 아래만 닫는다.

1. `heavy_cycle` due/skip 판단
2. `include_deep_scene_review=True`로 heavy refresh 체인 호출
3. 성공 시 `heavy_last_run` 갱신
4. `PA7 / PA78 / scene disagreement / scene preview` 핵심 요약을 watch report에 반영
5. 실패 시 `DEGRADED + WatchError`

즉 이번 단계는 “무거운 분석을 watch가 새로 계산한다”보다
“기존 무거운 분석 파이프라인을 watch에서 주기적으로 다시 태운다”에 가깝다.

---

## 새 함수

- [checkpoint_improvement_watch.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_watch.py)
  - `run_checkpoint_improvement_watch_heavy_cycle(...)`

이 함수는 light cycle과 같은 패턴으로 동작한다.

- row count와 row delta 확인
- cycle definition으로 due/skip 결정
- heavy refresh function 호출
- state update
- report/json/md 출력

---

## 기본 실행 방식

기본 heavy refresh는 기존 refresh chain을 재사용한다.

- [path_checkpoint_analysis_refresh.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/path_checkpoint_analysis_refresh.py)
  - `maybe_refresh_checkpoint_analysis_chain(...)`

다만 `heavy_cycle`에서는 아래처럼 호출한다.

- `force=True`
- `include_deep_scene_review=True`
- `recent_limit=2000` 기본값

즉 light cycle이 fast artifact 위주라면,
heavy cycle은 same chain을 deep-scene까지 포함해서 다시 태우는 용도다.

---

## due / skip 기준

이번 단계는 [checkpoint_improvement_cycle_definition.py](/C:/Users/bhs33/Desktop/project/cfd/backend/services/checkpoint_improvement_cycle_definition.py)의
`heavy` 규칙을 그대로 따른다.

주요 기준:

- sample floor 미달이면 skip
- cooldown 중이면 skip
- hot path가 `EMERGENCY/SHUTDOWN`이면 skip
- row delta floor 충족 또는 preferred interval 경과 시 due

---

## watch report에 담는 최소 heavy summary

이번 단계에서 watch report는 아래 핵심만 요약한다.

- `deep_scene_review_refreshed`
- `pa7_processed_group_count`
- `pa7_unresolved_review_group_count`
- `pa7_review_state`
- `pa8_review_state`
- `scene_bias_review_state`
- `high_conf_scene_disagreement_count`
- `preview_changed_row_count`
- `preview_improved_row_count`
- `preview_worsened_row_count`
- `recommended_next_action`

즉 heavy cycle report는 “무거운 계산이 돌았는가”와
“지금 어떤 review 축이 막혀 있는가”를 빠르게 읽게 해주는 수준만 먼저 담는다.

---

## 에러 처리

heavy refresh function에서 예외가 나면:

- `SystemStateManager.transition("DEGRADED")`
- `WatchError` event publish
- 필요 시 `SystemPhaseChanged` publish

를 수행한다.

즉 heavy cycle 실패는 hot path 전체 종료가 아니라
`degraded but recoverable`로 취급한다.

---

## 테스트 포인트

이번 단계 테스트는 아래 4개를 닫는다.

1. sample floor 미달이면 skip
2. heavy refresh 성공 시 `heavy_last_run`이 갱신된다
3. cooldown 중이면 heavy refresh를 다시 호출하지 않는다
4. heavy refresh 예외 시 `DEGRADED + WatchError`가 뜬다

테스트 파일:

- [test_checkpoint_improvement_watch.py](/C:/Users/bhs33/Desktop/project/cfd/tests/unit/test_checkpoint_improvement_watch.py)

---

## 완료 조건

`A6`은 아래가 만족되면 닫힌다.

- watch가 `heavy_cycle`을 due/skip 규칙에 따라 실행한다
- deep scene review 포함 refresh chain을 호출한다
- `heavy_last_run`이 저장된다
- heavy 핵심 summary가 report에 남는다
- 실패 시 degraded 흐름이 닫힌다

이 단계가 닫히면 다음은 `C1 Master Board`가 가장 자연스럽다.
